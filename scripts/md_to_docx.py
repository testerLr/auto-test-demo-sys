"""把 docs/api.md 转成排版好的 Word 文档。

用法：
    uv run --with python-docx python scripts/md_to_docx.py

输出：docs/Auto-Test-Demo-System-API.docx
"""

import re
import sys
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT_ROOT / "docs" / "api.md"
OUTPUT = PROJECT_ROOT / "docs" / "Auto-Test-Demo-System-API.docx"

FONT_CN = "微软雅黑"
FONT_CODE = "Consolas"

INLINE_RE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))")
HEADING_RE = re.compile(r"^(#{1,4})\s+(.*)$")
BULLET_RE = re.compile(r"^\s*[-*]\s+(.*)$")
ORDERED_RE = re.compile(r"^\s*\d+\.\s+(.*)$")


# ---------- Markdown 解析 ----------


def split_table_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    cells = re.split(r"(?<!\\)\|", line)
    return [cell.strip().replace("\\|", "|") for cell in cells]


def is_separator_row(line: str) -> bool:
    if "-" not in line:
        return False
    cells = split_table_row(line)
    return all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def parse_blocks(text: str) -> list[tuple]:
    lines = text.splitlines()
    blocks: list[tuple] = []
    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith("```"):
            i += 1
            code: list[str] = []
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            blocks.append(("code", "\n".join(code)))
            continue

        if line.strip().startswith("|"):
            rows: list[list[str]] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                if not is_separator_row(lines[i]):
                    rows.append(split_table_row(lines[i]))
                i += 1
            if rows:
                blocks.append(("table", rows))
            continue

        heading = HEADING_RE.match(line)
        if heading:
            blocks.append(("heading", len(heading.group(1)), heading.group(2).strip()))
            i += 1
            continue

        if line.strip() == "---":
            blocks.append(("hr",))
            i += 1
            continue

        bullet = BULLET_RE.match(line)
        if bullet:
            items = []
            while i < len(lines):
                match = BULLET_RE.match(lines[i])
                if not match:
                    break
                items.append(match.group(1).strip())
                i += 1
            blocks.append(("bullets", items))
            continue

        ordered = ORDERED_RE.match(line)
        if ordered:
            items = []
            while i < len(lines):
                match = ORDERED_RE.match(lines[i])
                if not match:
                    break
                items.append(match.group(1).strip())
                i += 1
            blocks.append(("ordered", items))
            continue

        if line.strip().startswith(">"):
            quote: list[str] = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip().lstrip(">").strip())
                i += 1
            blocks.append(("quote", " ".join(quote)))
            continue

        if not line.strip():
            i += 1
            continue

        paragraph: list[str] = []
        while i < len(lines):
            current = lines[i]
            if (
                not current.strip()
                or current.startswith("```")
                or current.strip().startswith("|")
                or HEADING_RE.match(current)
                or BULLET_RE.match(current)
                or ORDERED_RE.match(current)
                or current.strip().startswith(">")
                or current.strip() == "---"
            ):
                break
            paragraph.append(current.strip())
            i += 1
        if not paragraph:
            # 兜底：无法识别的行直接跳过，避免死循环
            i += 1
            continue
        blocks.append(("para", "".join(paragraph)))

    return blocks


# ---------- 文档构建 ----------


def set_east_asian_font(style, font_name: str) -> None:
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), font_name)
    rfonts.set(qn("w:ascii"), font_name)
    rfonts.set(qn("w:hAnsi"), font_name)


