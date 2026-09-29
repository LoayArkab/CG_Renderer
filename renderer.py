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


def draw_wireframe(fb, vertices, edges, mvp, rgb, near):
    """Project all vertices ONCE, then rasterize every edge.

    Edges fully in front of the near plane (the common case) use the
    already-projected points. Only edges crossing the near plane are clipped.
    """
    import math3d as m3   # local import keeps renderer independent of the math module

    edges = np.asarray(edges)
    clip = m3.transform_points(mvp, vertices)
    screen = m3.to_screen(clip, fb.w, fb.h)
    w = clip[:, 3]
    front_a = w[edges[:, 0]] >= near
    front_b = w[edges[:, 1]] >= near

    pts = screen.tolist()                       # plain Python lists are faster to index
    for a, b in edges[front_a & front_b].tolist():
        draw_line(fb, pts[a][0], pts[a][1], pts[b][0], pts[b][1], rgb)

    for a, b in edges[front_a ^ front_b].tolist():   # exactly one endpoint behind
        seg = m3.clip_segment_near(clip[a], clip[b], near)
        p0, p1 = m3.to_screen(np.array(seg), fb.w, fb.h)
        draw_line(fb, p0[0], p0[1], p1[0], p1[1], rgb)


# ---------------------------------------------------------------------------
# Stage 5: filled triangles
# ---------------------------------------------------------------------------

def edge_function(ax, ay, bx, by, px, py):
    """Twice the signed area of triangle (A, B, P).
    Its sign tells on which side of the line A->B the point P lies."""
    return (bx - ax) * (py - ay) - (by - ay) * (px - ax)


def fill_triangle(fb, x0, y0, x1, y1, x2, y2, rgb):
    """Rasterize a triangle with the edge-function (barycentric) method.

    1. Take the triangle's bounding box, clipped to the screen.
    2. For the CENTER of every pixel in the box, evaluate the three edge functions.
    3. The pixel is inside if all three have the same sign as the whole triangle.
    numpy evaluates all pixels of the box at once instead of one by one.
    """
    xmin = max(int(np.floor(min(x0, x1, x2))), 0)
    xmax = min(int(np.ceil(max(x0, x1, x2))), fb.w - 1)
    ymin = max(int(np.floor(min(y0, y1, y2))), 0)
    ymax = min(int(np.ceil(max(y0, y1, y2))), fb.h - 1)
    if xmin > xmax or ymin > ymax:
        return                                           # completely off-screen

    area = edge_function(x0, y0, x1, y1, x2, y2)
    if area == 0:
        return                                           # degenerate (a line)

    px = np.arange(xmin, xmax + 1)[:, None] + 0.5        # pixel centers, column
    py = np.arange(ymin, ymax + 1)[None, :] + 0.5        # pixel centers, row
    w0 = edge_function(x1, y1, x2, y2, px, py)           # (nx, ny) arrays
    w1 = edge_function(x2, y2, x0, y0, px, py)
    w2 = edge_function(x0, y0, x1, y1, px, py)

    if area > 0:
        inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
    else:
        inside = (w0 <= 0) & (w1 <= 0) & (w2 <= 0)

    fb.color[xmin:xmax + 1, ymin:ymax + 1][inside] = rgb


def draw_meshes_filled(fb, items, vp, near, cull=True, outline=False):
    """Draw solid meshes with back-face culling and the PAINTER'S ALGORITHM.

    items: list of (mesh, model_matrix).
    Triangles from ALL meshes are collected, sorted far-to-near by their
    average depth, and painted in that order so nearer ones cover farther ones.
    Returns (triangles drawn, triangles culled).
    """
    import math3d as m3

    all_pts, all_depth, all_col = [], [], []
    culled = 0
    for mesh, model in items:
        clip = m3.transform_points(vp @ model, mesh.vertices)
        scr = m3.to_screen(clip, fb.w, fb.h)[:, :2]
        tri = mesh.triangles
        w = clip[:, 3]

        # simple near-plane handling: drop triangles with a corner behind the camera
        keep = (w[tri] >= near).all(axis=1)

        a, b, c = scr[tri[:, 0]], scr[tri[:, 1]], scr[tri[:, 2]]
        # signed area on screen. Front faces are counter-clockwise in the
        # y-up world, which becomes clockwise on the y-down screen -> negative.
        signed = ((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1])
                  - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0]))
        if cull:
            front = signed < 0
            culled += int((keep & ~front).sum())
            keep &= front

        all_pts.append(np.stack([a, b, c], axis=1)[keep])     # (k, 3, 2)
        all_depth.append(w[tri].mean(axis=1)[keep])           # distance from camera
        all_col.append(mesh.tri_colors[keep])

    pts = np.concatenate(all_pts)
    depth = np.concatenate(all_depth)
    cols = np.concatenate(all_col)

    order = np.argsort(-depth)                                 # farthest first
    for (p0, p1, p2), col in zip(pts[order].tolist(), cols[order].tolist()):
        fill_triangle(fb, p0[0], p0[1], p1[0], p1[1], p2[0], p2[1], col)
        if outline:
            dark = (20, 20, 30)
            draw_line(fb, p0[0], p0[1], p1[0], p1[1], dark)
            draw_line(fb, p1[0], p1[1], p2[0], p2[1], dark)
            draw_line(fb, p2[0], p2[1], p0[0], p0[1], dark)

    return len(order), culled