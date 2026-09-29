"""
renderer.py - everything that writes pixels.
Stage 1: Framebuffer + Bresenham lines (moved here from main.py).
Later stages will add triangle filling, the z-buffer and shading here.
"""
import numpy as np


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


def clip_line_liang_barsky(x0, y0, x1, y1, xmin, ymin, xmax, ymax):
    """Liang-Barsky line clipping against a rectangle.

    Writes the segment as P(u) = P0 + u * (P1 - P0), u in [0, 1], and shrinks
    [u_enter, u_exit] with one inequality per rectangle side.
    Returns the clipped endpoints, or None if the line is fully outside.
    """
    dx, dy = x1 - x0, y1 - y0
    p = (-dx, dx, -dy, dy)
    q = (x0 - xmin, xmax - x0, y0 - ymin, ymax - y0)
    u_enter, u_exit = 0.0, 1.0
    for pi, qi in zip(p, q):
        if pi == 0:                 # line parallel to this side
            if qi < 0:              # ...and outside it
                return None
        else:
            u = qi / pi
            if pi < 0:              # entering the rectangle
                u_enter = max(u_enter, u)
            else:                   # leaving the rectangle
                u_exit = min(u_exit, u)
    if u_enter > u_exit:
        return None
    return (x0 + u_enter * dx, y0 + u_enter * dy,
            x0 + u_exit * dx, y0 + u_exit * dy)


def draw_line(fb, x0, y0, x1, y1, rgb):
    """Clip the line to the screen, then rasterize it with Bresenham."""
    clipped = clip_line_liang_barsky(x0, y0, x1, y1, 0, 0, fb.w - 1, fb.h - 1)
    if clipped is None:
        return
    x0, y0, x1, y1 = clipped
    # Snap endpoints to the pixel grid first, otherwise the stop
    # condition may never be exactly true -> infinite loop.
    x0, y0 = int(round(x0)), int(round(y0))
    x1, y1 = int(round(x1)), int(round(y1))

    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy

    while True:
        fb.put(x0, y0, rgb)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy