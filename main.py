"""
Software Renderer - Stage 6: the z-buffer.

Keys:
  W A S D   move          Q / E   down / up        Shift   move faster
  Arrows    look around   R       reset camera
  M  next model           Space   pause / resume rotation
  F  render mode: wireframe / filled / filled + outline / depth view
  Z  hidden surfaces: z-buffer / painter's algorithm
  B  back-face culling on / off
  P  perspective / orthographic      O  pyramid spin / orbit (shapes scene)
  C  save screenshot                 Esc quit
"""
import os
import time

import numpy as np
import pygame

import math3d as m3
from camera import Camera
from obj_loader import load_obj, make_cube, make_pyramid
from renderer import Framebuffer, depth_to_image, draw_meshes_filled, draw_wireframe

W, H = 320, 240
SCALE = 3
NEAR, FAR = 0.1, 100.0
MODEL_FILES = ["models/suzanne.obj", "models/teapot.obj", "models/spot.obj"]
MODES = ["wireframe", "filled", "filled + outline", "depth view"]


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

    cube, pyramid = make_cube(), make_pyramid()
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
    mode = 1
    cull = True
    use_zbuffer = True
    camera = Camera(position=(0, 0, 6))

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
                elif e.key == pygame.K_f:
                    mode = (mode + 1) % len(MODES)
                elif e.key == pygame.K_z:
                    use_zbuffer = not use_zbuffer
                elif e.key == pygame.K_b:
                    cull = not cull
                elif e.key == pygame.K_c:
                    os.makedirs("screenshots", exist_ok=True)
                    pygame.image.save(
                        window, f"screenshots/stage6_{time.strftime('%H%M%S')}.png")

        camera.update(pygame.key.get_pressed(), dt)
        if not paused:
            t += dt

        proj = persp if use_perspective else ortho
        vp = proj @ camera.view_matrix()

        if scene == 0:
            cube_model = m3.translate(-1.8, 0, 0) @ m3.rotate_y(t) @ m3.rotate_x(t * 0.7)
            if pyramid_orbits:
                pyr_model = m3.rotate_y(-t) @ m3.translate(1.8, 0, 0)
            else:
                pyr_model = m3.translate(1.8, 0, 0) @ m3.rotate_y(-t)
            items = [(cube, cube_model), (pyramid, pyr_model)]
            name = "shapes"
        else:
            mesh = meshes[scene - 1]
            items = [(mesh, m3.rotate_y(t * 0.5) @ m3.scale(1.8, 1.8, 1.8))]
            name = f"{mesh.name} ({len(mesh.triangles)} tris)"

        fb.clear((10, 10, 20))
        if MODES[mode] != "depth view":
            draw_wireframe(fb, GRID_VERTS, GRID_EDGES, vp, (40, 60, 90), NEAR)

        if MODES[mode] == "wireframe":
            for mesh, model in items:
                draw_wireframe(fb, mesh.vertices, mesh.edges, vp @ model, (0, 255, 160), NEAR)
            stats = ""
        else:
            depth_mode = MODES[mode] == "depth view"
            zbuf = use_zbuffer or depth_mode              # depth view needs the z-buffer
            drawn, culled = draw_meshes_filled(
                fb, items, vp, NEAR, cull,
                outline=(MODES[mode] == "filled + outline"), use_zbuffer=zbuf)
            if depth_mode:
                depth_to_image(fb, NEAR, FAR, use_perspective)
            stats = f" | {'z-buffer' if zbuf else 'painter'} | drawn {drawn}, culled {culled}"

        surf = pygame.surfarray.make_surface(fb.color)
        window.blit(pygame.transform.scale(surf, window.get_size()), (0, 0))
        proj_name = "Persp" if use_perspective else "Ortho"
        cull_name = "cull ON" if cull else "cull OFF"
        pygame.display.set_caption(
            f"Stage 6 | {name} | {MODES[mode]}{stats} | {cull_name} | "
            f"{proj_name} | {clock.get_fps():.0f} FPS")
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()