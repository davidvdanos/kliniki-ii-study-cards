from __future__ import annotations

import html
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from docx import Document
from docx.document import Document as DocxDocument
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "study-cards-app"
NOTES_DIR = APP / "notes"
DOWNLOADS_DIR = APP / "downloads"


@dataclass(frozen=True)
class NotePage:
    slug: str
    short: str
    title: str
    source: Path


PAGES = [
    NotePage(
        "sos-development",
        "SOS",
        "SOS Ανάπτυξης",
        ROOT / "study-notes/sos-development-final/Σημειώσεις_SOS_Ανάπτυξης_Κλινική_ΙΙ.docx",
    ),
    NotePage(
        "psychodynamic-maturity-self",
        "Ωριμότητα",
        "Ψυχική Ωριμότητα, Εαυτός και Ναρκισσισμός",
        ROOT / "study-notes/psychodynamic-maturity-self/Σημειώσεις_Ψυχική_Ωριμότητα_Εαυτός_Ναρκισσισμός_Κεφ_4_5.docx",
    ),
    NotePage(
        "diagnosis-clinical-assessment",
        "Διάγνωση",
        "Διάγνωση και Κλινική Εκτίμηση",
        ROOT / "study-notes/diagnosis-chapter-2/Σημειώσεις_Διάγνωση_Κλινική_Εκτίμηση_Κεφ_2.docx",
    ),
    NotePage(
        "mental-status-examination",
        "MSE",
        "Mental Status Examination",
        ROOT / "study-notes/mental-status-examination/Σημειώσεις_Κλινική_Εκτίμηση_Mental_Status_Examination.docx",
    ),
    NotePage(
        "attachment-theory",
        "Δεσμός",
        "Θεωρία Δεσμού και Ψυχικοποίηση",
        ROOT / "study-notes/attachment-theory/Σημειώσεις_Θεωρία_Δεσμού_Κεφ_6.docx",
    ),
    NotePage(
        "cluster-a",
        "Cluster A",
        "Ομάδα Α Διαταραχών Προσωπικότητας",
        ROOT / "study-notes/cluster-a/Σημειώσεις_Ομάδα_Α_Διαταραχές_Προσωπικότητας.docx",
    ),
    NotePage(
        "cluster-b",
        "Cluster B",
        "Ομάδα Β Διαταραχών Προσωπικότητας",
        ROOT / "study-notes/cluster-b/Σημειώσεις_Ομάδα_Β_Διαταραχές_Προσωπικότητας.docx",
    ),
    NotePage(
        "cluster-c",
        "Cluster C",
        "Ομάδα Γ Διαταραχών Προσωπικότητας",
        ROOT / "study-notes/cluster-c/Σημειώσεις_Ομάδα_Γ_Διαταραχές_Προσωπικότητας_justified.docx",
    ),
    NotePage(
        "anxiety-ptsd",
        "Άγχος/PTSD",
        "Νευρώσεις, Αγχώδεις Διαταραχές και PTSD",
        ROOT / "study-notes/anxiety-neuroses/Σημειώσεις_Νευρώσεις_Αγχώδεις_Διαταραχές_Κεφ_14.docx",
    ),
    NotePage(
        "mood-disorders",
        "Διάθεση",
        "Διαταραχές Διάθεσης",
        ROOT / "study-notes/mood-disorders/Σημειώσεις_Διαταραχές_Διάθεσης_Κεφ_15.docx",
    ),
    NotePage(
        "psychotic-disorders",
        "Ψύχωση",
        "Ψυχωτικές Διαταραχές",
        ROOT / "study-notes/psychotic-disorders/Σημειώσεις_Ψυχωτικές_Διαταραχές_Κεφ_17_18.docx",
    ),
    NotePage(
        "eating-disorders",
        "Τροφή",
        "Διαταραχές Πρόσληψης Τροφής",
        ROOT / "study-notes/eating-disorders/Σημειώσεις_Διαταραχές_Πρόσληψης_Τροφής_Κεφ_20.docx",
    ),
]


def iter_blocks(document: DocxDocument):
    body = document.element.body
    for child in body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, document)
        elif isinstance(child, CT_Tbl):
            yield Table(child, document)


