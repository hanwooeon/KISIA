from __future__ import annotations
import os
import re
import tempfile
from pathlib import Path
import openpyxl

SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".pptx", ".xlsx",
}

_converter = None

def _get_converter():
    global _converter
    if _converter is None:
        from docling.document_converter import DocumentConverter
        _converter = DocumentConverter()
    return _converter

_HEADING_LABELS = {'section_header', 'title', 'page_header'}

_SEP_ROW = re.compile(r'^\|[-| :]+\|$')

# 한국 문서의 헤딩 패턴 (로마자, 제X장, 숫자목차, 한글목차)
_H1_PAT = re.compile(r'^[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪⅫ]|^제\s*\d+\s*[장편절]')
_H2_PAT = re.compile(r'^\d+\.\s')
_H3_PAT = re.compile(r'^[가나다라마바사아자차카타파하]\.\s')


def _fix_docx_headings(docx_path: str) -> tuple[str, dict[str, int]]:
    """Normal 스타일의 전체 볼드 단락을 Heading 스타일로 교정하고,
    단락 텍스트 → 페이지 번호 맵도 함께 반환.
    변경 없으면 원본 경로 그대로 반환."""
    try:
        from docx import Document as _Doc
        from docx.oxml.ns import qn as _qn
    except ImportError:
        return docx_path, {}

    doc = _Doc(docx_path)

    # 페이지 번호 맵 빌드 (w:br type=page 기준)
    # 단락 + 표 셀 모두 포함 → 표 형식 회의록의 섹션도 page_no 추적 가능
    page_map: dict[str, int] = {}
    page_no = 1

    def _register(element):
        """요소의 텍스트와 페이지 번호를 page_map에 등록"""
        text = element.text.strip() if hasattr(element, 'text') else ''
        if text:
            page_map[text[:40]] = page_no

    def _count_pages(element):
        """요소 내 페이지 구분자(w:br type=page) 수를 반환"""
        count = 0
        for br in element._element.iter(_qn('w:br')):
            if br.get(_qn('w:type')) == 'page':
                count += 1
        return count

    # 문서 body를 순서대로 순회 (단락과 표가 섞여 있음)
    from docx.oxml.ns import qn as _qn2
    for child in doc.element.body:
        tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
        if tag == 'p':                          # 일반 단락
            from docx.text.paragraph import Paragraph
            para = Paragraph(child, doc)
            _register(para)
            page_no += _count_pages(para)
        elif tag == 'tbl':                      # 표
            from docx.table import Table
            tbl = Table(child, doc)
            for row in tbl.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        _register(para)
                        page_no += _count_pages(para)

    # 헤딩 스타일 교정
    modified = False
    for para in doc.paragraphs:
        if 'Heading' in para.style.name or 'heading' in para.style.name:
            continue
        text = para.text.strip()
        if not text or len(text) > 80:
            continue
        runs = [r for r in para.runs if r.text.strip()]
        if not runs or not all(r.bold for r in runs):
            continue

        if _H1_PAT.match(text):
            level = 1
        elif _H2_PAT.match(text):
            level = 2
        elif _H3_PAT.match(text):
            level = 3
        else:
            level = 1

        try:
            para.style = doc.styles[f'Heading {level}']
            modified = True
        except KeyError:
            try:
                para.style = doc.styles['Heading 1']
                modified = True
            except KeyError:
                pass

    if not modified:
        return docx_path, page_map

    tmp = tempfile.NamedTemporaryFile(suffix='.docx', delete=False)
    tmp.close()
    doc.save(tmp.name)
    return tmp.name, page_map


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


_IMAGE_LABELS = {'picture', 'figure', 'image'}

def _extract_elements(doc) -> list[dict]:
    elements = []
    try:
        for item, _ in doc.iterate_items():
            label = item.label.value if hasattr(item.label, 'value') else str(item.label)
            page_no = None
            prov = getattr(item, 'prov', None)
            if prov:
                page_no = prov[0].page_no

            # 이미지/그림 요소 → 서명·도장 플레이스홀더로 포함
            if label in _IMAGE_LABELS:
                elements.append({
                    'text': '[ 이미지/서명 ]',
                    'label': label,
                    'page_no': page_no,
                })
                continue

            text = getattr(item, 'text', None)
            if not text or not text.strip():
                continue
            elements.append({
                'text': text.strip(),
                'label': label,
                'page_no': page_no,
            })
    except Exception:
        pass
    return elements


def _find_header_idx(rows: list[list], col_count: int) -> int | None:
    """밀도 기반으로 헤더 행 인덱스를 반환한다.
    비어있지 않은 셀이 최대 밀도의 80% 이상인 첫 번째 행을 헤더로 선택한다.
    메타 행(2~4셀)을 건너뛰고 실제 컬럼 헤더를 올바르게 감지한다.
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
    """openpyxl로 xlsx를 직접 파싱 → (markdown, elements) 반환."""
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

        # 셀 1개짜리 행은 ### 서브섹션 제목, 나머지는 데이터
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

        for title, sec_rows in subsections:
            if title:
                markdown_parts.append(f"### {title}")
                elements.append({'text': str(title), 'label': 'section_header', 'page_no': None})

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


def parse_file(file_path: str) -> tuple[str, list[dict], object, dict]:
    path = Path(file_path)
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"지원하지 않는 파일 형식: {path.suffix}")

    # xlsx: openpyxl로 직접 파싱 (docling OCR 불필요)
    if path.suffix.lower() == '.xlsx':
        markdown, elements = _parse_xlsx(path)
        return markdown, elements, None, {}

    actual_path = str(path)
    tmp_created = False
    page_map: dict[str, int] = {}

    if path.suffix.lower() == '.docx':
        fixed, page_map = _fix_docx_headings(str(path))
        if fixed != str(path):
            actual_path = fixed
            tmp_created = True

    try:
        converter = _get_converter()
        result = converter.convert(actual_path)
        doc = result.document

        markdown = doc.export_to_markdown()
        elements = _extract_elements(doc)
        return markdown, elements, doc, page_map
    finally:
        if tmp_created:
            os.unlink(actual_path)
