#!/usr/bin/env python3
"""
Compiles the book.md markdown to index.html with a premium, modern reading layout.
Charts are embedded inline as <img> elements at the right conceptual points.
"""

import os
import re
import subprocess

CHARTS = {
    "hardware_vs_software": "img_hardware_vs_software.jpg",
    "twelve_pillars": "img_twelve_pillars.jpg",
    "somaliland_vs_somalia": "img_somaliland_vs_somalia.jpg",
    "currency_board": "img_currency_board.jpg",
    "sovereignty_spectrum": "img_sovereignty_spectrum.jpg",
}

def main():
    print("Merging chapters (if needed)...")
    if not os.path.exists("book.md"):
        subprocess.run(["python", "merge_chapters.py"], check=True)

    print("Compiling manuscript to HTML body using Pandoc...")
    cmd = [
        "pandoc", "book.md",
        "-o", "body.html",
        "--toc",
        "--toc-depth=1",
        "--number-sections",
        "--mathjax",
    ]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return

    with open("body.html", "r", encoding="utf-8") as f:
        body = f.read()

    # Inject charts at the right positions in the compiled HTML
    def chart_html(src, caption, alt):
        return f'''<figure class="chart-figure">
  <img src="{src}" alt="{alt}" class="chart-img" loading="lazy">
  <figcaption>{caption}</figcaption>
</figure>'''

    # After the intro chapter heading, inject the hardware vs software chart
    body = body.replace(
        '<h1 data-number="1"',
        chart_html(
            CHARTS["hardware_vs_software"],
            "The central thesis: nationhood is software, not hardware.",
            "Hardware vs Software of Statehood diagram"
        ) + '\n<h1 data-number="1"',
        1
    )

    # After section about the 12 pillars (TOC section), inject the wheel
    body = body.replace(
        '<h1 data-number="2"',
        chart_html(
            CHARTS["twelve_pillars"],
            "The 12 pillars that a functional state must build, maintain, and integrate.",
            "12 Pillars of Statecraft wheel diagram"
        ) + '\n<h1 data-number="2"',
        1
    )

    # After chapter 2 heading (Somalia/Somaliland), inject comparison chart
    body = body.replace(
        '<h1 data-number="3"',
        chart_html(
            CHARTS["somaliland_vs_somalia"],
            "Chapter 1: How Somaliland succeeded with $0 where Somalia failed with $4.2B in UN aid.",
            "Top-Down vs Bottom-Up State Building diagram"
        ) + '\n<h1 data-number="3"',
        1
    )

    # After chapter 3 heading (Estonia currency), inject currency board chart
    body = body.replace(
        '<h1 data-number="4"',
        chart_html(
            CHARTS["currency_board"],
            "Chapter 2: Estonia's Currency Board — the commitment device that ended hyperinflation.",
            "Currency Board System diagram"
        ) + '\n<h1 data-number="4"',
        1
    )

    # After chapter 6 heading (Sovereign Club / Malta / Taiwan), inject sovereignty spectrum
    body = body.replace(
        '<h1 data-number="7"',
        chart_html(
            CHARTS["sovereignty_spectrum"],
            "Chapter 5: The Sovereignty Spectrum — from zero recognition (Liberland) to de jure status (Malta SMOM).",
            "The Sovereignty Spectrum diagram"
        ) + '\n<h1 data-number="7"',
        1
    )

    css = '''/* ===== STATECRAFT — Premium Reading Stylesheet ===== */
@import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,600;1,400&family=Inter:wght@300;400;500;600;700&display=swap');

:root {
  --bg:          #0f0f13;
  --surface:     #17171e;
  --surface2:    #1e1e28;
  --border:      #2a2a38;
  --text:        #e8e8f0;
  --text-muted:  #7a7a9a;
  --accent:      #7c6af7;
  --accent2:     #4fc3f7;
  --accent3:     #66bb6a;
  --gold:        #ffd54f;
  --serif:       'Lora', Georgia, serif;
  --sans:        'Inter', system-ui, sans-serif;
  --max-w:       780px;
  --r:           14px;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html { scroll-behavior: smooth; }

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--serif);
  font-size: 19px;
  line-height: 1.75;
  -webkit-font-smoothing: antialiased;
}

/* ── Header ── */
header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(15,15,19,0.85);
  backdrop-filter: blur(24px) saturate(180%);
  -webkit-backdrop-filter: blur(24px) saturate(180%);
  border-bottom: 1px solid var(--border);
}
.header-inner {
  max-width: calc(var(--max-w) + 120px);
  margin: 0 auto;
  padding: 14px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}
.header-wordmark {
  font-family: var(--sans);
  font-weight: 700;
  font-size: 15px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text);
  text-decoration: none;
}
nav { display: flex; gap: 8px; flex-wrap: wrap; }
nav a, .nav-pill {
  font-family: var(--sans);
  font-size: 13px;
  font-weight: 500;
  padding: 6px 14px;
  border-radius: 999px;
  border: 1px solid var(--border);
  color: var(--text-muted);
  text-decoration: none;
  transition: all 0.2s;
  white-space: nowrap;
}
nav a:hover { color: var(--text); border-color: var(--accent); background: rgba(124,106,247,0.1); }
.nav-pill.disabled { cursor: not-allowed; opacity: 0.4; }
.nav-pill.coming-soon { color: var(--gold); border-color: rgba(255,213,79,0.3); background: rgba(255,213,79,0.05); }

/* ── Hero / Cover ── */
.hero {
  max-width: calc(var(--max-w) + 120px);
  margin: 0 auto;
  padding: 80px 24px 60px;
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 60px;
  align-items: center;
}
@media (max-width: 768px) { .hero { grid-template-columns: 1fr; text-align: center; } }
.hero-text {}
.hero-label {
  font-family: var(--sans);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 20px;
  display: block;
}
.hero-title {
  font-family: var(--sans);
  font-size: clamp(42px, 6vw, 72px);
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.05;
  color: #fff;
  margin-bottom: 16px;
}
.hero-subtitle {
  font-family: var(--serif);
  font-size: 20px;
  font-style: italic;
  color: var(--text-muted);
  margin-bottom: 32px;
  line-height: 1.5;
}
.hero-meta {
  font-family: var(--sans);
  font-size: 14px;
  color: var(--text-muted);
  margin-bottom: 40px;
}
.hero-meta strong { color: var(--text); }
.hero-actions { display: flex; gap: 12px; flex-wrap: wrap; }
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--accent);
  color: #fff;
  font-family: var(--sans);
  font-size: 14px;
  font-weight: 600;
  padding: 12px 24px;
  border-radius: 999px;
  text-decoration: none;
  transition: all 0.2s;
  box-shadow: 0 0 24px rgba(124,106,247,0.3);
}
.btn-primary:hover { background: #9681ff; box-shadow: 0 0 32px rgba(124,106,247,0.5); transform: translateY(-1px); }
.btn-secondary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: transparent;
  color: var(--text);
  font-family: var(--sans);
  font-size: 14px;
  font-weight: 500;
  padding: 12px 24px;
  border-radius: 999px;
  border: 1px solid var(--border);
  text-decoration: none;
  transition: all 0.2s;
}
.btn-secondary:hover { border-color: var(--accent); color: var(--accent); background: rgba(124,106,247,0.08); }
.btn-disabled {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: transparent;
  color: var(--gold);
  font-family: var(--sans);
  font-size: 14px;
  font-weight: 500;
  padding: 12px 24px;
  border-radius: 999px;
  border: 1px solid rgba(255,213,79,0.25);
  cursor: not-allowed;
  opacity: 0.7;
}
.cover-img {
  width: 100%;
  border-radius: 16px;
  box-shadow: 0 40px 80px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.06);
  display: block;
}

/* ── Stats Strip ── */
.stats-strip {
  background: var(--surface);
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
}
.stats-inner {
  max-width: calc(var(--max-w) + 120px);
  margin: 0 auto;
  padding: 32px 24px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 24px;
  text-align: center;
}
.stat-num {
  font-family: var(--sans);
  font-size: 32px;
  font-weight: 700;
  color: var(--accent);
  line-height: 1;
  margin-bottom: 6px;
}
.stat-label {
  font-family: var(--sans);
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-muted);
}

/* ── Reading container ── */
.content-wrap {
  max-width: var(--max-w);
  margin: 0 auto;
  padding: 64px 24px 120px;
}

/* ── TOC ── */
#TOC {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r);
  padding: 28px 32px;
  margin-bottom: 64px;
}
#TOC h2 {
  font-family: var(--sans);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 20px;
  border-bottom: 1px solid var(--border);
  padding-bottom: 12px;
}
#TOC ul { list-style: none; display: grid; gap: 4px; }
#TOC li { font-family: var(--sans); font-size: 15px; }
#TOC a {
  color: var(--text-muted);
  text-decoration: none;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px;
  border-radius: 8px;
  transition: all 0.15s;
}
#TOC a::before { content: '→'; color: var(--accent); opacity: 0; transition: opacity 0.15s; font-size: 13px; }
#TOC a:hover { background: rgba(124,106,247,0.08); color: var(--text); }
#TOC a:hover::before { opacity: 1; }

/* ── Headings ── */
h1, h2, h3, h4 { font-family: var(--sans); line-height: 1.2; }
h1 {
  font-size: clamp(28px, 4vw, 40px);
  font-weight: 700;
  color: #fff;
  margin-top: 80px;
  margin-bottom: 24px;
  padding-top: 32px;
  border-top: 1px solid var(--border);
}
h1:first-of-type { margin-top: 0; border-top: none; padding-top: 0; }
h2 { font-size: 24px; font-weight: 600; color: var(--text); margin-top: 48px; margin-bottom: 16px; }
h3 {
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--accent);
  margin-top: 40px;
  margin-bottom: 12px;
}
h4 { font-size: 18px; font-weight: 600; color: var(--text); margin-top: 32px; margin-bottom: 10px; }

/* ── Body text ── */
p { margin-bottom: 1.4em; color: var(--text); }
strong { color: #fff; font-weight: 600; }
em { font-style: italic; color: var(--text-muted); }
a { color: var(--accent2); text-decoration: none; border-bottom: 1px solid rgba(79,195,247,0.3); transition: border-color 0.15s; }
a:hover { border-color: var(--accent2); }

/* ── Blockquote ── */
blockquote {
  border-left: 3px solid var(--accent);
  background: var(--surface);
  padding: 20px 24px;
  margin: 32px 0;
  border-radius: 0 var(--r) var(--r) 0;
  font-style: italic;
  color: var(--text-muted);
}
blockquote p:last-child { margin-bottom: 0; }

/* ── Lists ── */
ul, ol { padding-left: 28px; margin-bottom: 1.4em; }
li { margin-bottom: 8px; }

/* ── Chart figures ── */
.chart-figure {
  margin: 48px -32px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r);
  overflow: hidden;
}
@media (max-width: 840px) { .chart-figure { margin: 40px 0; } }
.chart-img { display: block; width: 100%; height: auto; }
figcaption {
  padding: 14px 20px;
  font-family: var(--sans);
  font-size: 13px;
  color: var(--text-muted);
  border-top: 1px solid var(--border);
  font-style: italic;
}

/* ── Manual / callout boxes ── */
.manual-box, .callout {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r);
  padding: 28px 32px;
  margin: 40px 0;
}
.manual-box strong { color: var(--accent); }

/* ── Code / pre ── */
pre {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: var(--r);
  padding: 20px;
  overflow-x: auto;
  font-size: 14px;
  margin: 24px 0;
}
code { font-family: 'SF Mono', 'Fira Code', monospace; font-size: 0.9em; color: var(--accent2); }
pre code { color: var(--text); }

/* ── Tables ── */
table { width: 100%; border-collapse: collapse; margin: 32px 0; font-family: var(--sans); font-size: 15px; }
thead { background: var(--surface2); }
th { padding: 12px 16px; text-align: left; font-weight: 600; color: var(--text); border-bottom: 1px solid var(--border); }
td { padding: 12px 16px; border-bottom: 1px solid var(--border); color: var(--text-muted); }
tr:hover td { background: rgba(255,255,255,0.02); }

/* ── Chapter drop caps ── */
.chapter-start > p:first-of-type::first-letter {
  float: left;
  font-size: 4.2em;
  font-family: var(--serif);
  font-weight: 600;
  line-height: 0.8;
  margin: 4px 12px -4px 0;
  color: var(--accent);
}

/* ── Footer ── */
.site-footer {
  border-top: 1px solid var(--border);
  background: var(--surface);
  padding: 40px 24px;
  text-align: center;
}
.site-footer p { font-family: var(--sans); font-size: 13px; color: var(--text-muted); margin-bottom: 8px; }
.site-footer a { color: var(--accent); border-bottom: none; }

/* ── Reading progress bar ── */
#progress-bar {
  position: fixed;
  top: 0;
  left: 0;
  width: 0%;
  height: 3px;
  background: linear-gradient(90deg, var(--accent), var(--accent2));
  z-index: 9999;
  transition: width 0.1s linear;
  box-shadow: 0 0 8px rgba(124,106,247,0.6);
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent); }
'''

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="Statecraft: A How-To Guide for the Accidental Founder — an open-access narrative non-fiction book on state-building written in the style of Malcolm Gladwell.">
  <meta property="og:title" content="STATECRAFT — A How-To Guide for the Accidental Founder">
  <meta property="og:description" content="Why building a country is harder than you think. 67,600 words on sovereignty, legitimacy, currency, housing, and digital governance.">
  <meta property="og:image" content="statecraft_book_cover.jpg">
  <title>STATECRAFT — A How-To Guide for the Accidental Founder</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <style>{css}</style>
