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
        # z-buffer: depth of the nearest surface drawn so far at each pixel
        self.depth = np.full((w, h), np.inf)

    def clear(self, rgb=(0, 0, 0)):
        self.color[:] = rgb
        self.depth[:] = np.inf          # "nothing drawn yet" = infinitely far

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
# Stages 5-6: filled triangles, painter's algorithm and the z-buffer
# ---------------------------------------------------------------------------

OUTLINE_COLOR = (20, 20, 30)
OUTLINE_WIDTH = 0.8        # in pixels


def edge_function(ax, ay, bx, by, px, py):
    """Twice the signed area of triangle (A, B, P).
    Its sign tells on which side of the line A->B the point P lies."""
    return (bx - ax) * (py - ay) - (by - ay) * (px - ax)


def fill_triangle(fb, v0, v1, v2, rgb=None, inv_w=None, attrs=None, shader=None,
                  use_depth=True, outline=False):
    """Rasterize one triangle. Each vertex is (screen_x, screen_y, depth_z).

    Coloring, one of:
      rgb             one color for the whole triangle (flat shading, debug colors)
      attrs (3, k)    per-vertex values interpolated across the triangle
                      (colors for Gouraud, normal+position for Phong);
                      shader(values) turns interpolated values into colors.
    inv_w: 1/w of each vertex, for perspective-correct interpolation of attrs.
    """
    (x0, y0, z0), (x1, y1, z1), (x2, y2, z2) = v0, v1, v2

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
    w0 = edge_function(x1, y1, x2, y2, px, py)
    w1 = edge_function(x2, y2, x0, y0, px, py)
    w2 = edge_function(x0, y0, x1, y1, px, py)

    # screen-space barycentric coordinates (positive inside, sum to 1)
    l0, l1, l2 = w0 / area, w1 / area, w2 / area
    inside = (l0 >= 0) & (l1 >= 0) & (l2 >= 0)

    color = fb.color[xmin:xmax + 1, ymin:ymax + 1]
    depth = fb.depth[xmin:xmax + 1, ymin:ymax + 1]

    if use_depth:
        z = l0 * z0 + l1 * z1 + l2 * z2                  # NDC z is linear on screen
        visible = inside & (z < depth)                   # the depth test
        depth[visible] = z[visible]
    else:
        visible = inside
    if not visible.any():
        return

    if attrs is None:
        color[visible] = rgb
    else:
        # perspective-correct interpolation: interpolate attr/w and 1/w
        # linearly on screen, then divide. (Plain screen-space weights
        # would stretch values toward the far part of the triangle.)
        a0 = l0[visible] * inv_w[0]
        a1 = l1[visible] * inv_w[1]
        a2 = l2[visible] * inv_w[2]
        weights = np.stack([a0, a1, a2], axis=1)
        weights /= weights.sum(axis=1, keepdims=True)
        values = weights @ attrs                          # (pixels, k)
        if shader is not None:
            values = shader(values)
        color[visible] = np.clip(values, 0, 255)

    if outline:
        # distance (in pixels) from each pixel to each edge = |w| / edge length
        d0 = np.abs(w0) / np.hypot(x2 - x1, y2 - y1)
        d1 = np.abs(w1) / np.hypot(x0 - x2, y0 - y2)
        d2 = np.abs(w2) / np.hypot(x1 - x0, y1 - y0)
        near_edge = visible & (np.minimum(np.minimum(d0, d1), d2) < OUTLINE_WIDTH)
        color[near_edge] = OUTLINE_COLOR


