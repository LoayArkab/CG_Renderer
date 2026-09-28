"""
Software Renderer - Stage 2: 3D transformation pipeline + wireframe cube.

Pipeline per vertex:
  object space --model--> world --view--> camera --projection--> clip
  --divide by w--> NDC --viewport--> screen pixels --Bresenham--> lines
Keys:  P = toggle perspective / orthographic
       O = toggle pyramid transform order (spin in place / orbit)
       Esc = quit
"""
import numpy as np
import pygame
import os
import math3d as m3
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


def draw_wireframe(fb, verts, edges, mvp, rgb):
    clip = m3.transform_points(mvp, verts)
    screen = m3.to_screen(clip, fb.w, fb.h)
    in_front = clip[:, 3] > NEAR       # skip points behind the camera
    for a, b in edges:
        if in_front[a] and in_front[b]:
            draw_line(fb, screen[a, 0], screen[a, 1], screen[b, 0], screen[b, 1], rgb)


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

    view = m3.translate(0, 0, -6)      # move the world 6 units away from the camera
    t = 0.0
    running = True
    while running:
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
                elif e.key == pygame.K_s:
                    os.makedirs("screenshots", exist_ok=True)
                    mode_name = "perspective" if use_perspective else "orthographic"
                    pygame.image.save(window, f"screenshots/stage2_{mode_name}.png")

        proj = persp if use_perspective else ortho
        # Cube: spin around its own center first, THEN move it to the left.
        cube_model = m3.translate(-1.8, 0, 0) @ m3.rotate_y(t) @ m3.rotate_x(t * 0.7)

        # Pyramid: same two matrices, different order -> different motion.
        if pyramid_orbits:
            # translate first, then rotate around the WORLD origin -> orbit
            pyr_model = m3.rotate_y(-t) @ m3.translate(1.8, 0, 0)
        else:
            # rotate first (around its own center), then translate -> spin in place
            pyr_model = m3.translate(1.8, 0, 0) @ m3.rotate_y(-t)

        fb.clear((10, 10, 20))
        # rightmost matrix is applied first: model, then view, then projection
        draw_wireframe(fb, CUBE_VERTS, CUBE_EDGES, proj @ view @ cube_model, (0, 255, 255))
        draw_wireframe(fb, PYRAMID_VERTS, PYRAMID_EDGES, proj @ view @ pyr_model, (255, 140, 0))

        surf = pygame.surfarray.make_surface(fb.color)
        window.blit(pygame.transform.scale(surf, window.get_size()), (0, 0))
        mode = "Perspective" if use_perspective else "Orthographic"
        order = "orbit" if pyramid_orbits else "spin"
        pygame.display.set_caption(
            f"Stage 2 | {mode} | pyramid: {order} | {clock.get_fps():.0f} FPS")
        pygame.display.flip()

        t += 0.015
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()