</head>
<body>

<div id="progress-bar"></div>

<header>
  <div class="header-inner">
    <a href="#" class="header-wordmark">Statecraft</a>
    <nav>
      <a href="#TOC">Contents</a>
      <a href="statecraft_manual.pdf" target="_blank">↓ PDF</a>
      <span class="nav-pill coming-soon">🎧 Audiobook Coming Soon</span>
    </nav>
  </div>
</header>

<section class="hero">
  <div class="hero-text">
    <span class="hero-label">Open Access · July 2026</span>
    <h1 class="hero-title">STATECRAFT</h1>
    <p class="hero-subtitle">A How-To Guide for the Accidental Founder<br><em>Or: Why Building a Country is Harder Than You Think</em></p>
    <p class="hero-meta">By <strong>Antigravity &amp; Algimantas</strong> · 67,600 words · 12 Chapters</p>
    <div class="hero-actions">
      <a href="#TOC" class="btn-primary">📖 Start Reading</a>
      <a href="statecraft_manual.pdf" class="btn-secondary" target="_blank">↓ Download PDF</a>
      <span class="btn-disabled">🎧 Audiobook Soon</span>
    </div>
  </div>
  <div>
    <img src="statecraft_book_cover.jpg" class="cover-img" alt="Statecraft Book Cover" width="340">
  </div>
