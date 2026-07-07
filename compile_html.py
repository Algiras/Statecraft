#!/usr/bin/env python3
"""
Compiles the book.md markdown to index.html with a beautiful, modern reading layout,
incorporating download links for the PDF and Audiobook.
"""

import os
import subprocess

def main():
    print("Compiling manuscript to HTML body using Pandoc...")
    
    # Run Pandoc to generate the raw HTML body and Table of Contents
    cmd = [
        "pandoc", "book.md",
        "-o", "body.html",
        "--toc",
        "--toc-depth=1",
        "--number-sections"
    ]
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error compiling HTML via Pandoc: {e}")
        return

    print("Building full index.html with styling and templates...")
    
    with open("body.html", "r", encoding="utf-8") as f:
        body_content = f.read()

    # Define the template wrap
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>STATECRAFT: A How-To Guide for the Accidental Founder</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>

    <header>
        <div class="header-container">
            <h1 class="header-title">STATECRAFT</h1>
            <nav class="header-nav">
                <a href="#TOC">Table of Contents</a>
                <a href="statecraft_manual.pdf" target="_blank">Download PDF</a>
                <a href="statecraft_audiobook.mp3" target="_blank">Download Audiobook</a>
            </nav>
        </div>
    </header>

    <div class="content-container">
        
        <div class="title-block">
            <h1>STATECRAFT</h1>
            <div class="subtitle">A How-To Guide for the Accidental Founder</div>
            <div class="author">Antigravity & Algimantas</div>
            <div class="date">July 2026</div>
            
            <img src="statecraft_book_cover.jpg" class="cover-img" alt="Statecraft Book Cover">
        </div>

        <section class="download-section">
            <div class="download-card">
                <h3>PDF Edition</h3>
                <p>Read a beautifully styled, typeset version of the manual in print-ready layout.</p>
                <a href="statecraft_manual.pdf" class="btn" target="_blank">Download PDF</a>
            </div>
            <div class="download-card">
                <h3>Audiobook Edition</h3>
                <p>Listen to the complete 5-hour Gladwellian narrator audio (44,500+ words).</p>
                <a href="statecraft_audiobook.mp3" class="btn" target="_blank">Download MP3</a>
            </div>
        </section>

        <div class="manual-box">
            <strong>Open Access License:</strong> This book is licensed under the 
            <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank">Creative Commons Attribution 4.0 International (CC BY 4.0)</a>. 
            You are free to share, adapt, and build upon this material for any purpose.
        </div>

        <!-- Book Content Starts Here -->
        {body_content}
        <!-- Book Content Ends Here -->

    </div>

</body>
</html>
"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)
        
    # Clean up temporary body.html
    if os.path.exists("body.html"):
        os.remove("body.html")
        
    print("Success! index.html generated.")

if __name__ == "__main__":
    main()
