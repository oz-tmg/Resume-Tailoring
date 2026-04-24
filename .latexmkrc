# .latexmkrc
# ==========
# Project-wide latexmk configuration.
# Placed at the repo root so it applies to all resume builds regardless
# of which output subdirectory the .tex file lives in.
#
# latexmk reads .latexmkrc from the directory it's invoked from AND from
# the directory containing the .tex file. We invoke from the .tex file's
# directory (cwd=tex_path.parent in build.py), so this file needs to be
# copied or symlinked there — OR we pass it explicitly via -r flag.
# build.py passes -r /path/to/repo/.latexmkrc to handle this cleanly.

# ---------------------------------------------------------------------------
# Compiler
# ---------------------------------------------------------------------------
# Use XeLaTeX (required by cv-style.cls for custom fonts via fontspec)
$pdf_mode = 5;        # 5 = xelatex
$xelatex = 'xelatex -interaction=nonstopmode -halt-on-error %O %S';

# ---------------------------------------------------------------------------
# Asset search paths
# ---------------------------------------------------------------------------
# TEXINPUTS tells (Xe)LaTeX where to search for .tex, .sty, .cls, and font files.
# The repo root contains: cv-style.cls, fonts/, icons/
# %R is latexmk's variable for the root directory of the .tex file being compiled.
# We add two levels up (../../) as a fallback, but the explicit $repo_root
# set by build.py via ENV is more reliable.
ensure_path('TEXINPUTS', './');

# ---------------------------------------------------------------------------
# Build artifact cleanup
# ---------------------------------------------------------------------------
# Files to remove on `latexmk -c` (clean) or `make clean`
$clean_ext = 'aux fls fdb_latexmk log out synctex.gz xdv';

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
# Keep generated PDF in the same directory as the .tex file
$out_dir = '';   # empty = same dir as .tex (default)