def draw_meshes_filled(fb, items, vp, near, cull=True, outline=False, use_zbuffer=True,
                       shading="phong", camera_pos=(0, 0, 0), light_dir=(0, 1, 0)):
    """Draw solid meshes with culling, hidden surface removal and lighting.

    items: list of (mesh, model_matrix).
    shading: "faces"   one debug color per polygon (no lighting)
             "flat"    one lit color per triangle, from the face normal
             "gouraud" lighting computed at the vertices, colors interpolated
             "phong"   normals interpolated, lighting computed at every pixel
    Returns (triangles drawn, triangles culled).
    """
    import math3d as m3
    from lighting import blinn_phong

    jobs = []            # (depth, screen verts, kwargs for fill_triangle)
    culled = 0
    for mesh, model in items:
        clip = m3.transform_points(vp @ model, mesh.vertices)
        scr = m3.to_screen(clip, fb.w, fb.h)
        tri = mesh.triangles
        w = clip[:, 3]

        keep = (w[tri] >= near).all(axis=1)
        a, b, c = scr[tri[:, 0]], scr[tri[:, 1]], scr[tri[:, 2]]
        signed = ((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1])
                  - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0]))
        if cull:
            front = signed < 0
            culled += int((keep & ~front).sum())
            keep &= front
        idx = np.nonzero(keep)[0]
        if len(idx) == 0:
            continue

        # lighting happens in WORLD space
        world = m3.transform_points(model, mesh.vertices)[:, :3]
        # normals: rotate with the model's 3x3 part (fine for rotation and
        # uniform scale; non-uniform scale would need the inverse transpose)
        normals = mesh.vertex_normals @ model[:3, :3].T
        t = tri[idx]
        screen_tris = np.stack([a[idx], b[idx], c[idx]], axis=1).tolist()
        tri_depth = w[t].mean(axis=1).tolist()
        inv_w = (1.0 / w[t]).tolist()

        if shading == "faces":
            per_tri = [dict(rgb=tuple(col)) for col in mesh.tri_colors[idx].tolist()]
        elif shading == "flat":
            wa, wb, wc = world[t[:, 0]], world[t[:, 1]], world[t[:, 2]]
            face_n = np.cross(wb - wa, wc - wa)
            centers = (wa + wb + wc) / 3
            cols = blinn_phong(face_n, centers, mesh.base_color, camera_pos, light_dir)
            per_tri = [dict(rgb=tuple(int(v) for v in col)) for col in cols.tolist()]
        elif shading == "gouraud":
            vcols = blinn_phong(normals, world, mesh.base_color, camera_pos, light_dir)
            tri_cols = vcols[t]                                  # (k, 3 corners, 3)
            per_tri = [dict(attrs=tc, inv_w=iw) for tc, iw in zip(tri_cols, inv_w)]
        else:  # phong
            base = mesh.base_color

            def shader(values, base=base):
                return blinn_phong(values[:, :3], values[:, 3:], base, camera_pos, light_dir)

            tri_attrs = np.concatenate([normals[t], world[t]], axis=2)   # (k, 3, 6)
            per_tri = [dict(attrs=ta, inv_w=iw, shader=shader)
                       for ta, iw in zip(tri_attrs, inv_w)]

        for d, sv, kw in zip(tri_depth, screen_tris, per_tri):
            jobs.append((d, sv, kw))

    if not use_zbuffer:
        jobs.sort(key=lambda job: -job[0])        # painter: farthest first

    for _, (v0, v1, v2), kw in jobs:
        fill_triangle(fb, v0, v1, v2, use_depth=use_zbuffer, outline=outline, **kw)

    return len(jobs), culled


def depth_to_image(fb, near, far, perspective=True):
    """Turn the z-buffer into a grayscale picture: near = white, far = dark."""
    z = fb.depth
    hit = np.isfinite(z)
    image = np.zeros((fb.w, fb.h, 3), dtype=np.uint8)
    if not hit.any():
        fb.color[:] = image
        return
    zn = z[hit]
    if perspective:
        # NDC depth is NOT linear in distance; convert back to eye-space distance
        dist = 2 * near * far / (far + near - zn * (far - near))
    else:
        dist = zn                                        # orthographic depth is linear
    lo, hi = dist.min(), dist.max()
    t = (dist - lo) / (hi - lo) if hi > lo else np.zeros_like(dist)
    gray = (255 - 200 * t).astype(np.uint8)              # 255 (near) .. 55 (far)
    image[hit] = gray[:, None]
    fb.color[:] = image