# Publisher QA Checklist

Use this checklist before tagging a public release.

## Source QA

- Run `python3 scripts/qa_book.py`.
- Confirm there are no malformed ASCII diagrams, legacy manual panels, or stale removed-section references.
- Confirm every book image has useful alt text and a valid local asset.
- Confirm README, front matter, and release notes describe the current book structure.

## Editorial QA

- Check chapter structure: Hook, Pivot, Investigation, Manual Page.
- Normalize recurring section names across chapters.
- Remove duplicated explanation and AI-draft artifacts.
- Verify that every Manual Page reads as a framework, not professional advice.

## Citation and Fact QA

- Build a chapter-level source map for historical claims, statistics, laws, treaties, and technical claims.
- Prefer primary sources for law, public health, energy, fiscal, and diplomatic assertions.
- Add footnotes/endnotes where a reader would reasonably ask "according to whom?"
- Record unresolved source questions in GitHub issues before release.
- Tracking issue: <https://github.com/Algiras/Statecraft/issues/1>

## Artifact QA

- Run `quarto render --to html`.
- Run `python3 merge_chapters.py`.
- Run `bash compile_pdf.sh`.
- Run `bash compile_epub.sh`.
- Open the PDF and inspect title page, TOC, image placement, tables, page breaks, and figure captions.
- Open the EPUB in at least one reader and inspect cover, TOC, images, math, tables, and footnotes.
- Tracking issue: <https://github.com/Algiras/Statecraft/issues/3>

## Web QA

- Check desktop, tablet, and mobile layouts.
- Check homepage cover/title alignment.
- Check sidebar navigation, search, theme toggle, and download links.
- Check social preview metadata after deployment.
- Check `llms.txt` and `llms-full.txt` are published at the site root and link to the current edition.
- Check `robots.txt` is published at the site root and points to `https://algiras.github.io/Statecraft/sitemap.xml`.
- Check Quarto generated `sitemap.xml` includes all book HTML pages.
- Check LinkedIn, GitHub, portfolio, support, and corrections links.
- Tracking issues: <https://github.com/Algiras/Statecraft/issues/2> and <https://github.com/Algiras/Statecraft/issues/4>

## Release QA

- Confirm `ERRATA.md` is current.
- Confirm support/corrections links work.
- Tag the release only after HTML, PDF, EPUB, and Markdown artifacts are current.
- Confirm ISBN, imprint, and release-policy decisions are current: <https://github.com/Algiras/Statecraft/issues/5>
