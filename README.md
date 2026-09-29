# Rasterization from Scratch: A 3D Software Renderer in Python

## Overview

This project is a small 3D rendering engine written from scratch. Pygame is used **only** to open a window and show an array of pixels; every pixel in that array is computed by my own code. The project follows the path a GPU takes: 3D vertices are transformed with matrices, projected onto the screen, and rasterized into pixels.

**Main course topic:** Rasterization.
**Supporting topics:** geometric transformations and rotations, projection, mesh representation (graphics data), hidden surface removal, and shading.

## How to run

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install pygame-ce numpy     # Windows
.venv\Scripts\python.exe main.py
```

| Key | Action |
|---|---|
| W / A / S / D | Move forward / left / back / right |
| Q / E | Move down / up |
| Shift | Move 3× faster |
| Arrow keys | Look around (yaw and pitch) |
| R | Reset camera |
| M | Switch model (shapes → Suzanne → teapot → Spot the cow) |
| Space | Pause / resume the model rotation |
| P | Toggle perspective / orthographic projection |
| O | Toggle the pyramid's transform order (spin in place / orbit) |
| C | Save a screenshot to `screenshots/` |
| Esc | Quit |

## Project structure

| File | Responsibility |
|---|---|
| `main.py` | Main loop, input handling, scene setup |
| `math3d.py` | 4×4 matrices: translation, rotation, scaling, projection, viewport |
| `renderer.py` | Framebuffer and rasterization algorithms (everything that writes pixels) |
| `camera.py` | First-person fly camera: position, yaw, pitch, view matrix |
| `obj_loader.py` | Wavefront .obj loader: indexed mesh, triangulation, edge extraction |
| `models/` | Test models: Suzanne, the Utah teapot, Spot the cow |
| `devlog.md` | Development log: problems found and how they were solved |

---

## Stage 1: The framebuffer and Bresenham's line algorithm

### The framebuffer
The screen is a discrete grid of pixels, but geometry is continuous. The framebuffer is a `numpy` array of shape `(width, height, 3)` holding one RGB color per pixel. It is rendered at a low internal resolution (320×240) and scaled up 3×, which keeps the pure-Python renderer fast and makes individual pixels visible, so the rasterization is easy to see.

### Bresenham's line algorithm
To draw a line from (x0, y0) to (x1, y1) we must decide which pixels best approximate it. The naive approach computes `y = m·x + b` for every x, which needs floating-point multiplication and rounding per pixel, and leaves gaps on steep lines.

Bresenham's algorithm walks from one endpoint to the other one pixel at a time and keeps an integer **error term** `err` that measures how far the drawn pixels have drifted from the ideal line. At each step it compares `2·err` against `dx` and `dy` to decide whether to step in x, in y, or in both. Only integer additions and comparisons are used, so it is fast and exact. The implementation handles all 8 octants (any slope, any direction) by using step signs `sx` and `sy`.

**Test:** a "spoke" pattern of 24 rotating lines from the center covers every direction and confirms all octants work.

**Bug found:** the stop condition `x0 == x1 and y0 == y1` is never exactly true when the endpoints are floats (which projected 3D points always are), causing an infinite loop. Fix: round the endpoints to integer pixel coordinates before the loop.

---

## Stage 2: The 3D transformation pipeline

Every vertex passes through the same chain before it becomes a pixel:

```
object space --Model--> world space --View--> camera space --Projection--> clip space
  --divide by w--> normalized device coordinates (NDC) --Viewport--> screen pixels
