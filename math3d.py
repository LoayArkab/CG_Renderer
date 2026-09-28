"""
math3d.py - 4x4 matrices in homogeneous coordinates.

Convention: points are column vectors, so a transform is applied as  M @ p
and a chain  A @ B @ C  applies C first, then B, then A.
The camera looks down the -Z axis (same as OpenGL).
"""
import math

import numpy as np


def identity():
    return np.eye(4)


def translate(tx, ty, tz):
    m = np.eye(4)
    m[:3, 3] = (tx, ty, tz)
    return m


def scale(sx, sy, sz):
    return np.diag([sx, sy, sz, 1.0])


def rotate_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0, 0],
                     [0, c, -s, 0],
                     [0, s, c, 0],
                     [0, 0, 0, 1]], dtype=float)


def rotate_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s, 0],
                     [0, 1, 0, 0],
                     [-s, 0, c, 0],
                     [0, 0, 0, 1]], dtype=float)


def rotate_z(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0, 0],
                     [s, c, 0, 0],
                     [0, 0, 1, 0],
                     [0, 0, 0, 1]], dtype=float)


def perspective(fov_deg, aspect, near, far):
    """Perspective projection: distant things get smaller (after dividing by w)."""
    f = 1.0 / math.tan(math.radians(fov_deg) / 2)
    m = np.zeros((4, 4))
    m[0, 0] = f / aspect
    m[1, 1] = f
    m[2, 2] = (far + near) / (near - far)
    m[2, 3] = 2 * far * near / (near - far)
    m[3, 2] = -1.0          # this row copies -z into w -> the perspective divide
    return m


def orthographic(left, right, bottom, top, near, far):
    """Orthographic projection: parallel lines stay parallel, no size change with depth."""
    m = np.eye(4)
    m[0, 0] = 2 / (right - left)
    m[1, 1] = 2 / (top - bottom)
    m[2, 2] = -2 / (far - near)
    m[0, 3] = -(right + left) / (right - left)
    m[1, 3] = -(top + bottom) / (top - bottom)
    m[2, 3] = -(far + near) / (far - near)
    return m


def transform_points(m, pts):
    """Apply a 4x4 matrix to an (N, 3) array of points. Returns (N, 4) clip coords."""
    homogeneous = np.hstack([pts, np.ones((len(pts), 1))])
    return homogeneous @ m.T


def to_screen(clip, width, height):
    """Perspective divide (clip -> NDC) then viewport transform (NDC -> pixels)."""
    w = clip[:, 3:4]
    w = np.where(np.abs(w) < 1e-9, 1e-9, w)       # avoid division by zero
    ndc = clip[:, :3] / w                          # each coordinate now in [-1, 1]
    sx = (ndc[:, 0] + 1) * 0.5 * width
    sy = (1 - ndc[:, 1]) * 0.5 * height            # flip: screen y grows downward
    return np.stack([sx, sy, ndc[:, 2]], axis=1)