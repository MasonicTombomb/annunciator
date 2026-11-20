"""Make the SVG files of the annunciator logo from the LaTeX source.

The source of the logo is ``docs/_static/latex/annunciatorlogo.sty``. The
PDF form of the manual uses that file directly. This script makes the SVG
files for the HTML form, the favicon and the README:

* ``annunciator-mark.svg`` and ``annunciator-mark-dark.svg``
* ``annunciator-lockup.svg`` and ``annunciator-lockup-dark.svg``
* ``favicon.svg``

The script writes the files to ``docs/_static/logo``. It needs ``latex``
and ``dvisvgm`` (MiKTeX or TeX Live) and the LaTeX packages ``tikz``,
``standalone`` and ``roboto``. The text of the word mark becomes paths.
Thus the SVG files do not need the font.

Usage::

    python tools/make_logo.py
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STYLE = ROOT / "docs" / "_static" / "latex" / "annunciatorlogo.sty"
OUTPUT = ROOT / "docs" / "_static" / "logo"

VARIANTS = {
    "annunciator-mark": r"\annmark{64bp}",
    "annunciator-mark-dark": r"\annmark[dark]{64bp}",
    "annunciator-lockup": r"\annlockup{64bp}",
    "annunciator-lockup-dark": r"\annlockup[dark]{64bp}",
    # The edge of the dark bezel makes the icon visible on dark tabs also.
    "favicon": r"\annmark*[dark]{64bp}",
}

TEMPLATE = r"""\def\pgfsysdriver{pgfsys-dvisvgm.def}
\documentclass[border=0pt]{standalone}
\usepackage{annunciatorlogo}
\begin{document}
%s
\end{document}
"""


def _tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        sys.exit(f"make_logo: the program '{name}' is not available")
    return path


def make(output: Path = OUTPUT) -> list:
    """Make the SVG files and return their paths."""
    latex = _tool("latex")
    dvisvgm = _tool("dvisvgm")
    output.mkdir(parents=True, exist_ok=True)
    made = []
    with tempfile.TemporaryDirectory() as work:
        work_dir = Path(work)
        shutil.copy(STYLE, work_dir / STYLE.name)
        for name, body in VARIANTS.items():
            (work_dir / f"{name}.tex").write_text(TEMPLATE % body, encoding="utf-8")
            subprocess.run(
                [latex, "-interaction=nonstopmode", "-halt-on-error", f"{name}.tex"],
                cwd=work_dir, check=True, stdout=subprocess.DEVNULL,
            )
            target = output / f"{name}.svg"
            subprocess.run(
                [dvisvgm, "--no-fonts", "--exact-bbox", "--precision=4",
                 "--optimize", "-o", str(target), f"{name}.dvi"],
                cwd=work_dir, check=True, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            made.append(target)
    return made


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--output", type=Path, default=OUTPUT,
                        help="directory for the SVG files")
    args = parser.parse_args()
    for path in make(args.output):
        print(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