```

### Homogeneous coordinates and 4×4 matrices
Rotation and scaling can be written as 3×3 matrices, but translation cannot: it is an addition, not a multiplication. By writing a point as `(x, y, z, 1)` we can express translation as a 4×4 matrix too:

```
| 1 0 0 tx |   | x |   | x + tx |
| 0 1 0 ty | · | y | = | y + ty |
| 0 0 1 tz |   | z |   | z + tz |
| 0 0 0 1  |   | 1 |   |   1    |
```

Now every transformation is one matrix, and a whole chain collapses into a single matrix computed once per object per frame: `MVP = Projection · View · Model`.

### Rotation matrices
Rotation around the Y axis by angle θ:

```
|  cos θ  0  sin θ  0 |
|    0    1    0    0 |
| -sin θ  0  cos θ  0 |
|    0    0    0    1 |
```

X and Z rotations have the same structure on the other axis pairs. The cube is rotated with `rotate_y(t) · rotate_x(0.7t)`, a combination of Euler-angle rotations.

### Transform order matters (matrix multiplication is not commutative)
Points are column vectors, so in `A · B · p` the matrix **B is applied first**. The pyramid demonstrates this live (key **O**), using the same two matrices in two orders:

- `Translate(1.8, 0, 0) · RotateY(t)`: the pyramid is rotated around its own center first, then moved to the side. Result: **it spins in place**.
- `RotateY(t) · Translate(1.8, 0, 0)`: the pyramid is moved away from the origin first, then rotated around the **world** origin. Result: **it orbits around the center**, like a planet.

This is why a scene graph applies "local" transforms before "parent" transforms.

### Perspective projection
The perspective matrix (field of view 60°, `f = 1 / tan(fov/2)`):

```
| f/aspect  0        0                  0            |
|    0      f        0                  0            |
|    0      0   (far+near)/(near-far)  2·far·near/(near-far) |
|    0      0       -1                  0            |
```

The key is the last row: it copies `-z` into the `w` coordinate. After the matrix, every coordinate is **divided by w** (the perspective divide). Points farther from the camera have a larger `w`, so they shrink toward the center of the screen. That single division is what creates the sense of depth. The z row maps the range [near, far] into [-1, 1], which will be used for the z-buffer in a later stage.

### Orthographic projection
The orthographic matrix only scales and shifts a box of space into the [-1, 1] cube, and leaves `w = 1`. There is no divide by distance, so objects keep the same size at any depth and parallel lines stay parallel. It is used in engineering drawings and 2D games. Key **P** switches between the two so the difference can be seen directly.

### Viewport transform
NDC coordinates are in [-1, 1]. They are mapped to pixels with:

```
screen_x = (x_ndc + 1) / 2 · width
screen_y = (1 - y_ndc) / 2 · height      (flipped, because screen y grows downward)
```

### Clipping
In this stage, edges with an endpoint behind the near plane were simply skipped. Stage 3 replaces this with proper clipping.

---

## Stage 3: An interactive camera and line clipping

### The camera as an inverse transform
A camera is just an object in the world with a position and an orientation. Here it is described by a position and two angles: **yaw** (turning left/right around the Y axis) and **pitch** (looking up/down around the X axis). The camera's own transform in the world is:

```
CameraWorld = T(position) · Ry(yaw) · Rx(pitch)
```

The graphics pipeline, however, always assumes the camera sits at the origin looking down −Z. So instead of moving the camera, we move the **whole world in the opposite direction**. The view matrix is the inverse of the camera's transform:

```
View = CameraWorld⁻¹ = Rx(−pitch) · Ry(−yaw) · T(−position)
```

The inverse of a product reverses the order, and the inverse of a rotation is a rotation by the negative angle. Moving the camera 1 unit to the right is exactly the same as moving everything else 1 unit to the left.

### Moving relative to where you look
Pressing W should move the camera *forward from its own point of view*, not along a fixed world axis. The forward and right directions are the camera's local axes rotated by the yaw:

```
forward = Ry(yaw) · (0, 0, −1) = (−sin yaw, 0, −cos yaw)
right   = Ry(yaw) · (1, 0,  0) = ( cos yaw, 0, −sin yaw)
```

Pitch is clamped to ±89° so the camera cannot flip upside down (at exactly ±90° the yaw axis and the view axis line up and turning becomes ambiguous, a close relative of gimbal lock).

### Frame-rate independent movement
Movement is multiplied by `dt`, the time since the last frame in seconds. Speed is expressed in units per second, so the camera moves at the same real speed whether the renderer runs at 20 or 60 FPS.

### Why clipping became necessary
Once the camera can move, lines can pass behind it or extend far outside the screen. This caused two real problems:

1. **Points behind the camera:** they have `w ≤ 0`. Dividing by a negative `w` flips them to the opposite side of the screen and draws lines that should not exist.
2. **Huge off-screen lines:** a point just in front of the near plane projects to a coordinate like x = 1,000,000. Bresenham would then loop over a million pixels, almost all off-screen, and freeze the program.

The floor grid (lines 20 units long that pass under and behind the camera) triggers both, so the renderer now clips in two steps.

### Step 1: near-plane clipping in 3D (clip space)
Before the perspective divide, each edge is tested against the plane `w = near`. If both endpoints are in front, it is kept. If both are behind, it is dropped. If it crosses the plane, the crossing point is found by linear interpolation:

```
t   = (near − w0) / (w1 − w0)
hit = C0 + t · (C1 − C0)
```

and the part behind the camera is replaced by `hit`. Clipping in clip space (before dividing) is important, because the division is exactly what breaks for points behind the camera.

### Step 2: Liang–Barsky clipping in 2D (screen space)
After projection, each line is clipped to the screen rectangle before Bresenham runs. Liang–Barsky writes the line in parametric form:

```
P(u) = P0 + u · (P1 − P0),    0 ≤ u ≤ 1
```

Each of the four screen edges gives one inequality of the form `u · p_k ≤ q_k`. When `p_k < 0` the line is entering that boundary and `u = q_k / p_k` raises the lower bound `u_enter`; when `p_k > 0` the line is leaving and it lowers the upper bound `u_exit`. If `u_enter > u_exit` the line misses the screen entirely. Otherwise the visible part is `P(u_enter)` to `P(u_exit)`. It needs only four divisions per line and no repeated subdivision, which makes it more efficient than Cohen–Sutherland.

**Result:** Bresenham now only ever walks over visible pixels, so a line that was 1,000,000 pixels long is reduced to at most a few hundred, and the program stays smooth anywhere in the scene.

---

## Stage 4: Loading real 3D models (graphics data)

### Mesh representation: the indexed face set
A 3D model is a surface made of polygons. The naive way to store it is a list of triangles, each with its own three copies of its corner coordinates. Since a typical vertex is shared by about six triangles, that repeats every coordinate about six times, and nothing records that two triangles actually touch.

The renderer uses an **indexed face set** instead, the standard representation used by GPUs and most file formats:

- `vertices`: an (N, 3) array. Each vertex position is stored **once**.
- `triangles`: a (T, 3) array of integer **indices** into the vertex array.
- `edges`: an (E, 2) array of unique edges, used for wireframe drawing.

Besides saving memory, sharing vertices means a transform only has to be computed once per vertex, not once per triangle corner. The renderer takes advantage of this: all vertices are projected in a single matrix multiplication, and then every edge just looks up its two already-projected endpoints.

### The Wavefront OBJ format
OBJ is a plain-text format. The loader handles the lines that matter for geometry:

```
v  x y z          a vertex position
f  1 2 3 4        a face, listing vertex indices (1-based)
```

Details the loader has to deal with, all of which appear in the three test models:

- **Face corner formats:** a corner may be `v`, `v/vt`, `v//vn` or `v/vt/vn` (vertex / texture coordinate / normal). Only the first number, the vertex index, is used for now.
- **1-based and negative indices:** OBJ counts from 1, so 1 is subtracted. Negative indices count backwards from the most recently defined vertex.
- **Polygons with more than 3 corners:** Suzanne is made mostly of quads.

