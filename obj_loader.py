"""
obj_loader.py - load Wavefront .obj meshes.

A mesh is stored the standard way (an "indexed face set"):
  vertices : (N, 3) float array, each vertex stored ONCE
  triangles: (T, 3) int array of indices into vertices
  edges    : (E, 2) int array of unique edges (for wireframe drawing)
Sharing vertices between faces saves memory and keeps the surface connected.
"""
import os

import numpy as np


class Mesh:
    def __init__(self, name, vertices, triangles, edges):
        self.name = name
        self.vertices = vertices
        self.triangles = triangles
        self.edges = edges

    def __repr__(self):
        return (f"Mesh({self.name}: {len(self.vertices)} vertices, "
                f"{len(self.triangles)} triangles, {len(self.edges)} edges)")


def load_obj(path, normalize=True):
    vertices = []
    polygons = []

    with open(path, "r") as f:
        for line in f:
            parts = line.split()
            if not parts or parts[0].startswith("#"):
                continue
            if parts[0] == "v":                         # vertex position
                vertices.append([float(c) for c in parts[1:4]])
            elif parts[0] == "f":                       # face (3 or more corners)
                face = []
                for token in parts[1:]:
                    # a corner can be "v", "v/vt", "v//vn" or "v/vt/vn":
                    # we only need the vertex index (the first number)
                    i = int(token.split("/")[0])
                    # OBJ indices start at 1; negative indices count from the end
                    face.append(i - 1 if i > 0 else len(vertices) + i)
                polygons.append(face)
            # other lines (vt, vn, o, g, s, usemtl, ...) are ignored for now

    vertices = np.array(vertices, dtype=float)

    # Triangulate every polygon with a "fan" from its first corner:
    # a quad (a, b, c, d) becomes triangles (a, b, c) and (a, c, d).
    triangles = []
    for face in polygons:
        for k in range(1, len(face) - 1):
            triangles.append((face[0], face[k], face[k + 1]))
    triangles = np.array(triangles, dtype=np.int32)

    # Unique edges from the ORIGINAL polygon outlines, so quads are
    # drawn as quads (no extra diagonal) like in Blender's wireframe view.
    edge_set = set()
    for face in polygons:
        for k in range(len(face)):
            a, b = face[k], face[(k + 1) % len(face)]
            edge_set.add((min(a, b), max(a, b)))    # (a, b) and (b, a) are the same edge
    edges = np.array(sorted(edge_set), dtype=np.int32)

    if normalize:
        # center the model and scale its largest side to 2 (fits in [-1, 1])
        lo, hi = vertices.min(axis=0), vertices.max(axis=0)
        vertices = (vertices - (lo + hi) / 2) / (hi - lo).max() * 2

    name = os.path.splitext(os.path.basename(path))[0]
    return Mesh(name, vertices, triangles, edges)