#!/usr/bin/env python3
"""
Compiles the book.md markdown to index.html with a premium, modern reading layout.
Charts are embedded inline as <img> elements at the right conceptual points.
Fixes: mermaid rendering, table overflow wrapping, MathJax, tight lists.
"""

import os
import re
import subprocess
import html as htmllib
import tempfile

CHARTS = {
    "hardware_vs_software": "img_hardware_vs_software.jpg",
    "twelve_pillars": "img_twelve_pillars.jpg",
    "somaliland_vs_somalia": "img_somaliland_vs_somalia.jpg",
    "currency_board": "img_currency_board.jpg",
    "sovereignty_spectrum": "img_sovereignty_spectrum.jpg",
}

RELEASE_URL = "https://github.com/Algiras/Statecraft/releases/latest/download"
PDF_URL = f"{RELEASE_URL}/statecraft_manual.pdf"
EPUB_URL = f"{RELEASE_URL}/statecraft.epub"

def fix_tight_lists(md):
    """Insert blank lines before list items that follow paragraph text."""
    lines = md.split("\n")
    result = []
    for i, line in enumerate(lines):
        if i > 0 and re.match(r"^(\*   |\-   |\d+\.  )", line):
            prev = lines[i - 1]
            if prev.strip() and not re.match(r"^(\*   |\-   |\d+\.  |#|>|```|\s*$)", prev):
                if result and result[-1].strip():
                    result.append("")
        result.append(line)
    return "\n".join(result)

def extract_chapters(body):
    chapters = []
    for m in re.finditer(r'<h1\s+[^>]*id="([^"]+)"[^>]*>(.*?)</h1>', body, re.DOTALL):
        inner = m.group(2)
        num_m = re.search(r'header-section-number">(\d+)</span>\s*(.*)', inner, re.DOTALL)
        if num_m:
            num, title_html = num_m.group(1), num_m.group(2)
        else:
            num = str(len(chapters) + 1)
            title_html = inner
        title = re.sub(r"<[^>]+>", "", title_html)
        title = re.sub(r"\s+", " ", title).strip()
        chapters.append({"id": m.group(1), "num": num, "title": title})
    return chapters

def extract_sections(body, level, prefix=""):
    """Extract h2 (or other) headings for front/back matter navigation."""
    sections = []
    pattern = rf'<h{level}\s+[^>]*id="([^"]+)"[^>]*>(.*?)</h{level}>'
    for m in re.finditer(pattern, body, re.DOTALL):
        title = re.sub(r"<[^>]+>", "", m.group(2))
        title = re.sub(r"\s+", " ", title).strip()
        sections.append({"id": m.group(1), "title": title, "num": prefix})
    return sections

def shorten_title(title, max_len=52):
    if len(title) <= max_len:
        return title
    return title[: max_len - 1] + "…"

def build_toc_list_items(sections, numbered=True):
    items = []
    for sec in sections:
        label = shorten_title(sec["title"])
        anchor = sec.get("anchor", sec["id"])
        num_html = (
            f'<span class="toc-num">{sec["num"]}</span>'
            if numbered and sec.get("num")
            else '<span class="toc-num toc-num-dot">·</span>'
        )
        items.append(
            f'<li><a href="#{anchor}">{num_html}'
            f'<span class="toc-title">{htmllib.escape(label)}</span></a></li>'
        )
    return "\n".join(items)

def build_toc_group(title, sections, extra_class="", numbered=True):
    if not sections:
        return ""
    items = build_toc_list_items(sections, numbered=numbered)
    return f'''<div class="toc-group">
  <h3 class="toc-group-title">{htmllib.escape(title)}</h3>
  <ol class="toc-list {extra_class}">{items}</ol>
</div>'''

def build_toc_page(front, chapters, back):
    first_anchor = chapters[0]["anchor"] if chapters else "TOC"
    groups = (
        build_toc_group("Front Matter", front, "toc-front-list", numbered=False)
        + build_toc_group("Chapters", chapters, "toc-page-list", numbered=True)
        + build_toc_group("Back Matter", back, "toc-back-list", numbered=False)
    )
    return f'''<section id="TOC" class="toc-page" aria-labelledby="toc-heading">
  <h2 id="toc-heading">Table of Contents</h2>
  <p class="toc-lead">A complete open-access manual on the software of nationhood — from copyright and reading guide through twelve narrative chapters to references and sources.</p>
  <div class="toc-groups">{groups}</div>
  <p class="toc-actions"><a href="#copyright" class="btn-secondary">Front Matter</a> <a href="#{first_anchor}" class="btn-primary">Start Reading →</a></p>
</section>'''

