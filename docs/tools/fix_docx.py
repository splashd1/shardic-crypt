"""
Post-process a pandoc-generated docx (built with an existing docx as
--reference-doc) to fix two known issues:

1. Dangling Word style references: pandoc emits w:pStyle/w:rStyle/w:tblStyle
   values (Compact, FirstParagraph, Table, VerbatimChar) that aren't defined
   in the reference doc's styles.xml, which silently corrupts affected
   paragraphs/tables in Word. Remap them to styles that actually exist.
2. Orphaned duplicate media: using a docx as its own --reference-doc makes
   pandoc carry forward that doc's existing embedded images under their old
   relationship IDs *in addition to* freshly generating a second copy under
   new IDs. Strip the old, now-unreferenced copies.
3. Rel-less media parts: some reference docs (carried forward across
   several generations of bug #2, before this fix existed) already contain
   word/media/* zip parts with no Relationship entry pointing at them at
   all -- invisible to the rels-based cleanup in #2, which only strips
   entries that exist in the rels file but aren't referenced. Strip any
   media part whose filename never appears as a Target in the *cleaned*
   rels file, regardless of whether it ever had a rels entry.

Usage: fix_docx.py <in.docx> <out.docx>
"""
import re
import shutil
import sys
import zipfile

STYLE_REMAP = {
    "Compact": "Normal",
    "FirstParagraph": "Normal",
    "Table": "TableGrid",
    "VerbatimChar": "DefaultParagraphFont",
}


def fix_dangling_styles(document_xml: bytes, defined_style_ids: set[str]) -> bytes:
    text = document_xml.decode("utf-8")
    remapped = []

    def repl(m):
        tag, val = m.group(1), m.group(2)
        if val in defined_style_ids:
            return m.group(0)
        new_val = STYLE_REMAP.get(val)
        if new_val is None:
            return m.group(0)
        remapped.append((tag, val, new_val))
        return f'<w:{tag} w:val="{new_val}"/>'

    text, n = re.subn(r'<w:(pStyle|rStyle|tblStyle) w:val="([^"]+)"\s*/>', repl, text)
    print(f"scanned {n} pStyle/rStyle/tblStyle references, remapped {len(remapped)}: {sorted(set(remapped))}")
    return text.encode("utf-8")


def get_defined_style_ids(styles_xml: bytes) -> set[str]:
    text = styles_xml.decode("utf-8")
    return set(re.findall(r'<w:style [^>]*w:styleId="([^"]+)"', text))


def strip_orphaned_media(zin: zipfile.ZipFile, document_xml: bytes, rels_xml: bytes):
    doc_text = document_xml.decode("utf-8")
    referenced_rids = set(re.findall(r'r:embed="(rId\d+)"', doc_text))

    rels_text = rels_xml.decode("utf-8")
    all_media_rels = {}
    rel_spans = []
    for m in re.finditer(r"<Relationship\b[^>]*/>", rels_text):
        block = m.group(0)
        id_m = re.search(r'Id="(rId\d+)"', block)
        target_m = re.search(r'Target="(media/[^"]+)"', block)
        if id_m and target_m:
            all_media_rels[id_m.group(1)] = target_m.group(1)
            rel_spans.append((id_m.group(1), block))

    orphaned_rids = set(all_media_rels) - referenced_rids
    orphaned_targets = {all_media_rels[r] for r in orphaned_rids}

    new_rels_text = rels_text
    for rid, block in rel_spans:
        if rid in orphaned_rids:
            new_rels_text = new_rels_text.replace(block, "")

    return new_rels_text.encode("utf-8"), orphaned_targets


def strip_relless_media(zin: zipfile.ZipFile, cleaned_rels_xml: bytes, orphaned_targets: set[str]):
    """Media parts with no Relationship entry at all, in any rels file the
    package carries (invisible to strip_orphaned_media, which only sees
    entries declared in word/_rels/document.xml.rels)."""
    all_media_parts = {n for n in zin.namelist() if n.startswith("word/media/")}
    still_targeted = {f"word/{t}" for t in re.findall(r'Target="(media/[^"]+)"', cleaned_rels_xml.decode("utf-8"))}
    for name in zin.namelist():
        if name.endswith(".xml.rels") and name != "word/_rels/document.xml.rels":
            text = zin.read(name).decode("utf-8")
            still_targeted |= {f"word/{t}" for t in re.findall(r'Target="(media/[^"]+)"', text)}
    already_removed = {f"word/{t}" for t in orphaned_targets}
    return (all_media_parts - still_targeted) - already_removed


def main():
    in_path, out_path = sys.argv[1], sys.argv[2]
    shutil.copy(in_path, out_path)

    with zipfile.ZipFile(in_path) as zin:
        document_xml = zin.read("word/document.xml")
        styles_xml = zin.read("word/styles.xml")
        rels_xml = zin.read("word/_rels/document.xml.rels")
        names = zin.namelist()

    defined_ids = get_defined_style_ids(styles_xml)
    fixed_document_xml = fix_dangling_styles(document_xml, defined_ids)

    new_rels_xml, orphaned_targets = strip_orphaned_media(
        zipfile.ZipFile(in_path), fixed_document_xml, rels_xml
    )
    orphaned_parts = {f"word/{t}" for t in orphaned_targets}
    relless_parts = strip_relless_media(zipfile.ZipFile(in_path), new_rels_xml, orphaned_targets)
    orphaned_parts |= relless_parts

    with zipfile.ZipFile(in_path) as zin, zipfile.ZipFile(
        out_path, "w", zipfile.ZIP_DEFLATED
    ) as zout:
        for item in zin.infolist():
            if item.filename in orphaned_parts:
                continue
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                data = fixed_document_xml
            elif item.filename == "word/_rels/document.xml.rels":
                data = new_rels_xml
            zout.writestr(item, data)

    print(f"remapped styles against {len(defined_ids)} defined style ids")
    print(f"stripped {len(orphaned_parts)} orphaned media part(s): {sorted(orphaned_parts)}")


if __name__ == "__main__":
    main()
