#!/bin/bash
PAPER="$(cd "$(dirname "$0")/../crossecho/paper" && pwd)"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ZIP="$ROOT/crossecho_aqt_submission.zip"
cd "$PAPER"
echo "Packaging CrossEcho LaTeX source..."
rm -f "$ZIP"
zip -r "$ZIP" . \
    -x "*.pdf" "*.aux" "*.bbl" "*.blg" "*.log" "*.out" "*.pag" "*.zip" "texput.*" \
    -x ".DS_Store" "__pycache__/*" ".gitignore" ".python-version" "__init__.py"
echo "Done → $ZIP ($(ls -lh "$ZIP" | awk '{print $5}'))"
