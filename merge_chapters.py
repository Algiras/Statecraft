#!/usr/bin/env python3
"""
Merges individual chapters into the main book.md manuscript,
ensuring clean LaTeX page breaks and stripping duplicate YAML headers.
"""

import os
import re

OUTPUT_BOOK = "book.md"
CHAPTERS_DIR = "chapters"
CHAPTER_FILES = [
    "chapter_0_intro.md",
    "chapter_1_legitimacy.md",
    "chapter_2_monetary.md",
    "chapter_3_housing.md",
    "chapter_4_security.md",
    "chapter_5_recognition.md",
    "chapter_6_digital.md",
    "chapter_7_health.md",
    "chapter_8_education.md",
    "chapter_9_fiscal.md",
    "chapter_10_energy.md",
    "chapter_11_conclusion.md"
]

YAML_FRONTMATTER = """---
title: "STATECRAFT"
subtitle: "A How-To Guide for the Accidental Founder (Or: Why Building a Country is Harder Than You Think)"
author: "Antigravity & User"
date: "July 2026"
---

"""

def strip_yaml(content):
    """Strips any YAML frontmatter block from the top of the text."""
    # Matches a block starting with --- and ending with --- at the very start of the text
    return re.sub(r"^---[\s\S]*?---\s*", "", content)

def main():
    print("Merging chapters into book.md...")
    
    with open(OUTPUT_BOOK, "w", encoding="utf-8") as out:
        # Write main book title and metadata
        out.write(YAML_FRONTMATTER)
        
        for i, filename in enumerate(CHAPTER_FILES):
            filepath = os.path.join(CHAPTERS_DIR, filename)
            if not os.path.exists(filepath):
                print(f"Error: {filepath} not found!")
                continue
                
            print(f"Reading {filename}...")
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Clean up the chapter content
            content = strip_yaml(content).strip()
            
            # Add page break before subsequent chapters
            if i > 0:
                out.write("\n\n\\newpage\n\n")
            
            out.write(content)
            out.write("\n")
            
    print(f"Successfully merged {len(CHAPTER_FILES)} chapters into {OUTPUT_BOOK}!")

if __name__ == "__main__":
    main()
