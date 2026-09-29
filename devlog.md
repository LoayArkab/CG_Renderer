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

## Stage 3: Interactive camera and clipping
- Added a first-person fly camera (camera.py): WASD/QE to move, arrow keys to look, R to reset.
- View matrix = inverse of the camera transform: Rx(-pitch) @ Ry(-yaw) @ T(-position).
- Movement uses dt (seconds per frame) so speed doesn't depend on FPS.
- Added a floor grid. This exposed two bugs: lines behind the camera were flipped by the divide by w, and lines just in front of the near plane projected to huge coordinates, making Bresenham loop over ~1,000,000 pixels and freeze.
- Fix 1: near-plane clipping in clip space (cut each edge at w = near before the divide).
- Fix 2: Liang-Barsky clipping of every line to the screen rectangle before Bresenham.
- Screenshot key moved from S to C because S is now "move backward".