</section>

<div class="stats-strip">
  <div class="stats-inner">
    <div><div class="stat-num">67,600</div><div class="stat-label">Words</div></div>
    <div><div class="stat-num">12</div><div class="stat-label">Chapters</div></div>
    <div><div class="stat-num">11</div><div class="stat-label">Countries Studied</div></div>
    <div><div class="stat-num">7.5h</div><div class="stat-label">Audiobook (Soon)</div></div>
    <div><div class="stat-num">CC BY</div><div class="stat-label">Open License</div></div>
  </div>
</div>

<div class="content-wrap">
  {body}
</div>

<footer class="site-footer">
  <p>Published under <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank">CC BY 4.0</a> — free to share, adapt, and build upon with attribution.</p>
  <p><a href="https://github.com/Algiras/Statecraft" target="_blank">github.com/Algiras/Statecraft</a></p>
</footer>

<script>
// Reading progress bar
const bar = document.getElementById('progress-bar');
document.addEventListener('scroll', () => {{
  const docH = document.documentElement.scrollHeight - window.innerHeight;
  const progress = (window.scrollY / docH) * 100;
  bar.style.width = progress + '%';
}});
</script>

</body>
</html>'''

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    if os.path.exists("body.html"):
        os.remove("body.html")

    print("Success! Premium index.html generated.")

if __name__ == "__main__":
    main()
