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

## Stage 4: Loading OBJ models
- Wrote an OBJ loader (obj_loader.py) that stores meshes as an indexed face set: each vertex once, faces as index lists.
- Handles all face corner formats (v, v/vt, v//vn, v/vt/vn), 1-based and negative indices, and polygons with more than 3 corners.
- Quads and polygons are triangulated with a fan; wireframe edges come from the original polygon outlines and are de-duplicated with a set.
- Models are centered and scaled to fit [-1, 1] so every model works with the same camera.
- Performance: projecting all vertices in one numpy multiplication instead of per edge keeps the teapot (6,320 triangles, ~10,000 edges) interactive.
- Added M to switch models and Space to pause rotation.

## Stage 5: Filled triangles
- Implemented triangle rasterization with edge functions: for each pixel center in the triangle's bounding box, test the sign of the three edge functions. numpy tests the whole box at once.
- Back-face culling using the winding order (sign of the screen-space area). Culls about half the triangles (3,700 of 6,320 on the teapot).
- Verified all models use counter-clockwise winding by computing their signed volume (positive = faces point outward).
- Painter's algorithm: triangles from all objects sorted far-to-near by average depth.
- Known failure: when the pyramid orbits through the cube, whole faces pop in front of each other, because no ordering of whole triangles is correct for intersecting objects. Needs per-pixel depth: z-buffer (next stage).
- Debug colors per polygon using golden-ratio hue steps, since there is no lighting yet.
- Screenshot shows the failure: small pink pyramid triangles drawn on top of the cube where the pyramid is actually inside it.

## Stage 6: Z-buffer
- Added a depth buffer next to the color buffer, cleared to infinity every frame.
- Depth is interpolated per pixel with barycentric coordinates (edge functions divided by the signed area): z = l0*z0 + l1*z1 + l2*z2.
- Stored NDC z because it is linear in screen space after the perspective divide, so screen-space interpolation is exact.
- Triangles no longer need sorting. Intersecting objects (pyramid orbiting through the cube) now show a clean intersection line. Key Z switches painter/z-buffer to compare.
- Depth view: converts NDC z back to real distance (NDC z is very non-linear: ~90% of its range is used in the first metre with near=0.1, far=100) and shows it as grayscale.
- Problem: the Stage 5 outlines were drawn on top with Bresenham, which would show hidden edges now that triangles aren't sorted. Fix: compute the outline inside the rasterizer (pixel distance to edge = |w| / edge length), after the depth test.

## Stage 7: Lighting
- Added vertex normals (area-weighted average of face normals) and a Blinn-Phong lighting model (lighting.py): ambient + diffuse (Lambert) + specular (half vector).
- Three shading modes (key L): flat (per triangle), Gouraud (per vertex, colors interpolated), Phong (normals interpolated, lighting per pixel).
- Added perspective-correct interpolation (interpolate value/w and 1/w, then divide), used for Gouraud colors and Phong normals.
- Key K makes the light orbit: shows Gouraud's highlight jumping between vertices vs Phong's smooth highlight.
- Changed the light direction to come more from the camera side; the first direction left most visible faces dark.
- Noticed seams on the teapot: the OBJ duplicates vertices along patch borders, so normals don't match across them.
- Phong is ~2x slower than Gouraud in pure Python (~4-5 FPS on the teapot).

## Stage 8: Interface and anti-aliasing
- Replaced the window-title info with an on-screen display (model, triangles, mode, shading, z-buffer/painter, culling, projection, AA, FPS) and a help panel (key H).
- The HUD is drawn with pygame fonts on the final window, after rendering, so it never touches the framebuffer or z-buffer.
- Added 2x2 supersampling anti-aliasing (key X): render at 640x480 into a second framebuffer, then average each 2x2 block (numpy reshape + mean).
- Refactored the frame drawing into render_scene(fb, ...) so the same code can render into either framebuffer.
- AA costs about 4x the per-pixel work, but less than 4x overall because per-triangle work stays the same.

## Stage 9: Documentation
- Finished the README: overview, gallery, features, pipeline diagram, per-stage explanations, performance, limitations, extensions, what I learned, credits.