def build_quick_jump_bar(chapters, back):
    links = []
    for ch in chapters:
        anchor = ch.get("anchor", ch["id"])
        if anchor == "intro":
            label = "Intro"
        elif anchor == "conclusion":
            label = "Conclusion"
        elif anchor.startswith("chapter-"):
            label = f"Ch {anchor.split('-', 1)[1]}"
        else:
            label = shorten_title(ch["title"], 16)
        links.append(f'<a href="#{anchor}" class="jump-link">{htmllib.escape(label)}</a>')
    for sec in back:
        if sec["id"] in ("references", "sources"):
            links.append(
                f'<a href="#{sec.get("anchor", sec["id"])}" class="jump-link jump-ref">'
                f'{htmllib.escape("Refs" if sec["id"] == "references" else "Sources")}</a>'
            )
    inner = "\n".join(links)
    return f'''<nav class="chapter-jump" aria-label="Jump to chapter or references">
  <span class="jump-label">Jump to</span>
  <div class="jump-links">{inner}</div>
</nav>'''

def build_sidebar_toc(front, chapters, back):
    groups = (
        build_toc_group("Front Matter", front, "sidebar-list", numbered=False)
        + build_toc_group("Chapters", chapters, "sidebar-list", numbered=True)
        + build_toc_group("Back Matter", back, "sidebar-list", numbered=False)
    )
    return f'''<aside id="sidebar-toc" class="sidebar-toc" aria-label="Book navigation">
  <div class="sidebar-inner">
    <div class="sidebar-header">
      <span class="sidebar-title">Contents</span>
      <button type="button" class="sidebar-close" id="btn-sidebar-close" aria-label="Close table of contents">×</button>
    </div>
    <div class="toc-groups sidebar-groups">{groups}</div>
  </div>
</aside>
<div class="sidebar-overlay" id="sidebar-overlay" hidden></div>'''

def chapter_nav_html(index, chapters):
    if index > 0:
        p = chapters[index - 1]
        prev_link = (
            f'<a href="#{p.get("anchor", p["id"])}" class="chapter-nav-link prev">'
            f'<span class="nav-dir">← Previous</span>'
            f'<span class="nav-title">{htmllib.escape(shorten_title(p["title"], 44))}</span></a>'
        )
    else:
        prev_link = '<span class="chapter-nav-link prev disabled" aria-hidden="true"></span>'
    if index < len(chapters) - 1:
        n = chapters[index + 1]
        next_link = (
            f'<a href="#{n.get("anchor", n["id"])}" class="chapter-nav-link next">'
            f'<span class="nav-dir">Next →</span>'
            f'<span class="nav-title">{htmllib.escape(shorten_title(n["title"], 44))}</span></a>'
        )
    else:
        next_link = (
            f'<a href="#references" class="chapter-nav-link next">'
            f'<span class="nav-dir">Next →</span>'
            f'<span class="nav-title">References</span></a>'
        )
    return (
        f'<nav class="chapter-nav" aria-label="Chapter navigation">'
        f'{prev_link}'
        f'<a href="#TOC" class="chapter-nav-link contents">Contents</a>'
        f'{next_link}</nav>'
    )

def assign_chapter_anchors(chapters):
    for i, ch in enumerate(chapters):
        if i == 0:
            ch["anchor"] = "intro"
        elif i == len(chapters) - 1:
            ch["anchor"] = "conclusion"
        else:
            ch["anchor"] = f"chapter-{i}"
    return chapters

def assign_section_anchors(sections):
    for sec in sections:
        sec["anchor"] = sec["id"]
    return sections

def inject_anchor_targets(body, sections, tag):
    for sec in sections:
        anchor = sec.get("anchor", sec["id"])
        sid = sec["id"]
        pattern = rf'(<{tag}[^>]*\bid="{re.escape(sid)}"[^>]*>)'
        replacement = f'<span id="{anchor}" class="anchor-target" aria-hidden="true"></span>\\1'
        body = re.sub(pattern, replacement, body, count=1)
    return body

def inject_heading_permalinks(body, sections, tag):
    for sec in sections:
        anchor = sec.get("anchor", sec["id"])
        sid = sec["id"]
        plink = (
            f'<a class="heading-anchor" href="#{anchor}" '
            f'aria-label="Link to {htmllib.escape(sec["title"])}" title="#{anchor}">¶</a>'
        )
        pattern = rf'(<{tag}[^>]*\bid="{re.escape(sid)}"[^>]*>)'
        body = re.sub(pattern, r"\1" + plink, body, count=1)
    return body