def add_inline(paragraph, text: str, bold: bool = False, size: Pt | None = None) -> None:
    for part in INLINE_RE.split(text):
        if not part:
            continue
        run = paragraph.add_run()
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            run.text = part[2:-2]
            run.bold = True
        elif part.startswith("`") and part.endswith("`") and len(part) > 2:
            run.text = part[1:-1]
            run.font.name = FONT_CODE
            run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_CODE)
            run.font.size = Pt(9)
            run.font.color.rgb = RGBColor(0xC7, 0x25, 0x4E)
        elif part.startswith("[") and "](" in part and part.endswith(")"):
            label, url = re.match(r"\[([^\]]+)\]\(([^)]+)\)", part).groups()
            is_code = label.startswith("`") and label.endswith("`")
            run.text = label.strip("`")
            if is_code:
                run.font.name = FONT_CODE
                run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_CODE)
                run.font.size = Pt(9)
            run.font.color.rgb = RGBColor(0x1F, 0x4E, 0x9A)
            run.underline = True
            tail = paragraph.add_run(f" ({url})")
            tail.font.size = Pt(8.5)
            tail.font.color.rgb = RGBColor(0x80, 0x80, 0x80)
            continue
        else:
            run.text = part
        if bold:
            run.bold = True
        if size is not None:
            run.font.size = size


def shade_cell(cell, color: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    tc_pr.append(shd)


def shade_paragraph(paragraph, color: str) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    p_pr.append(shd)


def repeat_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    header = OxmlElement("w:tblHeader")
    header.set(qn("w:val"), "true")
    tr_pr.append(header)


def add_table(doc: Document, rows: list[list[str]]) -> None:
    cols = max(len(row) for row in rows)
    table = doc.add_table(rows=len(rows), cols=cols)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True

    for row_index, row in enumerate(rows):
        for col_index in range(cols):
            cell = table.cell(row_index, col_index)
            cell.text = ""
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_before = Pt(2)
            paragraph.paragraph_format.space_after = Pt(2)
            value = row[col_index] if col_index < len(row) else ""
            add_inline(paragraph, value, bold=row_index == 0, size=Pt(9))
            if row_index == 0:
                shade_cell(cell, "D9E2F3")
        if row_index == 0:
            repeat_header(table.rows[0])

    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def add_code_block(doc: Document, code: str) -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.left_indent = Cm(0.3)
    paragraph.paragraph_format.space_before = Pt(4)
    paragraph.paragraph_format.space_after = Pt(6)
    shade_paragraph(paragraph, "F4F4F4")
    lines = code.splitlines() or [""]
    for index, line in enumerate(lines):
        run = paragraph.add_run(line)
        run.font.name = FONT_CODE
        run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_CODE)
        run.font.size = Pt(8.5)
        if index < len(lines) - 1:
            run.add_break()


def add_quote(doc: Document, text: str) -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.left_indent = Cm(0.5)
    paragraph.paragraph_format.space_before = Pt(2)
    paragraph.paragraph_format.space_after = Pt(4)
    shade_paragraph(paragraph, "F2F2F2")
    add_inline(paragraph, text, size=Pt(9.5))
    for run in paragraph.runs:
        run.font.color.rgb = RGBColor(0x59, 0x59, 0x59)


def add_hr(doc: Document) -> None:
    paragraph = doc.add_paragraph()
    p_pr = paragraph._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "BFBFBF")
    borders.append(bottom)
    p_pr.append(borders)


def add_field(paragraph, instruction: str, placeholder: str) -> None:
    """插入 Word 域；各节点放在独立 run 中，兼容性最好。"""
    parts: list[tuple[str, str | None]] = [
        ("begin", None),
        ("instr", instruction),
        ("separate", None),
        ("text", placeholder),
        ("end", None),
    ]
    for kind, value in parts:
        run = paragraph.add_run()
        if kind == "instr":
            element = OxmlElement("w:instrText")
            element.set(qn("xml:space"), "preserve")
            element.text = value
        elif kind == "text":
            element = OxmlElement("w:t")
            element.text = value
        else:
            element = OxmlElement("w:fldChar")
            element.set(qn("w:fldCharType"), kind)
        run._r.append(element)


