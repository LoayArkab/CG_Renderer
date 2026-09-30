"""
Rasterization from Scratch - a 3D software renderer in Python.
Stage 8: on-screen display (HUD), help overlay and supersampling anti-aliasing.

Keys:
  W A S D   move          Q / E   down / up        Shift   move faster
  Arrows    look around   R       reset camera
  M  next model           Space   pause / resume rotation
  F  render mode: wireframe / filled / filled + outline / depth view
  L  shading: face colors / flat / Gouraud / Phong
  K  light orbits on / off
  Z  hidden surfaces: z-buffer / painter's algorithm
  B  back-face culling on / off
  X  anti-aliasing (2x2 supersampling) on / off
  P  perspective / orthographic      O  pyramid spin / orbit (shapes scene)
  H  show / hide help                C  save screenshot       Esc quit
"""
import os
import time

import numpy as np
import pygame

import math3d as m3
from camera import Camera
from lighting import normalize
from obj_loader import load_obj, make_cube, make_pyramid
from renderer import (Framebuffer, depth_to_image, downsample,
                      draw_meshes_filled, draw_wireframe)

W, H = 320, 240
SCALE = 3
AA_FACTOR = 2
NEAR, FAR = 0.1, 100.0
MODEL_FILES = ["models/suzanne.obj", "models/teapot.obj", "models/spot.obj"]
MODES = ["wireframe", "filled", "filled + outline", "depth view"]
SHADINGS = ["faces", "flat", "gouraud", "phong"]
BASE_LIGHT = normalize([-0.4, 0.5, 0.8])      # direction TOWARD the light
MATERIALS = {"cube": (70, 190, 255), "pyramid": (255, 140, 50),
             "suzanne": (235, 150, 60), "teapot": (190, 200, 225), "spot": (240, 215, 195)}

HELP_LINES = [
    "CONTROLS",
    "W A S D / Q E   move          Shift  faster",
    "Arrow keys      look around   R      reset camera",
    "M      next model             Space  pause rotation",
    "F      render mode            L      shading",
    "Z      z-buffer / painter     B      back-face culling",
    "X      anti-aliasing          K      orbiting light",
    "P      perspective / ortho    O      spin / orbit",
    "C      screenshot             H      hide help",
]


def make_grid(size=10, y=-2.0):
    verts, edges = [], []
    for i in range(-size, size + 1):
        verts += [[i, y, -size], [i, y, size]]
        edges.append((len(verts) - 2, len(verts) - 1))
        verts += [[-size, y, i], [size, y, i]]
        edges.append((len(verts) - 2, len(verts) - 1))
    return np.array(verts, dtype=float), edges


GRID_VERTS, GRID_EDGES = make_grid()


def draw_panel(window, font, lines, pos, color=(230, 230, 240)):
    """Draw lines of text on a semi-transparent dark box."""
    rendered = [font.render(line, True, color) for line in lines]
    width = max(r.get_width() for r in rendered) + 16
    height = sum(r.get_height() for r in rendered) + 12
    panel = pygame.Surface((width, height), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 160))
    window.blit(panel, pos)
    y = pos[1] + 6
    for r in rendered:
        window.blit(r, (pos[0] + 8, y))
        y += r.get_height()


def render_scene(fb, items, vp, s):
    """Draw one frame into framebuffer fb. s = dict with the current settings."""
    fb.clear((10, 10, 20))
    mode = MODES[s["mode"]]
    if mode != "depth view":
        draw_wireframe(fb, GRID_VERTS, GRID_EDGES, vp, (40, 60, 90), NEAR)

    if mode == "wireframe":
        for mesh, model in items:
            draw_wireframe(fb, mesh.vertices, mesh.edges, vp @ model, (0, 255, 160), NEAR)
        return 0, 0

    zbuf = s["zbuffer"] or mode == "depth view"           # depth view needs the z-buffer
    drawn, culled = draw_meshes_filled(
        fb, items, vp, NEAR, s["cull"],
        outline=(mode == "filled + outline"), use_zbuffer=zbuf,
        shading=SHADINGS[s["shading"]], camera_pos=s["camera_pos"], light_dir=s["light_dir"])
    if mode == "depth view":
        depth_to_image(fb, NEAR, FAR, s["perspective"])
    return drawn, culled


