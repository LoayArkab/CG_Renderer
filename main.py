"""
Software Renderer - Stage 3: interactive fly camera + line clipping.

Keys:
  W A S D   move          Q / E   down / up        Shift   move faster
  Arrows    look around   R       reset camera
  P  perspective / orthographic      O  pyramid spin / orbit
  C  save screenshot                 Esc quit
"""
import os

import numpy as np
import pygame

import math3d as m3
from camera import Camera
from renderer import Framebuffer, draw_line

W, H = 320, 240
SCALE = 3
NEAR, FAR = 0.1, 100.0

CUBE_VERTS = np.array([
    [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],   # back face  (z = -1)
    [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1],       # front face (z = +1)
], dtype=float)

CUBE_EDGES = [
    (0, 1), (1, 2), (2, 3), (3, 0),   # back square
    (4, 5), (5, 6), (6, 7), (7, 4),   # front square
    (0, 4), (1, 5), (2, 6), (3, 7),   # connectors
]

PYRAMID_VERTS = np.array([
    [-1, -1, -1], [1, -1, -1], [1, -1, 1], [-1, -1, 1],   # square base (y = -1)
    [0, 1.2, 0],                                          # apex
], dtype=float)

PYRAMID_EDGES = [
    (0, 1), (1, 2), (2, 3), (3, 0),   # base square
    (0, 4), (1, 4), (2, 4), (3, 4),   # edges up to the apex
]


def make_grid(size=10, y=-2.0):
    """A floor grid of lines from -size to +size on the plane at height y."""
    verts, edges = [], []
    for i in range(-size, size + 1):
        verts += [[i, y, -size], [i, y, size]]       # line along Z
        edges.append((len(verts) - 2, len(verts) - 1))
        verts += [[-size, y, i], [size, y, i]]       # line along X
        edges.append((len(verts) - 2, len(verts) - 1))
    return np.array(verts, dtype=float), edges


GRID_VERTS, GRID_EDGES = make_grid()


def draw_wireframe(fb, verts, edges, mvp, rgb):
    clip = m3.transform_points(mvp, verts)
    for a, b in edges:
        segment = m3.clip_segment_near(clip[a], clip[b], NEAR)   # 3D clipping
        if segment is None:
            continue
        p0, p1 = m3.to_screen(np.array(segment), fb.w, fb.h)
        draw_line(fb, p0[0], p0[1], p1[0], p1[1], rgb)            # 2D clipping inside


def main():
    pygame.init()
    window = pygame.display.set_mode((W * SCALE, H * SCALE))
    clock = pygame.time.Clock()
    fb = Framebuffer(W, H)

    aspect = W / H
    persp = m3.perspective(60, aspect, NEAR, FAR)
    ortho = m3.orthographic(-3 * aspect, 3 * aspect, -3, 3, NEAR, FAR)
    use_perspective = True
    pyramid_orbits = False
    camera = Camera(position=(0, 0, 6))
    shot = 0

    t = 0.0
    running = True
    while running:
        dt = clock.tick(60) / 1000.0     # seconds since last frame

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    running = False
                elif e.key == pygame.K_p:
                    use_perspective = not use_perspective
                elif e.key == pygame.K_o:
                    pyramid_orbits = not pyramid_orbits
                elif e.key == pygame.K_r:
                    camera.reset()
                elif e.key == pygame.K_c:
                    os.makedirs("screenshots", exist_ok=True)
                    shot += 1
                    pygame.image.save(window, f"screenshots/stage3_{shot}.png")

        camera.update(pygame.key.get_pressed(), dt)

        proj = persp if use_perspective else ortho
        view = camera.view_matrix()
        vp = proj @ view                 # shared by every object this frame

        cube_model = m3.translate(-1.8, 0, 0) @ m3.rotate_y(t) @ m3.rotate_x(t * 0.7)
        if pyramid_orbits:
            pyr_model = m3.rotate_y(-t) @ m3.translate(1.8, 0, 0)    # orbit
        else:
            pyr_model = m3.translate(1.8, 0, 0) @ m3.rotate_y(-t)    # spin in place

        fb.clear((10, 10, 20))
        draw_wireframe(fb, GRID_VERTS, GRID_EDGES, vp, (40, 60, 90))
        draw_wireframe(fb, CUBE_VERTS, CUBE_EDGES, vp @ cube_model, (0, 255, 255))
        draw_wireframe(fb, PYRAMID_VERTS, PYRAMID_EDGES, vp @ pyr_model, (255, 140, 0))

        surf = pygame.surfarray.make_surface(fb.color)
        window.blit(pygame.transform.scale(surf, window.get_size()), (0, 0))
        x, y, z = camera.position
        mode = "Persp" if use_perspective else "Ortho"
        pygame.display.set_caption(
            f"Stage 3 | {mode} | cam ({x:.1f}, {y:.1f}, {z:.1f}) | {clock.get_fps():.0f} FPS")
        pygame.display.flip()

        t += dt

    pygame.quit()


if __name__ == "__main__":
    main()