def setup_document() -> Document:
    doc = Document()

    normal = doc.styles["Normal"]
    normal.font.name = FONT_CN
    normal.font.size = Pt(10.5)
    set_east_asian_font(normal, FONT_CN)
    normal.paragraph_format.line_spacing = 1.25
    normal.paragraph_format.space_after = Pt(4)

    for name, size in (("Heading 1", 16), ("Heading 2", 13), ("Heading 3", 11.5)):
        style = doc.styles[name]
        style.font.name = FONT_CN
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)
        style.font.bold = True
        set_east_asian_font(style, FONT_CN)
        style.paragraph_format.space_before = Pt(12)
        style.paragraph_format.space_after = Pt(6)

    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(2.2)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)
    section.different_first_page_header_footer = True

    header = section.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    header.text = "Auto Test Demo System · 接口文档"
    header.runs[0].font.size = Pt(8.5)
    header.runs[0].font.color.rgb = RGBColor(0x80, 0x80, 0x80)

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_field(footer, "PAGE", "1")
    footer.runs[0].font.size = Pt(9)
    return doc


def render(doc: Document, blocks: list[tuple]) -> None:
    title = "接口文档"
    title_index = next(
        (i for i, block in enumerate(blocks) if block[0] == "heading" and block[1] == 1),
        None,
    )
    if title_index is not None:
        title = blocks[title_index][2]

    # 封面：标题 + 元信息表
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(140)
    run = paragraph.add_run(title)
    run.font.size = Pt(30)
    run.bold = True
    run.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)
    run.font.name = FONT_CN
    run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_CN)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub_run = subtitle.add_run(
        f"Auto Test Demo System · v1.0.0 · {date.today().isoformat()}"
    )
    sub_run.font.size = Pt(11)
    sub_run.font.color.rgb = RGBColor(0x59, 0x59, 0x59)

    if title_index is not None:
        for block in blocks[title_index + 1 :]:
            if block[0] == "heading" and block[1] <= 2:
                break
            if block[0] == "table":
                add_table(doc, block[1])
            elif block[0] == "para":
                para = doc.add_paragraph()
                para.alignment = WD_ALIGN_PARAGRAPH.LEFT
                add_inline(para, block[1])

    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    # 目录
    toc_title = doc.add_paragraph()
    toc_run = toc_title.add_run("目录")
    toc_run.font.size = Pt(18)
    toc_run.bold = True
    toc_run.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)

    toc = doc.add_paragraph()
    add_field(toc, 'TOC \\o "1-3" \\h \\z \\u', "在 Word 中右键此处，选择「更新域」生成目录")
    hint = doc.add_paragraph()
    hint_run = hint.add_run("提示：目录为 Word 域，打开文档后右键目录并选择「更新域」即可生成页码。")
    hint_run.font.size = Pt(9)
    hint_run.font.color.rgb = RGBColor(0x80, 0x80, 0x80)

    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    # 正文
    body_start = 0
    if title_index is not None:
        for index, block in enumerate(blocks):
            if index > title_index and block[0] == "heading" and block[1] <= 2:
                body_start = index
                break

    for block in blocks[body_start:]:
        kind = block[0]
        if kind == "heading":
            level = block[1]
            if level == 1:
                continue
            doc.add_heading(block[2], level=min(level - 1, 3))
        elif kind == "para":
            paragraph = doc.add_paragraph()
            add_inline(paragraph, block[1])
        elif kind == "table":
            add_table(doc, block[1])
        elif kind == "code":
            add_code_block(doc, block[1])
        elif kind == "bullets":
            for item in block[1]:
                paragraph = doc.add_paragraph(style="List Bullet")
                add_inline(paragraph, item)
        elif kind == "ordered":
            for item in block[1]:
                paragraph = doc.add_paragraph(style="List Number")
                add_inline(paragraph, item)
        elif kind == "quote":
            add_quote(doc, block[1])
        elif kind == "hr":
            add_hr(doc)


def main() -> None:
    if not SOURCE.exists():
        sys.exit(f"未找到源文件：{SOURCE}")
    text = SOURCE.read_text(encoding="utf-8")
    doc = setup_document()
    render(doc, parse_blocks(text))
    doc.save(OUTPUT)
    print(f"已生成：{OUTPUT}")


if __name__ == "__main__":
    main()
