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
| P | Toggle perspective / orthographic projection |
| O | Toggle the pyramid's transform order (spin in place / orbit) |
| Esc | Quit |

## Project structure

| File | Responsibility |
|---|---|
| `main.py` | Main loop, input handling, scene setup |
| `math3d.py` | 4×4 matrices: translation, rotation, scaling, projection, viewport |
| `renderer.py` | Framebuffer and rasterization algorithms (everything that writes pixels) |
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

### Clipping (simplified)
A point behind the camera has `w ≤ 0`, and dividing by it would flip it to the wrong side of the screen. Edges with an endpoint closer than the near plane are skipped. (Full clipping, which cuts the edge exactly at the near plane, is a possible extension.)

---

<!-- Later stages are added below -->