#!/bin/bash
# Build CrossEcho paper — Quantum Engineering
PAPER="$(cd "$(dirname "$0")/../crossecho/paper" && pwd)"
cd "$PAPER"
echo "CrossEcho — Quantum Engineering"
rm -f main.aux main.bbl main.blg main.log main.out main.pag main.pdf
echo "[1/2] XeLaTeX..." && xelatex -interaction=nonstopmode main.tex > /dev/null 2>&1 || true
echo "[2/2] XeLaTeX..." && xelatex -interaction=nonstopmode main.tex > /dev/null 2>&1 || true
U=$(grep -c "Warning.*undefined" main.log 2>/dev/null || echo 0)
P=$(pdfinfo main.pdf 2>/dev/null | grep Pages | awk '{print $2}')
echo "Undefined: $U  |  Pages: $P"
rm -f main.aux main.bbl main.blg main.log main.out main.pag
echo "Done → crossecho/paper/main.pdf"
