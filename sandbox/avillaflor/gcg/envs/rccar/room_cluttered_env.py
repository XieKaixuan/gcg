import os
import numpy as np
from math import pi

from panda3d.core import BitMask32
from panda3d.bullet import BulletHelper
from panda3d.bullet import BulletRigidBodyNode

from rllab.spaces.box import Box
from sandbox.avillaflor.gcg.envs.rccar.square_env import SquareEnv
from sandbox.avillaflor.gcg.envs.rccar.car_env import CarEnv

class RoomClutteredEnv(SquareEnv):
    def __init__(self, params={}):
        
        #TODO
        self._goal_heading = np.array([0.])
        self._base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')
        params.setdefault('model_path', os.path.join(self._base_dir, 'room.egg'))
        params.setdefault('obj_paths', ['bookcase.egg', 'chair.egg', 'coffee_table.egg', 'desk.egg', 'stool.egg', 'table.egg'])
        self._obj_paths = [os.path.join(self._base_dir, x) for x in params['obj_paths']]
        
        SquareEnv.__init__(self, params=params)

    def _default_pos(self):
        return (20.0, -20., 0.3)

    def _setup_map(self):
        index = 0
        max_len = len(self._obj_paths)
        oris = [0., 90., 180., 270.]
        for i in range(5, 45, 5):
            for j in range(5, 45, 5):
                pos = (i - 22.5, j - 22.5, 0.3)
                path = self._obj_paths[index % max_len]
                angle = oris[(index // max_len) % 4]
                hpr = (angle, 0.0, 0.0)
                self._setup_collision_object(path, pos, hpr)
                index += 1
        self._setup_collision_object(self._model_path)

    def _get_observation(self):
        im, vec = super(RoomClutteredEnv, self)._get_observation()

#        goal = np.array([0.0])
        vec = np.hstack([vec, self._goal_heading])
        return im, vec

    def _get_reward(self):
        if self._collision:
            reward = self._collision_reward
        else:
            if self._collision_reward_only:
                reward = 0
            else:
#                if self._get_heading() > pi or self._goal_heading[0] > pi:
#                    import IPython; IPython.embed()
                reward = np.cos(self._goal_heading[0] - self._get_heading())  
        return reward

    def _default_restart_pos(self):
        return [
                [  21., -21., 0.3,  30.0, 0.0, 0.0], [  21., -21., 0.3,  45.0, 0.0, 0.0], [  21., -21., 0.3,  60.0, 0.0, 0.0],
                [  21.,  21., 0.3, 120.0, 0.0, 0.0], [  21.,  21., 0.3, 135.0, 0.0, 0.0], [  21.,  21., 0.3, 150.0, 0.0, 0.0],
                [ -21.,  21., 0.3, 210.0, 0.0, 0.0], [ -21.,  21., 0.3, 225.0, 0.0, 0.0], [ -21.,  21., 0.3, 240.0, 0.0, 0.0],
                [ -21., -21., 0.3, 300.0, 0.0, 0.0], [ -21., -21., 0.3, 315.0, 0.0, 0.0], [ -21., -21., 0.3, 330.0, 0.0, 0.0],
            ]

    def _default_restart_goal(self):
        goals = []
        for pos in self._default_restart_pos():
            goal = pos[3] * pi / 180.0
#            if goal > pi:
#                goal = goal - (2 * pi)
            goals.append(goal)
        return goals

    def _next_restart_pos_hpr_goal(self):
        num = len(self._restart_pos)
        if num == 0:
            return None, None
        else:
            # TODO
            pos_hpr = self._restart_pos[self._restart_index]
            goal = self._default_restart_goal()[self._restart_index]
            self._restart_index = (self._restart_index + 1) % num
            return pos_hpr[:3], pos_hpr[3:], goal

    @property
    def horizon(self):
        return 80

    # TODO
    def reset(self):
        if self._do_back_up:
            if self._collision:
                self._back_up()
        else:
            pos, hpr, goal = self._next_restart_pos_hpr_goal()
            self._place_vehicle(pos=pos, hpr=hpr)
            self._goal_heading = np.array([goal])
        self._collision = False
        return self._get_observation()

    def _get_info(self):
        info = {}
        info['pos'] = np.array(self._vehicle_pointer.getPos())
        info['hpr'] = np.array(self._vehicle_pointer.getHpr())
        info['vel'] = self._get_speed()
        info['goal_h'] =  self._goal_heading
        info['coll'] = self._collision
        return info

if __name__ == '__main__':
    params = {'visualize': True, 'run_as_task': True, 'do_back_up': True, 'hfov': 120}
    env = RoomClutteredEnv(params)
