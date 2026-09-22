---
name: shardic-doc-pipeline
description: Low-friction regeneration and revision of shardic's docx/html/pptx artifacts (whitepaper trio, standalone reference docs, the slide deck) from their markdown/pptx sources. Invoke whenever asked to regenerate a doc's docx/html twins, add or edit a whitepaper section and its rendered forms, or update the slide deck to reflect new whitepaper content. Covers the two known pandoc-regen bugs (dangling Word styles, orphaned duplicate media) and the pptx XML-surgery workflow for adding/editing slides by hand.
---

# shardic-doc-pipeline

This project keeps several docs in three parallel forms (`.md` source,
`.docx`, `.html`) plus a slide deck (`.pptx`) that should track the
whitepaper's content. Regenerating these by hand has hit the same two
bugs enough times across sessions that they're now fixed by a script
instead of re-discovered each time. Use this skill instead of
re-deriving the pipeline from scratch.

## Which pipeline applies

- **A standalone doc with no docx/html yet, or a plain one-way
  conversion** (e.g. `docs/shardic-cryptographic-path.md`): use the
  **plain pandoc pipeline** below. No reference-doc, no post-processing
  needed.
- **The whitepaper trio** (`docs/shardic_white_paper.v2.X.md` /
  `SHARDIC_White_Paper_v2.X_with_figures.docx` /
  `shardic_white_paperXX.html`): use the **reference-doc pipeline**
  below — it preserves the existing docx's styles/template but hits
  two known bugs that `docs/tools/fix_docx.py` exists to fix.
- **The slide deck** (`docs/shardic_deck_v2_2.pptx`): use the **pptx
  XML-surgery workflow** further down — there is no markdown source for
  this file; edits are made directly against the OOXML.

## Plain pandoc pipeline (no existing docx/html)

Run from `docs/` so relative `./media/...` image paths resolve:

```
cd docs
pandoc <name>.md -o <name>.docx
pandoc <name>.md -o <name>.html --standalone --metadata title="<Title>"
```

Verify before calling it done:
```
soffice --headless --convert-to pdf <name>.docx --outdir /tmp/...
pdfinfo <name>.pdf | grep Pages   # sanity page count
```

## Reference-doc pipeline (whitepaper trio, or any doc with an
established docx template to preserve)

Using the *existing* docx as `--reference-doc` keeps its styles/template
consistent release to release, but triggers two bugs every time:

1. **Dangling Word styles.** Pandoc emits `w:pStyle`/`w:rStyle`/
   `w:tblStyle` values (`Compact`, `FirstParagraph`, `Table`,
   `VerbatimChar`) that the reference doc's `styles.xml` doesn't define.
   Word/LibreOffice silently falls back to no formatting at all for the
   affected paragraphs/tables — a table renders as flattened, borderless
   paragraph text, not an error, so it's easy to ship without noticing.
2. **Orphaned duplicate media.** Because the reference-doc *is* the
   previous output, pandoc carries its embedded images forward under
   their old relationship IDs *in addition to* generating a fresh copy
   under new IDs — every image ends up embedded twice, silently
   doubling the file size, with half the copies unreferenced.

Both are fixed by `docs/tools/fix_docx.py`:

```
cd docs
pandoc shardic_white_paper.v2.X.md -o /tmp/raw.docx \
  --reference-doc=SHARDIC_White_Paper_v2.X_with_figures.docx
python3 tools/fix_docx.py /tmp/raw.docx SHARDIC_White_Paper_v2.X_with_figures.docx
pandoc shardic_white_paper.v2.X.md -o shardic_white_paperXX.html \
  --standalone --metadata title="shardic_white_paper.v2.X"
```

`fix_docx.py` prints what it did — a remap count and list of remapped
`(tag, old, new)` tuples, and which media parts it stripped. **A remap
count of 0 on a doc that has tables is a red flag**, not a clean run —
it means the regex didn't match anything (check for the whitespace
variant `w:val="X" />` vs `w:val="X"/>`) and the corruption bug is still
present unfixed. Always verify by rendering:

```
soffice --headless --convert-to pdf SHARDIC_White_Paper_v2.X_with_figures.docx --outdir /tmp/...
pdftotext -layout /tmp/....pdf - | grep -n "<a known table header text>"
pdftoppm -png -r 100 -f <page> -l <page> /tmp/....pdf /tmp/check
```
Then look at the rendered page: a real table has visible cell borders
and columns; a corrupted one shows every cell's text as a flat vertical
list of one-line paragraphs. If you can't tell from `pdftotext`, render
to PNG and look — don't assume the fix worked just because the script
didn't error.

Also worth a table-count sanity check via `python-docx` (install into a
throwaway venv if not present system-wide — this machine is
externally-managed):
```
python3 -m venv /tmp/docxenv && /tmp/docxenv/bin/pip install -q python-docx
/tmp/docxenv/bin/python -c "
import docx
d = docx.Document('SHARDIC_White_Paper_v2.X_with_figures.docx')
print(len(d.tables), 'tables')
"
```
Compare against the table count from the previous known-good regen
(check git history / prior session notes) — a big drop usually means
something silently failed to convert.

## pptx XML-surgery workflow (the slide deck)

There is no markdown source for `docs/shardic_deck_v2_2.pptx` — edits
are made directly against the pptx's internal OOXML. This has been done
successfully several times (adding a new slide, removing bullets and
reflowing a grid); the pattern below is what worked.

### 1. Extract and inspect

```
mkdir -p /tmp/deck_audit/extracted
unzip -q -o docs/shardic_deck_v2_2.pptx -d /tmp/deck_audit/extracted
```