def mark_chapters(body):
    return re.sub(r"<h1(\s+)", r'<h1 class="chapter-start"\1', body)

def inject_chapter_nav(body, chapters):
    for i in range(len(chapters) - 1, -1, -1):
        ch = chapters[i]
        pattern = r'(<h1[^>]*id="' + re.escape(ch["id"]) + r'"[^>]*>.*?</h1>)'
        m = re.search(pattern, body, re.DOTALL)
        if not m:
            continue
        nav = chapter_nav_html(i, chapters)
        body = body[: m.end()] + "\n" + nav + body[m.end() :]
    return body

def wrap_book_parts(body):
    """Split compiled HTML into front matter, main text, and back matter."""
    intro_m = re.search(r'<h1[^>]*id="introduction[^"]*"', body, re.IGNORECASE)
    back_m = re.search(r'<h2[^>]*id="acknowledgments"', body, re.IGNORECASE)

    if not intro_m:
        return f'<article class="book-part book-text" id="book-text">{body}</article>'

    front_html = body[: intro_m.start()].strip()
    if back_m and back_m.start() > intro_m.start():
        main_html = body[intro_m.start() : back_m.start()].strip()
        back_html = body[back_m.start() :].strip()
    else:
        main_html = body[intro_m.start() :].strip()
        back_html = ""

    parts = []
    if front_html:
        front_html = re.sub(r"<h2", r'<h2 class="matter-heading"', front_html)
        parts.append(
            f'<section class="book-part front-matter" id="front-matter" aria-label="Front matter">\n{front_html}\n</section>'
        )
    parts.append(
        f'<article class="book-part book-text" id="book-text" aria-label="Book chapters">\n{main_html}\n</article>'
    )
    if back_html:
        back_html = re.sub(r"<h2", r'<h2 class="matter-heading"', back_html)
        parts.append(
            f'<section class="book-part back-matter" id="back-matter" aria-label="Back matter">\n{back_html}\n</section>'
        )
    return "\n".join(parts)

def style_footnotes(body):
    return re.sub(
        r'<section class="footnotes"',
        r'<section class="footnotes book-footnotes" role="doc-endnotes"',
        body,
    )

