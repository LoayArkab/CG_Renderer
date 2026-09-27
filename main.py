"""
Software Renderer - Stage 1: Framebuffer + Bresenham line rasterization.

We render into our OWN pixel buffer (a numpy array) and only use pygame
to show that buffer on screen. Every pixel is decided by our code.
"""
import math

import numpy as np
import pygame

W, H = 320, 240   # internal render resolution (small = fast in Python)
SCALE = 3         # window is W*SCALE x H*SCALE, pixels get upscaled


class Framebuffer:
    def __init__(self, w, h):
        self.w, self.h = w, h
        # pygame.surfarray expects shape (width, height, 3), indexed [x, y]
        self.color = np.zeros((w, h, 3), dtype=np.uint8)

    def clear(self, rgb=(0, 0, 0)):
        self.color[:] = rgb

    def put(self, x, y, rgb):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.color[x, y] = rgb


def draw_line(fb, x0, y0, x1, y1, rgb):
    """Bresenham's line algorithm (integer-only, works in all 8 octants)."""
    # Snap endpoints to the pixel grid FIRST. With float endpoints the
    # stop condition (x0 == x1 and y0 == y1) may never be true -> infinite loop.
    x0, y0 = int(round(x0)), int(round(y0))
    x1, y1 = int(round(x1)), int(round(y1))

    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy  # error term: tracks distance from the ideal line

    while True:
        fb.put(x0, y0, rgb)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:   # step in x
            err += dy
            x0 += sx
        if e2 <= dx:   # step in y
            err += dx
            y0 += sy


def main():
    pygame.init()
    screen = pygame.display.set_mode((W * SCALE, H * SCALE))
    pygame.display.set_caption("Software Renderer - Stage 1 (Bresenham)")
    clock = pygame.time.Clock()
    fb = Framebuffer(W, H)

    t = 0.0
    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                running = False

        fb.clear((10, 10, 20))

        # "Spoke test": lines in every direction check all 8 octants
        cx, cy, r = W // 2, H // 2, 100
        spokes = 24
        for i in range(spokes):
            a = t + i * 2 * math.pi / spokes
            x1 = cx + r * math.cos(a)
            y1 = cy + r * math.sin(a)
            color = (int(128 + 127 * math.cos(a)),
                     int(128 + 127 * math.sin(a)),
                     200)
            draw_line(fb, cx, cy, x1, y1, color)

        surf = pygame.surfarray.make_surface(fb.color)
        screen.blit(pygame.transform.scale(surf, screen.get_size()), (0, 0))
        pygame.display.flip()

        t += 0.01
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()