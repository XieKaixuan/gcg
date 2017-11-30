import os, pickle
import itertools
import numpy as np

from rllab.misc.ext import get_seed

try:
    from rllab.envs.gym_env import GymEnv
    import gym_ple
except:
    GymEnv = None

from sandbox.rocky.tf.envs.vec_env_executor import VecEnvExecutor

from sandbox.gkahn.gcg.sampler.replay_pool import RNNCriticReplayPool
from sandbox.gkahn.gcg.utils import utils
from sandbox.gkahn.gcg.envs.env_utils import create_env
from sandbox.rocky.tf.spaces.discrete import Discrete
from sandbox.rocky.tf.spaces.box import Box
from sandbox.gkahn.gcg.utils import logger
from sandbox.gkahn.gcg.utils import mypickle

class RNNCriticSampler(object):
    def __init__(self, policy, env, n_envs, replay_pool_size, max_path_length, sampling_method,
                 save_rollouts=False, save_rollouts_observations=True, save_env_infos=False, env_str=None, replay_pool_params={}):
        self._policy = policy
        self._n_envs = n_envs

        assert(self._n_envs == 1) # b/c policy reset

        self._replay_pools = [RNNCriticReplayPool(env.spec,
                                                  env.horizon,
                                                  policy.N,
                                                  policy.gamma,
                                                  replay_pool_size // n_envs,
                                                  obs_history_len=policy.obs_history_len,
                                                  sampling_method=sampling_method,
                                                  save_rollouts=save_rollouts,
                                                  save_rollouts_observations=save_rollouts_observations,
                                                  save_env_infos=save_env_infos,
                                                  replay_pool_params=replay_pool_params)
                              for _ in range(n_envs)]

        try:
            envs = [pickle.loads(pickle.dumps(env)) for _ in range(self._n_envs)] if self._n_envs > 1 else [env]
        except:
            envs = [create_env(env_str) for _ in range(self._n_envs)] if self._n_envs > 1 else [env]
        ### need to seed each environment if it is GymEnv
        seed = get_seed()
        if seed is not None and GymEnv is not None and isinstance(utils.inner_env(env), GymEnv):
            for i, env in enumerate(envs):
                utils.inner_env(env).env.seed(seed + i)
        self._vec_env = VecEnvExecutor(
            envs=envs,
            max_path_length=max_path_length
        )

    @property
    def n_envs(self):
        return self._n_envs

    ##################
    ### Statistics ###
    ##################

    @property
    def statistics(self):
        return RNNCriticReplayPool.statistics_pools(self._replay_pools)

    def __len__(self):
        return sum([len(rp) for rp in self._replay_pools])

    ####################
    ### Add to pools ###
    ####################

    def step(self, step, take_random_actions=False, explore=True):
        """ Takes one step in each simulator and adds to respective replay pools """
        ### store last observations and get encoded
        encoded_observations = []
        for i, (replay_pool, observation) in enumerate(zip(self._replay_pools, self._curr_observations)):
            replay_pool.store_observation(step + i, observation)
            encoded_observations.append(replay_pool.encode_recent_observation())

        ### get actions
        if take_random_actions:
            actions = [self._vec_env.action_space.sample() for _ in range(self._n_envs)]
            est_values = [np.nan] * self._n_envs
            if isinstance(self._vec_env.action_space, Discrete):
                logprobs = [-np.log(self._vec_env.action_space.flat_dim)] * self._n_envs
            elif isinstance(self._vec_env.action_space, Box):
                low = self._vec_env.action_space.low
                high = self._vec_env.action_space.high
                logprobs = [-np.sum(np.log(high - low))] * self._n_envs
            else:
                raise NotImplementedError
        else:
            actions, est_values, logprobs, _ = self._policy.get_actions(
                steps=list(range(step, step + self._n_envs)),
                current_episode_steps=self._vec_env.current_episode_steps,
                observations=encoded_observations,
                explore=explore)

        ### take step
        next_observations, rewards, dones, env_infos = self._vec_env.step(actions)

        if np.any(dones):
            self._policy.reset_get_action()

        ### add to replay pool
        for replay_pool, action, reward, done, env_info, est_value, logprob in \
                zip(self._replay_pools, actions, rewards, dones, env_infos, est_values, logprobs):
            replay_pool.store_effect(action, reward, done, env_info, est_value, logprob)

        self._curr_observations = next_observations

    def trash_current_rollouts(self):
        """ In case an error happens """
        steps_removed = 0
        for replay_pool in self._replay_pools:
            steps_removed += replay_pool.trash_current_rollout()
        return steps_removed

    def reset(self):
        self._curr_observations = self._vec_env.reset()
        for replay_pool in self._replay_pools:
            replay_pool.force_done()

    ####################
    ### Add rollouts ###
    ####################

    def add_rollouts(self, rollout_filenames, max_to_add=None):
        step = sum([replay_pool.num_store_calls for replay_pool in self._replay_pools])
        itr = 0
        replay_pools = itertools.cycle(self._replay_pools)
        done_adding = False

        for fname in rollout_filenames:
            rollouts = mypickle.load(fname)['rollouts']
            itr += 1

            for rollout, replay_pool in zip(rollouts, replay_pools):
                r_len = len(rollout['dones'])
                if max_to_add is not None and step + r_len >= max_to_add:
                    diff = max_to_add - step
                    for k in ('observations', 'actions', 'rewards', 'dones', 'logprobs'):
                        rollout[k] = rollout[k][:diff]
                    done_adding = True
                    r_len = len(rollout['dones'])

                replay_pool.store_rollout(step, rollout)
                step += r_len

                if done_adding:
                    break

            if done_adding:
                break

    #########################
    ### Sample from pools ###
    #########################

    def can_sample(self):
        return np.any([replay_pool.can_sample() for replay_pool in self._replay_pools])

    def sample(self, batch_size):
        return RNNCriticReplayPool.sample_pools(self._replay_pools, batch_size,
                                                only_completed_episodes=self._policy.only_completed_episodes)

    ###############
    ### Logging ###
    ###############

    def log(self, prefix=''):
        RNNCriticReplayPool.log_pools(self._replay_pools, prefix=prefix)

    def get_recent_paths(self):
        return RNNCriticReplayPool.get_recent_paths_pools(self._replay_pools)

