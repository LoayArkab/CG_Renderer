"""
lighting.py - the Blinn-Phong reflection model, vectorized with numpy.

For a surface point with normal N, lit by a directional light coming from
direction L, seen from direction V (toward the camera):

  color = base * (ambient + kd * max(N.L, 0))  +  white * ks * max(N.H, 0)^shininess
  where H = normalize(L + V) is the "half vector" between light and view.
"""
import numpy as np

AMBIENT = 0.15      # light that reaches everything (fakes indirect bounces)
KD = 0.85           # diffuse strength (matte, Lambert)
KS = 0.45           # specular strength (shiny highlight)
SHININESS = 32      # higher = smaller, sharper highlight


def normalize(v):
    v = np.asarray(v, dtype=float)
    length = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.where(length == 0, 1, length)


def blinn_phong(normals, positions, base_color, camera_pos, light_dir):
    """normals, positions: (n, 3) arrays in WORLD space.
    base_color: (r, g, b) 0..255.  light_dir: unit vector pointing TOWARD the light.
    Returns (n, 3) float colors in 0..255."""
    n = normalize(normals)
    l = np.asarray(light_dir, dtype=float)
    v = normalize(np.asarray(camera_pos) - positions)
    h = normalize(l + v)

    n_dot_l = np.clip(n @ l, 0.0, None)                     # Lambert's cosine law
    n_dot_h = np.clip(np.einsum("ij,ij->i", n, h), 0.0, None)
    spec = np.where(n_dot_l > 0, n_dot_h ** SHININESS, 0.0)  # no highlight on the dark side

    base = np.asarray(base_color, dtype=float)
    color = base * (AMBIENT + KD * n_dot_l)[:, None] + 255.0 * KS * spec[:, None]
    return np.clip(color, 0, 255)