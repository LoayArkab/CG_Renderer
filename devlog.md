# Development Log

## Stage 1: Framebuffer and Bresenham line algorithm
- Built my own pixel framebuffer with numpy; pygame is only used to display it.
- Implemented Bresenham's line algorithm and tested it with a spoke pattern covering all 8 octants.
- Bug found: float endpoints cause an infinite loop, because the stop condition x0 == x1 is never exactly true. Fixed by rounding endpoints to integers first.
- Setup issue: my Python is managed by uv and blocks pip installs, so I created a project virtual environment (.venv).