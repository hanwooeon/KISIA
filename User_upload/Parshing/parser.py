from __future__ import annotations
import re
from pathlib import Path
from docling.document_converter import DocumentConverter
import openpyxl

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


def _find_header_idx(rows: list[list], col_count: int) -> int | None:
    """서브섹션 행 목록에서 실제 헤더 행 인덱스를 반환한다.

    각 행의 비어있지 않은 셀 수를 계산하고, 최대값의 80% 이상을 채운
    첫 번째 행을 헤더로 선택한다. 이렇게 하면 메타 행(2~4셀)을 건너뛰고
    실제 컬럼 헤더(고밀도 행)를 올바르게 감지한다.
    """
    if not rows:
        return None
    counts = [sum(1 for c in r if c is not None and str(c).strip()) for r in rows]
    max_count = max(counts)
    if max_count < 2:
        return None
    threshold = max(2, int(max_count * 0.8))
    for i, cnt in enumerate(counts):
        if cnt >= threshold:
            return i
    return None


def _parse_xlsx(path: Path) -> tuple[str, list[dict]]:
    wb = openpyxl.load_workbook(str(path), data_only=True)
    markdown_parts = []
    elements = []

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            continue

        non_empty_rows = [r for r in rows if any(c is not None and str(c).strip() for c in r)]
        if not non_empty_rows:
            continue

        markdown_parts.append(f"## {sheet_name}")
        elements.append({'text': sheet_name, 'label': 'section_header', 'page_no': None})

        col_count = max(len(r) for r in non_empty_rows)

        # 행을 서브섹션으로 분리: 셀 1개짜리 병합 행은 ### 제목, 나머지는 데이터
        subsections: list[tuple[str | None, list[list]]] = []
        current_title: str | None = None
        current_rows: list[list] = []

        for raw_row in non_empty_rows:
            row = list(raw_row) + [None] * (col_count - len(raw_row))
            non_empty = [c for c in row if c is not None and str(c).strip()]

            if len(non_empty) == 1:
                if current_rows:
                    subsections.append((current_title, current_rows))
                    current_rows = []
                current_title = non_empty[0]
            else:
                current_rows.append(row)

        if current_rows:
            subsections.append((current_title, current_rows))

        # 서브섹션별로 헤더를 밀도 기반으로 탐지 후 마크다운 테이블 생성
        for title, sec_rows in subsections:
            if title:
                markdown_parts.append(f"### {title}")
                elements.append({'text': title, 'label': 'section_header', 'page_no': None})

            if not sec_rows:
                continue

            header_idx = _find_header_idx(sec_rows, col_count)
            if header_idx is None:
                continue

            header_cells = [str(c) if c is not None else '' for c in sec_rows[header_idx]]
            n_cols = len(header_cells)

            table_lines = [
                '| ' + ' | '.join(header_cells) + ' |',
                '| ' + ' | '.join(['---'] * n_cols) + ' |',
            ]

            for data_row in sec_rows[header_idx + 1:]:
                cells = [str(c) if c is not None else '' for c in data_row]
                if len(cells) != n_cols:
                    continue
                if not any(c.strip() for c in cells):
                    continue
                table_lines.append('| ' + ' | '.join(cells) + ' |')
                row_text = ' | '.join(c for c in cells if c.strip())
                if row_text:
                    elements.append({'text': row_text, 'label': 'table', 'page_no': None})

            if len(table_lines) > 2:
                markdown_parts.append(_clean_merged_cell_rows('\n'.join(table_lines)))

    return '\n\n'.join(markdown_parts), elements


def parse_file(file_path: str) -> tuple[str, list[dict]]:
    path = Path(file_path)
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"지원하지 않는 파일 형식: {path.suffix}")

    if path.suffix.lower() == '.xlsx':
        return _parse_xlsx(path)

    converter = DocumentConverter()
    result = converter.convert(str(path))
    doc = result.document

    markdown = doc.export_to_markdown()
    elements = _extract_elements(doc)
    return markdown, elements