def slugify(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", "-", text.strip().lower())
    text = re.sub(r"[^0-9a-zA-Z\u0370-\u03ff-]+", "", text)
    return text.strip("-") or "section"


def run_to_html(run) -> str:
    text = html.escape(run.text).replace("\n", "<br>")
    if not text:
        return ""

    styles = []
    if run.font.color and run.font.color.rgb:
        styles.append(f"color: #{run.font.color.rgb}")
    if run.font.highlight_color:
        text = f"<mark>{text}</mark>"
    if styles:
        text = f"<span style=\"{' ; '.join(styles)}\">{text}</span>"
    if run.bold:
        text = f"<strong>{text}</strong>"
    if run.italic:
        text = f"<em>{text}</em>"
    if run.underline:
        text = f"<u>{text}</u>"
    return text


def paragraph_inner_html(paragraph: Paragraph) -> str:
    pieces = [run_to_html(run) for run in paragraph.runs]
    joined = "".join(pieces).strip()
    return joined or html.escape(paragraph.text.strip())


def blockquote_kind(text: str) -> str | None:
    stripped = re.sub(r"<[^>]+>", "", text).strip().lower()
    if stripped.startswith(("sos", "προσοχη", "πρόσεξε", "σημειωση", "σημείωση", "εξεταστικ")):
        return "note-callout"
    return None


def heading_level(paragraph: Paragraph) -> int | None:
    style = (paragraph.style.name or "").lower()
    if "title" in style:
        return 2
    if "heading 1" in style:
        return 2
    if "heading 2" in style:
        return 3
    if "heading 3" in style:
        return 4
    return None


def table_to_html(table: Table) -> str:
    rows = []
    for row_index, row in enumerate(table.rows):
        cells = []
        tag = "th" if row_index == 0 else "td"
        for cell in row.cells:
            text_parts = []
            for paragraph in cell.paragraphs:
                value = paragraph_inner_html(paragraph)
                if value:
                    text_parts.append(value)
            cells.append(f"<{tag}>{'<br>'.join(text_parts)}</{tag}>")
        rows.append(f"<tr>{''.join(cells)}</tr>")
    return f"<div class=\"table-wrap\"><table>{''.join(rows)}</table></div>"


def docx_to_html(path: Path) -> tuple[str, list[tuple[int, str, str]]]:
    document = Document(str(path))
    parts: list[str] = []
    toc: list[tuple[int, str, str]] = []
    open_list = False
    used_ids: dict[str, int] = {}

    def close_list() -> None:
        nonlocal open_list
        if open_list:
            parts.append("</ul>")
            open_list = False

    for block in iter_blocks(document):
        if isinstance(block, Table):
            close_list()
            parts.append(table_to_html(block))
            continue

        text = paragraph_inner_html(block)
        plain = block.text.strip()
        if not plain:
            close_list()
            continue

        level = heading_level(block)
        if level:
            close_list()
            base_id = slugify(plain)
            count = used_ids.get(base_id, 0)
            used_ids[base_id] = count + 1
            item_id = base_id if count == 0 else f"{base_id}-{count + 1}"
            toc.append((level, plain, item_id))
            parts.append(f"<h{level} id=\"{item_id}\">{text}</h{level}>")
            continue

        style = (block.style.name or "").lower()
        is_list = "list" in style or plain.startswith(("- ", "• "))
        if is_list:
            if not open_list:
                parts.append("<ul>")
                open_list = True
            item = re.sub(r"^[-•]\s*", "", text)
            parts.append(f"<li>{item}</li>")
            continue

        close_list()
        callout = blockquote_kind(text)
        if callout:
            parts.append(f"<p class=\"{callout}\">{text}</p>")
        else:
            parts.append(f"<p>{text}</p>")

    close_list()
    return "\n".join(parts), toc


def nav_html(active_slug: str | None, prefix: str = "") -> str:
    links = [f"<a class=\"nav-tab {'active' if active_slug is None else ''}\" href=\"{prefix}index.html\">Κάρτες</a>"]
    for page in PAGES:
        active = "active" if page.slug == active_slug else ""
        links.append(f"<a class=\"nav-tab {active}\" href=\"{prefix}notes/{page.slug}.html\">{html.escape(page.short)}</a>")
    links.append(f"<a class=\"nav-tab\" href=\"{prefix}exam/development.html\">Ανάπτυξης</a>")
    links.append(f"<a class=\"nav-tab\" href=\"{prefix}exam/multiple-choice.html\">Quiz Πολλαπλής</a>")
    return (
        "<nav class=\"site-tabs\" aria-label=\"Κύρια πλοήγηση\">"
        "<div class=\"site-tabs-inner\">"
        + "".join(links)
        + "</div></nav>"
    )


def page_template(page: NotePage, body: str, toc: list[tuple[int, str, str]]) -> str:
    toc_items = "\n".join(
        f"<a class=\"toc-level-{level}\" href=\"#{item_id}\">{html.escape(title)}</a>"
        for level, title, item_id in toc[:40]
    )
    download_name = page.source.name
    return f"""<!doctype html>
<html lang="el">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{html.escape(page.title)} | Κλινική Ψυχολογία ΙΙ</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Sans+Greek:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
    <link rel="stylesheet" href="../styles.css" />
  </head>
  <body class="notes-page">
    {nav_html(page.slug, "../")}
    <main class="notes-shell">
      <aside class="notes-toc" aria-label="Περιεχόμενα σελίδας">
        <p>Περιεχόμενα</p>
        {toc_items}
      </aside>
      <article class="notes-article">
        <header class="notes-hero">
          <p class="course-label">Κλινική Ψυχολογία ΙΙ</p>
          <h1>{html.escape(page.title)}</h1>
          <a class="word-download" href="../downloads/{html.escape(download_name)}">Άνοιγμα Word</a>
        </header>
        <div class="notes-content">
          {body}
        </div>
      </article>
    </main>
  </body>
</html>
"""


def build() -> None:
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

    for page in PAGES:
        if not page.source.exists():
            raise FileNotFoundError(page.source)
        body, toc = docx_to_html(page.source)
        (NOTES_DIR / f"{page.slug}.html").write_text(page_template(page, body, toc), encoding="utf-8")
        shutil.copy2(page.source, DOWNLOADS_DIR / page.source.name)

    print(f"Built {len(PAGES)} note pages in {NOTES_DIR}")


if __name__ == "__main__":
    build()