def main():
    print("Merging chapters (if needed)...")
    if not os.path.exists("book.md"):
        subprocess.run(["python", "merge_chapters.py"], check=True)

    print("Compiling manuscript to HTML body using Pandoc...")
    with open("book.md", "r", encoding="utf-8") as f:
        manuscript = fix_tight_lists(f.read())

    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as tmp:
        tmp.write(manuscript)
        tmp_path = tmp.name

    cmd = [
        "pandoc", tmp_path,
        "-o", "body.html",
        "--toc",
        "--toc-depth=1",
        "--number-sections",
        "--from", "markdown+footnotes",
        "--mathjax",
    ]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return
    finally:
        os.remove(tmp_path)

    with open("body.html", "r", encoding="utf-8") as f:
        body = f.read()

    # ── Fix 1: Mermaid — Pandoc wraps in <pre class="mermaid"><code>...</code></pre>
    # Mermaid.js needs plain text inside <pre class="mermaid"> (no inner <code> tag)
    def fix_mermaid(m):
        inner = m.group(1)
        # Pandoc HTML-escapes the content inside <code>; unescape it
        inner = inner.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
        return f'<pre class="mermaid">{inner}</pre>'
    body = re.sub(
        r'<pre class="mermaid"><code>(.*?)</code></pre>',
        fix_mermaid,
        body,
        flags=re.DOTALL
    )

    # ── Fix 2: Strip LaTeX page breaks (used by PDF build only)
    body = re.sub(r'\\newpage\s*', '', body)

    # ── Fix 3: Tables — wrap every <table> in a scrollable div
    body = re.sub(
        r'(<table\b)',
        r'<div class="table-wrap">\1',
        body
    )
    body = body.replace('</table>', '</table></div>')

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

    chapters = extract_chapters(body)
    intro_m = re.search(r'<h1[^>]*id="introduction', body, re.I)
    front = extract_sections(body[: intro_m.start()] if intro_m else "", 2)
    back_start = re.search(r'<h2[^>]*id="acknowledgments"', body, re.I)
    back = extract_sections(body[back_start.start() :] if back_start else "", 2)

    chapters = assign_chapter_anchors(chapters)
    front = assign_section_anchors(front)
    back = assign_section_anchors(back)

    body = inject_anchor_targets(body, chapters, "h1")
    body = inject_anchor_targets(body, front + back, "h2")
    body = inject_heading_permalinks(body, chapters, "h1")
    body = inject_heading_permalinks(body, front + back, "h2")

    body = mark_chapters(body)
    body = inject_chapter_nav(body, chapters)
    body = style_footnotes(body)
    body = wrap_book_parts(body)

    toc_page = build_toc_page(front, chapters, back)
    sidebar = build_sidebar_toc(front, chapters, back)
    jump_bar = build_quick_jump_bar(chapters, back)
    book_content = toc_page + "\n" + body

    css = '''/* ===== STATECRAFT — Premium Reading Stylesheet ===== */
@import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,600;1,400&family=Inter:wght@300;400;500;600;700&display=swap');

:root {
  --bg:          #0f0f13;
  --surface:     #17171e;
  --surface2:    #1e1e28;
  --border:      #2a2a38;
  --text:        #e8e8f0;
  --text-muted:  #7a7a9a;
  --heading:     #ffffff;
  --heading-strong: #ffffff;
  --accent:      #7c6af7;
  --accent2:     #4fc3f7;
  --accent3:     #66bb6a;
  --gold:        #ffd54f;
  --serif:       'Lora', Georgia, serif;
  --sans:        'Inter', system-ui, sans-serif;
  --max-w:       780px;
  --r:           14px;
  --header-h:    58px;
  color-scheme: dark;
}

html[data-theme="light"] {
  --bg:          #f4f4f8;
  --surface:     #ffffff;
  --surface2:    #eef0f6;
  --border:      #d8dbe8;
  --text:        #1a1a24;
  --text-muted:  #5c5c78;
  --heading:     #12121a;
  --heading-strong: #0a0a10;
  color-scheme: light;
}

html[data-font-size="sm"] body { font-size: 17px; }
html[data-font-size="md"] body { font-size: 19px; }
html[data-font-size="lg"] body { font-size: 21px; }
html[data-font-size="xl"] body { font-size: 23px; }

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html { scroll-behavior: smooth; scroll-padding-top: calc(var(--header-h) + 16px); }

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
  z-index: 200;
  background: color-mix(in srgb, var(--bg) 88%, transparent);
  backdrop-filter: blur(24px) saturate(180%);
  -webkit-backdrop-filter: blur(24px) saturate(180%);
  border-bottom: 1px solid var(--border);
}
.header-inner {
  max-width: 1280px;
  margin: 0 auto;
  padding: 10px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  min-height: var(--header-h);
}
.header-wordmark {
  font-family: var(--sans);
  font-weight: 700;
  font-size: 15px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text);
  text-decoration: none;
  flex-shrink: 0;
}
.header-nav { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
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

/* ── Reader controls ── */
.reader-controls {
  display: flex;
  gap: 4px;
  align-items: center;
  margin-left: auto;
}
.ctrl-btn {
  font-family: var(--sans);
  font-size: 14px;
  font-weight: 600;
  width: 34px;
  height: 34px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.15s;
  line-height: 1;
}
.ctrl-btn:hover, .ctrl-btn.active {
  color: var(--text);
  border-color: var(--accent);
  background: rgba(124,106,247,0.12);
}
.ctrl-btn.theme-toggle { font-size: 16px; }
.ctrl-btn.theme-toggle .theme-icon-dark,
html[data-theme="light"] .ctrl-btn.theme-toggle .theme-icon-light { display: none; }
html[data-theme="light"] .ctrl-btn.theme-toggle .theme-icon-dark { display: inline; }
@media (max-width: 900px) {
  .header-nav a:not([href="#TOC"]):not([href="#references"]):not([href="#sources"]) { display: none; }
}

/* ── Book layout ── */
.book-shell {
  display: grid;
  grid-template-columns: minmax(220px, 260px) minmax(0, 1fr);
  align-items: start;
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 20px 120px;
  gap: 36px;
}
.book-main { min-width: 0; }
body.focus-mode .hero,
body.focus-mode .stats-strip,
body.focus-mode .chapter-jump { display: none; }
body.focus-mode .book-shell { max-width: var(--max-w); grid-template-columns: 1fr; }
body.focus-mode .sidebar-toc,
body.focus-mode .sidebar-overlay { display: none !important; }

.sidebar-toc {
  position: sticky;
  top: calc(var(--header-h) + 16px);
  max-height: calc(100vh - var(--header-h) - 32px);
  overflow-y: auto;
  border: 1px solid var(--border);
  border-radius: var(--r);
  background: var(--surface);
}
.sidebar-inner { padding: 16px 12px; }
.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding: 0 8px 10px;
  border-bottom: 1px solid var(--border);
}
.sidebar-title {
  font-family: var(--sans);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--accent);
}
.sidebar-close { display: none; }
.sidebar-overlay {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.45);
  z-index: 250;
}
.sidebar-overlay.visible { display: block; }

.toc-list { list-style: none; display: grid; gap: 2px; counter-reset: toc; }
.toc-list a {
  display: grid;
  grid-template-columns: 28px 1fr;
  gap: 8px;
  align-items: start;
  padding: 7px 8px;
  border-radius: 8px;
  color: var(--text-muted);
  text-decoration: none;
  font-family: var(--sans);
  font-size: 13px;
  line-height: 1.35;
  transition: all 0.15s;
}
.toc-list a:hover, .toc-list a.active {
  background: rgba(124,106,247,0.1);
  color: var(--text);
}
.toc-num {
  font-weight: 700;
  color: var(--accent);
  font-size: 12px;
  padding-top: 1px;
}
.toc-title { min-width: 0; }

.toc-page {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r);
  padding: 32px 36px;
  margin-bottom: 56px;
}
.toc-page h2 {
  font-family: var(--sans);
  font-size: clamp(24px, 3vw, 32px);
  font-weight: 700;
  color: var(--heading);
  margin-bottom: 12px;
}
.toc-lead {
  font-family: var(--sans);
  font-size: 15px;
  color: var(--text-muted);
  margin-bottom: 24px;
  line-height: 1.6;
}
.toc-page-list a { font-size: 15px; padding: 10px 12px; }
.toc-actions { margin-top: 28px; display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }
.toc-groups { display: grid; gap: 28px; }
.toc-group-title {
  font-family: var(--sans);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}
.toc-num-dot { opacity: 0.5; font-weight: 400; }
.sidebar-groups .toc-group { margin-bottom: 16px; }

.book-part { margin-bottom: 48px; }
.front-matter, .back-matter {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r);
  padding: 36px 40px;
  margin-bottom: 48px;
}
.matter-heading {
  font-family: var(--sans);
  font-size: 22px;
  font-weight: 600;
  color: var(--heading);
  margin-top: 40px;
  margin-bottom: 16px;
  padding-top: 24px;
  border-top: 1px solid var(--border);
}
.front-matter .matter-heading:first-child,
.back-matter .matter-heading:first-child {
  margin-top: 0;
  padding-top: 0;
  border-top: none;
}

sup.footnote-ref a {
  color: var(--accent);
  text-decoration: none;
  font-weight: 600;
  padding: 0 2px;
}
section.footnotes, section.book-footnotes {
  margin-top: 48px;
  padding: 28px 32px;
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: var(--r);
  font-family: var(--sans);
  font-size: 14px;
  line-height: 1.6;
}
section.footnotes h2, section.book-footnotes h2 {
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 16px;
}
section.footnotes ol, section.book-footnotes ol { padding-left: 24px; margin: 0; }
section.footnotes li, section.book-footnotes li { margin-bottom: 10px; color: var(--text-muted); }
section.footnotes li p, section.book-footnotes li p { margin-bottom: 0.4em; }
a.footnote-back { color: var(--accent2); margin-left: 6px; }

.chapter-nav {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 12px;
  align-items: stretch;
  margin: 28px 0 12px;
  padding: 16px 0 0;
  border-top: 1px solid var(--border);
}
.chapter-nav-link {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: var(--r);
  background: var(--surface);
  color: var(--text-muted);
  text-decoration: none;
  font-family: var(--sans);
  font-size: 13px;
  transition: all 0.15s;
  min-height: 64px;
}
.chapter-nav-link:hover { border-color: var(--accent); color: var(--text); background: rgba(124,106,247,0.08); }
.chapter-nav-link.prev { text-align: left; }
.chapter-nav-link.next { text-align: right; }
.chapter-nav-link.contents {
  align-items: center;
  justify-content: center;
  font-weight: 600;
  color: var(--accent);
  min-height: 0;
}
.chapter-nav-link.disabled { visibility: hidden; }
.nav-dir { font-size: 11px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--accent); }
.nav-title { color: var(--text); font-size: 13px; line-height: 1.35; }

@media (max-width: 1024px) {
  .book-shell { grid-template-columns: 1fr; gap: 0; }
  .sidebar-toc {
    position: fixed;
    top: 0;
    left: 0;
    width: min(320px, 88vw);
    height: 100vh;
    max-height: none;
    z-index: 300;
    border-radius: 0;
    transform: translateX(-105%);
    transition: transform 0.25s ease;
  }
  .sidebar-toc.open { transform: translateX(0); }
  .sidebar-close {
    display: block;
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: 24px;
    cursor: pointer;
    line-height: 1;
    padding: 0 4px;
  }
  .chapter-nav { grid-template-columns: 1fr; }
  .chapter-nav-link.next { text-align: left; }
}
@media (max-width: 640px) {
  .reader-controls .ctrl-btn:not(#btn-toc):not(#btn-theme) { display: none; }
}

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
  color: var(--heading);
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

/* ── Chapter jump bar ── */
.chapter-jump {
  max-width: 1280px;
  margin: 0 auto;
  padding: 14px 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  border-bottom: 1px solid var(--border);
  background: var(--surface2);
}
.jump-label {
  font-family: var(--sans);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-muted);
  flex-shrink: 0;
}
.jump-links {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.jump-link {
  font-family: var(--sans);
  font-size: 12px;
  font-weight: 500;
  padding: 5px 10px;
  border-radius: 999px;
  border: 1px solid var(--border);
  color: var(--text-muted);
  text-decoration: none;
  transition: all 0.15s;
}
.jump-link:hover { color: var(--text); border-color: var(--accent); background: rgba(124,106,247,0.1); }
.jump-link.jump-ref { color: var(--accent); border-color: rgba(124,106,247,0.35); }

/* ── Section anchors ── */
.anchor-target {
  display: block;
  position: relative;
  scroll-margin-top: calc(var(--header-h) + 20px);
}
h1, h2.matter-heading { scroll-margin-top: calc(var(--header-h) + 20px); }
.heading-anchor {
  margin-left: 10px;
  font-family: var(--sans);
  font-size: 0.55em;
  font-weight: 600;
  color: var(--text-muted);
  text-decoration: none;
  opacity: 0;
  transition: opacity 0.15s, color 0.15s;
  vertical-align: middle;
}
h1:hover .heading-anchor,
h2.matter-heading:hover .heading-anchor,
.heading-anchor:focus { opacity: 1; color: var(--accent); }
.heading-anchor:hover { color: var(--accent2); }

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
  margin: 0;
  padding: 48px 0 0;
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
.toc-page-list a::before { display: none; }

/* ── Headings ── */
h1, h2, h3, h4 { font-family: var(--sans); line-height: 1.2; }
h1 {
  font-size: clamp(28px, 4vw, 40px);
  font-weight: 700;
  color: var(--heading);
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
strong { color: var(--heading-strong); font-weight: 600; }
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

/* ── Mermaid diagrams ── */
pre.mermaid {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r);
  padding: 32px 20px;
  text-align: center;
  overflow: visible;
  font-size: inherit;
}
pre.mermaid svg {
  max-width: 100%;
  height: auto;
}

/* ── Tables ── */
.table-wrap {
  overflow-x: auto;
  margin: 32px 0;
  border-radius: var(--r);
  border: 1px solid var(--border);
}
code { font-family: 'SF Mono', 'Fira Code', monospace; font-size: 0.9em; color: var(--accent2); }
pre code { color: var(--text); }

/* ── Tables (inside .table-wrap) ── */
table { width: 100%; border-collapse: collapse; margin: 0; font-family: var(--sans); font-size: 15px; min-width: 500px; }
thead { background: var(--surface2); }
th { padding: 12px 16px; text-align: left; font-weight: 600; color: var(--text); border-bottom: 2px solid var(--border); white-space: nowrap; }
td { padding: 11px 16px; border-bottom: 1px solid var(--border); color: var(--text-muted); vertical-align: top; }
tr:last-child td { border-bottom: none; }
tr:hover td { background: rgba(255,255,255,0.025); color: var(--text); }

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
.footer-anchors a { color: var(--text-muted); }
.footer-anchors a:hover { color: var(--accent); }

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
  <script>
    (function() {{
      var theme;
      try {{ theme = localStorage.getItem('statecraft-theme'); }} catch (e) {{}}
      if (!theme) {{
        theme = window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
      }}
      document.documentElement.dataset.theme = theme;
    }})();
  </script>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
  <script>
    window.MathJax = {{
      tex: {{ inlineMath: [['\\\\(', '\\\\)']], displayMath: [['\\\\[', '\\\\]']] }},
      options: {{ skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre'] }}
    }};
  </script>
  <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml-full.js" async></script>
  <style>{css}</style>
</head>
<body>

<div id="progress-bar"></div>

<header>
  <div class="header-inner">
    <a href="#" class="header-wordmark">Statecraft</a>
    <div class="reader-controls" role="toolbar" aria-label="Reading controls">
      <button type="button" class="ctrl-btn" id="btn-toc" title="Table of contents" aria-label="Table of contents">☰</button>
      <button type="button" class="ctrl-btn" id="btn-font-down" title="Smaller text" aria-label="Decrease font size">A−</button>
      <button type="button" class="ctrl-btn" id="btn-font-up" title="Larger text" aria-label="Increase font size">A+</button>
      <button type="button" class="ctrl-btn theme-toggle" id="btn-theme" title="Switch to light mode" aria-label="Toggle light and dark reading theme">
        <span class="theme-icon-light" aria-hidden="true">☀</span>
        <span class="theme-icon-dark" aria-hidden="true">🌙</span>
      </button>
      <button type="button" class="ctrl-btn" id="btn-focus" title="Focus mode" aria-label="Focus reading mode">◎</button>
    </div>
    <nav class="header-nav">
      <a href="#TOC">Contents</a>
      <a href="#intro">Intro</a>
      <a href="#references">References</a>
      <a href="#sources">Sources</a>
      <a href="{PDF_URL}" target="_blank" rel="noopener">↓ PDF</a>
      <a href="{EPUB_URL}" target="_blank" rel="noopener">↓ EPUB</a>
      <span class="nav-pill coming-soon">🎧 Audiobook Soon</span>
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
      <a href="{PDF_URL}" class="btn-secondary" target="_blank" rel="noopener">↓ Download PDF</a>
      <a href="{EPUB_URL}" class="btn-secondary" target="_blank" rel="noopener">↓ Download EPUB</a>
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

{jump_bar}

<div class="book-shell">
  {sidebar}
  <main class="book-main">
    <div class="content-wrap">
      {book_content}
    </div>
  </main>
</div>

<footer class="site-footer">
  <p>Published under <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank">CC BY 4.0</a> — free to share, adapt, and build upon with attribution.</p>
  <p class="footer-anchors">
    <a href="#TOC">Contents</a> ·
    <a href="#intro">Introduction</a> ·
    <a href="#references">References</a> ·
    <a href="#sources">Sources</a> ·
    <a href="#acknowledgments">Acknowledgments</a>
  </p>
  <p><a href="https://github.com/Algiras/Statecraft" target="_blank">github.com/Algiras/Statecraft</a></p>
</footer>

<script>
// Reading progress bar
const bar = document.getElementById('progress-bar');
document.addEventListener('scroll', () => {{
  const docH = document.documentElement.scrollHeight - window.innerHeight;
  const progress = docH > 0 ? (window.scrollY / docH) * 100 : 0;
  bar.style.width = progress + '%';
}});

// Reader controls
(function() {{
  const root = document.documentElement;
  const body = document.body;
  const sizes = ['sm', 'md', 'lg', 'xl'];
  const sidebar = document.getElementById('sidebar-toc');
  const overlay = document.getElementById('sidebar-overlay');

  function load(key, fallback) {{
    try {{ return localStorage.getItem(key) || fallback; }} catch (e) {{ return fallback; }}
  }}
  function save(key, value) {{
    try {{ localStorage.setItem(key, value); }} catch (e) {{}}
  }}

  root.dataset.theme = load('statecraft-theme', '');
  if (!root.dataset.theme) {{
    root.dataset.theme = window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  }}
  root.dataset.fontSize = load('statecraft-font', 'md');
  if (load('statecraft-focus', '0') === '1') body.classList.add('focus-mode');

  const MERMAID_THEMES = {{
    dark: {{
      theme: 'dark',
      themeVariables: {{
        background: '#17171e',
        primaryColor: '#7c6af7',
        primaryTextColor: '#e8e8f0',
        lineColor: '#4a4a6a',
        fontSize: '15px'
      }}
    }},
    light: {{
      theme: 'neutral',
      themeVariables: {{
        background: '#ffffff',
        primaryColor: '#7c6af7',
        primaryTextColor: '#1a1a24',
        lineColor: '#9a9ab8',
        fontSize: '15px'
      }}
    }}
  }};

  function cacheMermaidSources() {{
    document.querySelectorAll('pre.mermaid').forEach((el) => {{
      if (!el.dataset.source) el.dataset.source = el.textContent.trim();
    }});
  }}

  async function renderMermaid(theme) {{
    if (typeof mermaid === 'undefined') return;
    const cfg = MERMAID_THEMES[theme === 'light' ? 'light' : 'dark'];
    mermaid.initialize({{ startOnLoad: false, ...cfg }});
    document.querySelectorAll('pre.mermaid').forEach((el) => {{
      el.textContent = el.dataset.source || el.textContent;
      el.removeAttribute('data-processed');
    }});
    try {{
      await mermaid.run({{ nodes: document.querySelectorAll('pre.mermaid') }});
    }} catch (e) {{}}
  }}

  cacheMermaidSources();
  renderMermaid(root.dataset.theme);

  function setFontSize(idx) {{
    root.dataset.fontSize = sizes[Math.max(0, Math.min(sizes.length - 1, idx))];
    save('statecraft-font', root.dataset.fontSize);
  }}
  setFontSize(sizes.indexOf(root.dataset.fontSize) >= 0 ? sizes.indexOf(root.dataset.fontSize) : 1);

  document.getElementById('btn-font-down').addEventListener('click', () => {{
    setFontSize(sizes.indexOf(root.dataset.fontSize) - 1);
  }});
  document.getElementById('btn-font-up').addEventListener('click', () => {{
    setFontSize(sizes.indexOf(root.dataset.fontSize) + 1);
  }});

  const themeBtn = document.getElementById('btn-theme');
  function syncThemeBtn() {{
    const isLight = root.dataset.theme === 'light';
    themeBtn.classList.toggle('active', isLight);
    themeBtn.title = isLight ? 'Switch to dark mode' : 'Switch to light mode';
    themeBtn.setAttribute('aria-label', isLight ? 'Switch to dark reading theme' : 'Switch to light reading theme');
  }}
  syncThemeBtn();
  themeBtn.addEventListener('click', () => {{
    root.dataset.theme = root.dataset.theme === 'light' ? 'dark' : 'light';
    save('statecraft-theme', root.dataset.theme);
    syncThemeBtn();
    renderMermaid(root.dataset.theme);
  }});

  const focusBtn = document.getElementById('btn-focus');
  function syncFocusBtn() {{
    focusBtn.classList.toggle('active', body.classList.contains('focus-mode'));
  }}
  syncFocusBtn();
  focusBtn.addEventListener('click', () => {{
    body.classList.toggle('focus-mode');
    save('statecraft-focus', body.classList.contains('focus-mode') ? '1' : '0');
    syncFocusBtn();
  }});

  function openSidebar() {{
    sidebar.classList.add('open');
    overlay.hidden = false;
    overlay.classList.add('visible');
  }}
  function closeSidebar() {{
    sidebar.classList.remove('open');
    overlay.classList.remove('visible');
    overlay.hidden = true;
  }}

  document.getElementById('btn-toc').addEventListener('click', () => {{
    if (window.matchMedia('(min-width: 1025px)').matches) {{
      document.getElementById('TOC').scrollIntoView({{ behavior: 'smooth', block: 'start' }});
      return;
    }}
    if (sidebar.classList.contains('open')) closeSidebar();
    else openSidebar();
  }});
  document.getElementById('btn-sidebar-close').addEventListener('click', closeSidebar);
  overlay.addEventListener('click', closeSidebar);
  sidebar.querySelectorAll('a').forEach((link) => {{
    link.addEventListener('click', () => {{
      if (window.matchMedia('(max-width: 1024px)').matches) closeSidebar();
    }});
  }});

  // Highlight active chapter in sidebar
  const chapterLinks = Array.from(document.querySelectorAll('.sidebar-list a'));
  const chapters = chapterLinks.map((a) => document.querySelector(a.getAttribute('href'))).filter(Boolean);
  if (chapters.length && 'IntersectionObserver' in window) {{
    const observer = new IntersectionObserver((entries) => {{
      entries.forEach((entry) => {{
        if (entry.isIntersecting) {{
          const id = entry.target.id;
          chapterLinks.forEach((link) => {{
            link.classList.toggle('active', link.getAttribute('href') === '#' + id);
          }});
        }}
      }});
    }}, {{ rootMargin: '-20% 0px -70% 0px', threshold: 0 }});
    chapters.forEach((el) => observer.observe(el));
  }}
}})();
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
