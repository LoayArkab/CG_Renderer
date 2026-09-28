# Development Log

## Stage 1: Framebuffer and Bresenham line algorithm
- Built my own pixel framebuffer with numpy; pygame is only used to display it.
- Implemented Bresenham's line algorithm and tested it with a spoke pattern covering all 8 octants.
- Bug found: float endpoints cause an infinite loop, because the stop condition x0 == x1 is never exactly true. Fixed by rounding endpoints to integers first.
- Setup issue: my Python is managed by uv and blocks pip installs, so I created a project virtual environment (.venv).

## Stage 2: 3D transformation pipeline
- Built 4x4 matrices in homogeneous coordinates: translate, scale, rotate X/Y/Z, perspective and orthographic projection.
- Pipeline: model -> view -> projection -> divide by w -> viewport -> Bresenham.
- Experiment: translate @ rotate makes the object spin in place; rotate @ translate makes it orbit the origin, because the rightmost matrix is applied first. Added key O to show this live.
- Added a pyramid (5 vertices, 8 edges) next to the cube, and key P to compare perspective vs orthographic.
- Moved the camera from 5 to 6 units away so both objects fit on screen.