from __future__ import annotations
import re
from pathlib import Path
from docling.document_converter import DocumentConverter

SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".pptx", ".xlsx",
}

_HEADING_LABELS = {'section_header', 'title', 'page_header'}

_SEP_ROW = re.compile(r'^\|[-| :]+\|$')


def _clean_merged_cell_rows(markdown: str) -> str:
    lines = markdown.split('\n')
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('|') and not _SEP_ROW.match(line):
            cells = [c.strip() for c in line.split('|')[1:-1]]
            non_empty = [c for c in cells if c]
            if len(set(non_empty)) == 1 and len(non_empty) > 1:
                result.append(non_empty[0])
                if i + 1 < len(lines) and _SEP_ROW.match(lines[i + 1]):
                    i += 1
            else:
                result.append(line)
        else:
            result.append(line)
        i += 1
    return '\n'.join(result)


def _extract_elements(doc) -> list[dict]:
    elements = []
    try:
        for item, _ in doc.iterate_items():
            text = getattr(item, 'text', None)
            if not text or not text.strip():
                continue
            label = item.label.value if hasattr(item.label, 'value') else str(item.label)
            page_no = None
            prov = getattr(item, 'prov', None)
            if prov:
                page_no = prov[0].page_no
            elements.append({
                'text': text.strip(),
                'label': label,
                'page_no': page_no,
            })
    except Exception:
        pass
    return elements


def parse_file(file_path: str) -> tuple[str, list[dict]]:
    path = Path(file_path)
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"지원하지 않는 파일 형식: {path.suffix}")

    converter = DocumentConverter()
    result = converter.convert(str(path))
    doc = result.document

    markdown = doc.export_to_markdown()
    if path.suffix.lower() == '.xlsx':
        markdown = _clean_merged_cell_rows(markdown)

    elements = _extract_elements(doc)
    return markdown, elements
