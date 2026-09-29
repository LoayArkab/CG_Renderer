"""
obj_loader.py - meshes and the Wavefront .obj loader.

A mesh is stored the standard way (an "indexed face set"):
  vertices : (N, 3) float array, each vertex stored ONCE
  triangles: (T, 3) int array of indices into vertices (counter-clockwise = front)
  face_ids : (T,)   which original polygon each triangle came from
  edges    : (E, 2) int array of unique edges (for wireframe drawing)
  face_colors: (F, 3) one debug color per original polygon
"""
import colorsys
import os

import numpy as np


class Mesh:
    def __init__(self, name, vertices, triangles, face_ids, edges, face_colors):
        self.name = name
        self.vertices = vertices
        self.triangles = triangles
        self.face_ids = face_ids
        self.edges = edges
        self.face_colors = face_colors
        self.tri_colors = face_colors[face_ids]      # color of every triangle

    def __repr__(self):
        return (f"Mesh({self.name}: {len(self.vertices)} vertices, "
                f"{len(self.triangles)} triangles, {len(self.edges)} edges)")


def debug_colors(n):
    """n clearly different pastel colors, using golden-ratio steps around the hue wheel."""
    colors = []
    for i in range(n):
        hue = (i * 0.618033988749895) % 1.0
        r, g, b = colorsys.hsv_to_rgb(hue, 0.45, 0.95)
        colors.append((int(r * 255), int(g * 255), int(b * 255)))
    return np.array(colors, dtype=np.uint8)


def mesh_from_polygons(name, vertices, polygons, normalize=False):
    """Build a Mesh from vertex positions and polygons (lists of vertex indices)."""
    vertices = np.array(vertices, dtype=float)

    # Fan triangulation: polygon (a, b, c, d) -> (a, b, c) and (a, c, d).
    # The winding (counter-clockwise order) of the polygon is preserved.
    triangles, face_ids = [], []
    for fid, face in enumerate(polygons):
        for k in range(1, len(face) - 1):
            triangles.append((face[0], face[k], face[k + 1]))
            face_ids.append(fid)

    # Unique edges from the original polygon outlines (no quad diagonals).
    edge_set = set()
    for face in polygons:
        for k in range(len(face)):
            a, b = face[k], face[(k + 1) % len(face)]
            edge_set.add((min(a, b), max(a, b)))

    if normalize:
        lo, hi = vertices.min(axis=0), vertices.max(axis=0)
        vertices = (vertices - (lo + hi) / 2) / (hi - lo).max() * 2

    return Mesh(name, vertices,
                np.array(triangles, dtype=np.int32),
                np.array(face_ids, dtype=np.int32),
                np.array(sorted(edge_set), dtype=np.int32),
                debug_colors(len(polygons)))


def load_obj(path, normalize=True):
    vertices, polygons = [], []
    with open(path, "r") as f:
        for line in f:
            parts = line.split()
            if not parts or parts[0].startswith("#"):
                continue
            if parts[0] == "v":
                vertices.append([float(c) for c in parts[1:4]])
            elif parts[0] == "f":
                face = []
                for token in parts[1:]:
                    # corner formats: "v", "v/vt", "v//vn", "v/vt/vn"
                    i = int(token.split("/")[0])
                    face.append(i - 1 if i > 0 else len(vertices) + i)
                polygons.append(face)
    name = os.path.splitext(os.path.basename(path))[0]
    return mesh_from_polygons(name, vertices, polygons, normalize)


# ---- built-in shapes, polygons listed counter-clockwise seen from OUTSIDE ----

def make_cube():
    v = [[-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
         [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]]
    faces = [[4, 5, 6, 7],   # front  (+z)
             [1, 0, 3, 2],   # back   (-z)
             [5, 1, 2, 6],   # right  (+x)
             [0, 4, 7, 3],   # left   (-x)
             [7, 6, 2, 3],   # top    (+y)
             [0, 1, 5, 4]]   # bottom (-y)
    return mesh_from_polygons("cube", v, faces)


def make_pyramid():
    v = [[-1, -1, -1], [1, -1, -1], [1, -1, 1], [-1, -1, 1], [0, 1.2, 0]]
    faces = [[0, 1, 2, 3],   # base (seen from below)
             [3, 2, 4], [2, 1, 4], [1, 0, 4], [0, 3, 4]]
    return mesh_from_polygons("pyramid", v, faces)