Slide **display order** is governed by `ppt/presentation.xml`'s
`<p:sldIdLst>` (an ordered list of `<p:sldId id="..." r:id="rIdN"/>`)
crossed with `ppt/_rels/presentation.xml.rels` (which maps `rIdN` to a
`slides/slideM.xml` filename) — **never assume slide N is `slideN.xml`**;
parts get added out of numeric order as the deck evolves and the
mapping has to be resolved explicitly every time. Build the map with a
small script rather than eyeballing it.

To read all slide text in display order (needs `python-pptx`; install
into a throwaway venv, same externally-managed-machine caveat as
above): a `Presentation(path).slides` iterator already walks slides in
the correct display order without needing to resolve the mapping
yourself — use that for *reading*. You only need the raw
sldIdLst/rels mapping when *writing* (inserting a new slide at a
specific position, see below).

### 2. Match the existing visual system

Before adding new shapes, find the slide(s) whose layout is closest to
what you need and pretty-print their XML (`xml.dom.minidom.toprettyxml`)
to read off exact colors, offsets, and sizes — don't guess geometry.
This deck's recurring patterns, worth knowing before searching:
- **Two-card side-by-side comparison** (e.g. the §4.7 slide): navy
  `24316E` rounded-rect cards, an icon circle (`263874` blue or
  `3A2F14` warm-brown) with a white icon PNG on top, title + body text
  boxes, a full-width `263874` callout rect below.
- **2×2 (or larger) card grid** (e.g. the §7.3 limitations slide):
  same card/icon/title/body shapes, tiled with a fixed column/row
  offset delta — reuse those exact deltas for a new grid rather than
  re-deriving spacing.
- Page background is a **per-slide `<p:bg>` override**, not a shape —
  easy to miss if only skimming the shape tree.
- Footer page numbers are plain text shapes with a bare `<a:t>NN</a:t>`
  — find them with a regex on the *slide's* XML, not the deck's, since
  each slide carries its own.

Build an icon contact sheet before picking icons — the deck reuses a
shared ~29-icon PNG set in `ppt/media/`, most icons have no filename
hint about their meaning:
```python
from PIL import Image, ImageDraw
# tile ppt/media/*.png onto a labeled grid, dark background matching
# the icons' own transparent-PNG-on-navy convention, save as PNG, then
# view it directly (image files can be read as images).
```

### 3. Write the new/edited slide XML

Generate the new slide's XML with a small Python script (string
templating with exact EMU offsets), not hand-edited XML — it keeps the
many repeated shape blocks (card rect, icon circle, icon pic, title,
body) consistent and makes it trivial to loop over N cards. Validate
with `xml.dom.minidom.parse` before wiring it in.

### 4. Wire a new slide into the deck

Four edits, in this order, each idempotent-checked before applying
(assert the target string exists / the new one doesn't, so a re-run
doesn't double-apply):

1. Copy `slideN.xml` (+ its `_rels/slideN.xml.rels`, referencing the
   layout and any icon images it uses) into
   `extracted/ppt/slides/`.
2. Add an `<Override PartName="/ppt/slides/slideN.xml" ContentType=".../slide+xml"/>`
   to `[Content_Types].xml`, right after the slide it's most related
   to.
3. Add a new `<Relationship Id="rIdM" .../>` to
   `ppt/_rels/presentation.xml.rels` pointing at `slides/slideN.xml`.
4. Insert a new `<p:sldId id="..." r:id="rIdM"/>` into
   `ppt/presentation.xml`'s `<p:sldIdLst>` at the position you want it
   to display — position in this list is what actually controls
   display order, independent of the slide's filename or id number.

Then **renumber every subsequent slide's footer page number by the
number of slides you inserted** — find each shifted slide's bare
`<a:t>NN</a:t>` footer text and bump it. Check the deck's actual closing
slide first: it may use a different, non-numeric footer style (this
deck's does) that needs no change.

### 5. Repackage and verify

```
cd extracted && zip -q -r -X ../new_deck.pptx . -x '.*' && cd ..
```
(`-X` strips extra file attributes; excluding dotfiles avoids
accidentally zipping stray editor artifacts.)

Verify, in this order — each catches a different failure mode:
1. `python-pptx` open + `len(prs.slides)` — catches structural breakage
   (bad XML, broken rels) immediately, cheaply.
2. `soffice --headless --convert-to pdf` — catches anything
   `python-pptx` can parse but that doesn't actually render (bad
   geometry, missing image parts).
3. `pdftoppm` the new/changed slides (and a couple of neighbors either
   side, to confirm the shift/renumbering landed right) to PNG and look
   at them directly — layout bugs (overlap, off-slide shapes, wrong
   spacing) are easy to miss from XML alone and easy to spot visually.

Only copy `new_deck.pptx` over the tracked file once all three pass.

## What NOT to do

- Don't hand-edit XML strings with `sed`/manual string surgery for
  anything beyond a single-value swap (like a footer number) — use a
  script for anything structural, so it can be re-run and diffed.
- Don't skip the visual render-and-look step because the XML parses or
  `python-pptx` opens it — both known bugs this skill exists for
  (dangling styles, pptx layout mistakes) are silent at that level and
  only visible in the rendered output.
- Don't reuse a docx as its own `--reference-doc` without running
  `fix_docx.py` afterward — the orphaned-media doubling happens every
  time, not just occasionally.
- Don't assume a slide's filename tells you its display position —
  always resolve it through `sldIdLst` + the rels mapping.
