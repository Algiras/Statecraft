#!/bin/bash
set -e

echo "Compiling Statecraft PDF using Pandoc and XeLaTeX..."
pandoc book.md \
  -o statecraft_manual.pdf \
  --pdf-engine=xelatex \
  -H header.tex \
  --toc \
  --toc-depth=1 \
  --number-sections \
  --metadata title="STATECRAFT" \
  --metadata subtitle="A How-To Guide for the Accidental Founder" \
  --metadata author="Antigravity & Algimantas" \
  --metadata date="Open Access Edition 1.0, July 2026" \
  -V documentclass=article \
  -V geometry="margin=1.25in" \
  -V fontsize="12pt"

echo "PDF successfully generated as statecraft_manual.pdf!"
