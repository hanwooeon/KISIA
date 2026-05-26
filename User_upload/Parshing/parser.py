from __future__ import annotations
import re
from pathlib import Path
from docling.document_converter import DocumentConverter
from .ocr import ocr_image

SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".pptx", ".xlsx",
    ".png", ".jpg", ".jpeg", ".tiff",
}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff"}

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


def parse_file(file_path: str) -> str:
    path = Path(file_path)
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"지원하지 않는 파일 형식: {path.suffix}")

    if path.suffix.lower() in IMAGE_EXTENSIONS:
        return ocr_image(str(path))

    converter = DocumentConverter()
    result = converter.convert(str(path))
    markdown = result.document.export_to_markdown()

    if path.suffix.lower() == '.xlsx':
        markdown = _clean_merged_cell_rows(markdown)

    return markdown
