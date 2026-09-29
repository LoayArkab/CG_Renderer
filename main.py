"""
Software Renderer - Stage 4: loading real 3D models from .obj files.

Keys:
  W A S D   move          Q / E   down / up        Shift   move faster
  Arrows    look around   R       reset camera
  M  next model           Space   pause / resume rotation
  P  perspective / orthographic      O  pyramid spin / orbit (shapes scene)
  C  save screenshot                 Esc quit
"""
import os

import numpy as np
import pygame

import math3d as m3
from camera import Camera
from obj_loader import load_obj
from renderer import Framebuffer, draw_wireframe

W, H = 320, 240
SCALE = 3
NEAR, FAR = 0.1, 100.0
MODEL_FILES = ["models/suzanne.obj", "models/teapot.obj", "models/spot.obj"]

CUBE_VERTS = np.array([
    [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
    [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1],
], dtype=float)
CUBE_EDGES = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6),
              (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]

PYRAMID_VERTS = np.array([
    [-1, -1, -1], [1, -1, -1], [1, -1, 1], [-1, -1, 1], [0, 1.2, 0],
], dtype=float)
PYRAMID_EDGES = [(0, 1), (1, 2), (2, 3), (3, 0), (0, 4), (1, 4), (2, 4), (3, 4)]


def make_grid(size=10, y=-2.0):
    verts, edges = [], []
    for i in range(-size, size + 1):
        verts += [[i, y, -size], [i, y, size]]
        edges.append((len(verts) - 2, len(verts) - 1))
        verts += [[-size, y, i], [size, y, i]]
        edges.append((len(verts) - 2, len(verts) - 1))
    return np.array(verts, dtype=float), edges


GRID_VERTS, GRID_EDGES = make_grid()


def main():
    pygame.init()
    window = pygame.display.set_mode((W * SCALE, H * SCALE))
    clock = pygame.time.Clock()
    fb = Framebuffer(W, H)

    meshes = [load_obj(path) for path in MODEL_FILES]
    for mesh in meshes:
        print("Loaded", mesh)
    scene = 0                        # 0 = cube and pyramid, 1.. = loaded meshes

    aspect = W / H
    persp = m3.perspective(60, aspect, NEAR, FAR)
    ortho = m3.orthographic(-3 * aspect, 3 * aspect, -3, 3, NEAR, FAR)
    use_perspective = True
    pyramid_orbits = False
    paused = False
    camera = Camera(position=(0, 0, 6))
    shot = 0

    t = 0.0
    running = True
    while running:
        dt = clock.tick(60) / 1000.0

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
                elif e.key == pygame.K_m:
                    scene = (scene + 1) % (len(meshes) + 1)
                elif e.key == pygame.K_SPACE:
                    paused = not paused
                elif e.key == pygame.K_c:
                    os.makedirs("screenshots", exist_ok=True)
                    shot += 1
                    pygame.image.save(window, f"screenshots/stage4_{shot}.png")

        camera.update(pygame.key.get_pressed(), dt)
        if not paused:
            t += dt

        proj = persp if use_perspective else ortho
        vp = proj @ camera.view_matrix()

        fb.clear((10, 10, 20))
        draw_wireframe(fb, GRID_VERTS, GRID_EDGES, vp, (40, 60, 90), NEAR)

        if scene == 0:
            name, info = "shapes", ""
            cube_model = m3.translate(-1.8, 0, 0) @ m3.rotate_y(t) @ m3.rotate_x(t * 0.7)
            if pyramid_orbits:
                pyr_model = m3.rotate_y(-t) @ m3.translate(1.8, 0, 0)
            else:
                pyr_model = m3.translate(1.8, 0, 0) @ m3.rotate_y(-t)
            draw_wireframe(fb, CUBE_VERTS, CUBE_EDGES, vp @ cube_model, (0, 255, 255), NEAR)
            draw_wireframe(fb, PYRAMID_VERTS, PYRAMID_EDGES, vp @ pyr_model, (255, 140, 0), NEAR)
        else:
            mesh = meshes[scene - 1]
            name = mesh.name
            info = f" | {len(mesh.vertices)} v, {len(mesh.triangles)} tris"
            model = m3.rotate_y(t * 0.5) @ m3.scale(1.8, 1.8, 1.8)
            draw_wireframe(fb, mesh.vertices, mesh.edges, vp @ model, (0, 255, 160), NEAR)

        surf = pygame.surfarray.make_surface(fb.color)
        window.blit(pygame.transform.scale(surf, window.get_size()), (0, 0))
        mode = "Persp" if use_perspective else "Ortho"
        pygame.display.set_caption(
            f"Stage 4 | {name}{info} | {mode} | {clock.get_fps():.0f} FPS")
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()