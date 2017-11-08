import os
import numpy as np
from math import pi

from panda3d.core import BitMask32
from panda3d.bullet import BulletHelper
from panda3d.bullet import BulletRigidBodyNode

from rllab.spaces.box import Box
from sandbox.avillaflor.gcg.envs.rccar.room_cluttered_env import RoomClutteredEnv

class SimpleRoomClutteredEnv(RoomClutteredEnv):
    def __init__(self, params={}):
        self._base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')
        params.setdefault('model_path', os.path.join(self._base_dir, 'small_room.egg'))
        params.setdefault('obj_paths', ['bookcase.egg'])
        RoomClutteredEnv.__init__(self, params=params)

    def _setup_map(self):
        # TODO maybe stagger
        index = 0
        max_len = len(self._obj_paths)
        oris = [0., 90., 180., 270.]
        for i in range(2, 27, 5):
            for j in range(2, 27, 5):
                if (i != 2 and i != 22) or (j!=2 and j!=22): 
                    pos = (i - 12., j - 12., 0.3)
                    path = self._obj_paths[index % max_len]
                    angle = oris[(index // max_len) % 4]
                    hpr = (angle, 0.0, 0.0)
                    self._setup_collision_object(path, pos, hpr)
                    index += 1
        self._setup_collision_object(self._model_path)

    def _default_pos(self):
        return (11.0, -11., 0.3)

    def _default_restart_pos(self):
        return [
                [  11., -11., 0.3,  30.0, 0.0, 0.0], [  11., -11., 0.3,  45.0, 0.0, 0.0], [  11., -11., 0.3,  60.0, 0.0, 0.0],
                [  11.,  11., 0.3, 120.0, 0.0, 0.0], [  11.,  11., 0.3, 135.0, 0.0, 0.0], [  11.,  11., 0.3, 150.0, 0.0, 0.0],
                [ -11.,  11., 0.3, 210.0, 0.0, 0.0], [ -11.,  11., 0.3, 225.0, 0.0, 0.0], [ -11.,  11., 0.3, 240.0, 0.0, 0.0],
                [ -11., -11., 0.3, 300.0, 0.0, 0.0], [ -11., -11., 0.3, 315.0, 0.0, 0.0], [ -11., -11., 0.3, 330.0, 0.0, 0.0],
            ]

    @property
    def horizon(self):
        return 40

if __name__ == '__main__':
    params = {'visualize': True, 'run_as_task': True, 'do_back_up': True, 'hfov': 120}
    env = SimpleRoomClutteredEnv(params)
