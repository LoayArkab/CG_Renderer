"""
camera.py - a first-person "fly" camera.

The camera has a position and two angles: yaw (turn left/right around Y)
and pitch (look up/down around X). The camera's own transform in the world is
    T(position) @ Ry(yaw) @ Rx(pitch)
The VIEW matrix is the inverse of that: it moves the whole world so that the
camera ends up at the origin looking down -Z:
    Rx(-pitch) @ Ry(-yaw) @ T(-position)
"""
import math

import numpy as np
import pygame

import math3d as m3

MOVE_SPEED = 3.0              # units per second
TURN_SPEED = math.radians(90) # radians per second
PITCH_LIMIT = math.radians(89)


class Camera:
    def __init__(self, position=(0.0, 0.0, 6.0), yaw=0.0, pitch=0.0):
        self.start = (tuple(position), yaw, pitch)
        self.reset()

    def reset(self):
        position, self.yaw, self.pitch = self.start
        self.position = np.array(position, dtype=float)

    def forward(self):
        """Direction the camera faces, flattened onto the ground plane."""
        return np.array([-math.sin(self.yaw), 0.0, -math.cos(self.yaw)])

    def right(self):
        return np.array([math.cos(self.yaw), 0.0, -math.sin(self.yaw)])

    def view_matrix(self):
        return (m3.rotate_x(-self.pitch)
                @ m3.rotate_y(-self.yaw)
                @ m3.translate(*(-self.position)))

    def update(self, keys, dt):
        """Move with WASD / Q E, look with the arrow keys. dt = seconds since last frame."""
        speed = MOVE_SPEED * (3 if keys[pygame.K_LSHIFT] else 1) * dt

        if keys[pygame.K_w]:
            self.position += self.forward() * speed
        if keys[pygame.K_s]:
            self.position -= self.forward() * speed
        if keys[pygame.K_d]:
            self.position += self.right() * speed
        if keys[pygame.K_a]:
            self.position -= self.right() * speed
        if keys[pygame.K_e]:
            self.position[1] += speed
        if keys[pygame.K_q]:
            self.position[1] -= speed

        turn = TURN_SPEED * dt
        if keys[pygame.K_LEFT]:
            self.yaw += turn
        if keys[pygame.K_RIGHT]:
            self.yaw -= turn
        if keys[pygame.K_UP]:
            self.pitch += turn
        if keys[pygame.K_DOWN]:
            self.pitch -= turn
        # clamp pitch so the camera can't flip upside down
        self.pitch = max(-PITCH_LIMIT, min(PITCH_LIMIT, self.pitch))