def main():
    pygame.init()
    window = pygame.display.set_mode((W * SCALE, H * SCALE))
    pygame.display.set_caption("Rasterization from Scratch - 3D Software Renderer")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 24)

    fb = Framebuffer(W, H)                                  # final image
    fb_aa = Framebuffer(W * AA_FACTOR, H * AA_FACTOR)       # high-res samples for SSAA

    cube, pyramid = make_cube(), make_pyramid()
    meshes = [load_obj(path) for path in MODEL_FILES]
    for mesh in [cube, pyramid] + meshes:
        mesh.base_color = MATERIALS.get(mesh.name, (200, 200, 200))
    for mesh in meshes:
        print("Loaded", mesh)

    aspect = W / H
    persp = m3.perspective(60, aspect, NEAR, FAR)
    ortho = m3.orthographic(-3 * aspect, 3 * aspect, -3, 3, NEAR, FAR)
    camera = Camera(position=(0, 0, 6))

    s = dict(mode=1, shading=3, zbuffer=True, cull=True, perspective=True)
    scene = 0                      # 0 = cube and pyramid, 1.. = loaded meshes
    pyramid_orbits = False
    paused = False
    light_orbits = False
    light_angle = 0.0
    antialias = False
    show_help = True

    t = 0.0
    running = True
    while running:
        dt = clock.tick(60) / 1000.0

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                k = e.key
                if k == pygame.K_ESCAPE:
                    running = False
                elif k == pygame.K_p:
                    s["perspective"] = not s["perspective"]
                elif k == pygame.K_o:
                    pyramid_orbits = not pyramid_orbits
                elif k == pygame.K_r:
                    camera.reset()
                elif k == pygame.K_m:
                    scene = (scene + 1) % (len(meshes) + 1)
                elif k == pygame.K_SPACE:
                    paused = not paused
                elif k == pygame.K_f:
                    s["mode"] = (s["mode"] + 1) % len(MODES)
                elif k == pygame.K_l:
                    s["shading"] = (s["shading"] + 1) % len(SHADINGS)
                elif k == pygame.K_k:
                    light_orbits = not light_orbits
                elif k == pygame.K_z:
                    s["zbuffer"] = not s["zbuffer"]
                elif k == pygame.K_b:
                    s["cull"] = not s["cull"]
                elif k == pygame.K_x:
                    antialias = not antialias
                elif k == pygame.K_h:
                    show_help = not show_help
                elif k == pygame.K_c:
                    os.makedirs("screenshots", exist_ok=True)
                    pygame.image.save(
                        window, f"screenshots/stage8_{time.strftime('%H%M%S')}.png")

        camera.update(pygame.key.get_pressed(), dt)
        if not paused:
            t += dt
        if light_orbits:
            light_angle += dt
        s["light_dir"] = m3.rotate_y(light_angle)[:3, :3] @ BASE_LIGHT
        s["camera_pos"] = camera.position

        proj = persp if s["perspective"] else ortho
        vp = proj @ camera.view_matrix()

        if scene == 0:
            cube_model = m3.translate(-1.8, 0, 0) @ m3.rotate_y(t) @ m3.rotate_x(t * 0.7)
            if pyramid_orbits:
                pyr_model = m3.rotate_y(-t) @ m3.translate(1.8, 0, 0)
            else:
                pyr_model = m3.translate(1.8, 0, 0) @ m3.rotate_y(-t)
            items = [(cube, cube_model), (pyramid, pyr_model)]
            name, tris = "cube + pyramid", len(cube.triangles) + len(pyramid.triangles)
        else:
            mesh = meshes[scene - 1]
            items = [(mesh, m3.rotate_y(t * 0.5) @ m3.scale(1.8, 1.8, 1.8))]
            name, tris = mesh.name, len(mesh.triangles)

        # ---- render ----
        if antialias:
            drawn, culled = render_scene(fb_aa, items, vp, s)   # 4 samples per pixel
            downsample(fb_aa, fb, AA_FACTOR)                     # average them
        else:
            drawn, culled = render_scene(fb, items, vp, s)

        surf = pygame.surfarray.make_surface(fb.color)
        window.blit(pygame.transform.scale(surf, window.get_size()), (0, 0))

        # ---- on-screen display ----
        mode = MODES[s["mode"]]
        status = [
            f"Model: {name}  ({tris} triangles)",
            f"Mode: {mode}"
            + ("" if mode in ("wireframe", "depth view") else f"   Shading: {SHADINGS[s['shading']]}"),
            f"Hidden surfaces: {'z-buffer' if s['zbuffer'] or mode == 'depth view' else 'painter'}"
            f"   Culling: {'on' if s['cull'] else 'off'}",
            f"Projection: {'perspective' if s['perspective'] else 'orthographic'}"
            f"   Anti-aliasing: {'2x2 SSAA' if antialias else 'off'}",
            (f"Drawn {drawn} / culled {culled} triangles   " if mode != "wireframe" else "")
            + f"{clock.get_fps():.0f} FPS",
        ]
        draw_panel(window, font, status, (10, 10))
        if show_help:
            draw_panel(window, font, HELP_LINES, (10, window.get_height() - 230))
        else:
            draw_panel(window, font, ["H: help"], (10, window.get_height() - 36))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()