### Triangulation
The rasterizer (next stage) only works with triangles, because a triangle is always flat and always convex, so filling it has no special cases. Every polygon is split with a **fan** from its first corner: a quad `(a, b, c, d)` becomes `(a, b, c)` and `(a, c, d)`. A fan is correct for any convex polygon, which is what modeling tools export.

### Edge extraction
For the wireframe, edges are taken from the **original polygon outlines**, not the triangles, so quads are drawn without their internal diagonal (like Blender's wireframe view). Each edge is stored as `(min(a, b), max(a, b))` in a set, because the edge from a to b and the edge from b to a are the same line, and neighboring faces share it. Without this, every interior edge would be drawn twice.

### Normalization
Models come in arbitrary units and positions (the teapot is about 6 units wide and sits above the origin; Spot is under 2 units). Each model is centered on its bounding box and scaled so its largest side is 2, so every model fits in the same [−1, 1] box and the same camera setup works for all of them.

### The test models

| Model | Vertices | Triangles | Unique edges | Notes |
|---|---|---|---|---|
| Suzanne | 507 | 968 | 1,005 | Blender's mascot, mostly quads, `v//vn` corners |
| Utah teapot | 3,644 | 6,320 | 9,998 | The classic computer graphics test model (1975), plain `v` corners |
| Spot the cow | 2,930 | 5,856 | 8,784 | Uses `v/vt` corners (texture coordinates) |

Models from Alec Jacobson's *common-3d-test-models* collection on GitHub.

### Performance
Projecting all vertices at once with numpy, and converting the result to plain Python lists before the per-edge loop, keeps even the teapot at an interactive frame rate. The remaining cost is Bresenham itself, which runs in pure Python one pixel at a time. This is exactly the work a GPU does in parallel hardware.

---

