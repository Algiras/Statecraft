#!/bin/bash
set -e

if [ ! -f book.md ]; then
  echo "book.md not found — run merge_chapters.py first."
  exit 1
fi

echo "Preprocessing manuscript for EPUB..."
python3 <<'PY'
from compile_html import fix_tight_lists

with open("book.md", "r", encoding="utf-8") as f:
    md = fix_tight_lists(f.read())
with open("book_epub.md", "w", encoding="utf-8") as f:
    f.write(md)
PY

echo "Compiling EPUB with Pandoc..."
pandoc book_epub.md \
  -o statecraft.epub \
  --from markdown+footnotes \
  --toc \
  --toc-depth=2 \
  --epub-cover-image=statecraft_book_cover.jpg \
  --metadata title="STATECRAFT" \
  --metadata subtitle="A How-To Guide for the Accidental Founder" \
  --metadata author="Antigravity & Algimantas" \
  --metadata date="July 2026" \
  --metadata lang="en"

rm -f book_epub.md
echo "EPUB successfully generated as statecraft.epub!"
