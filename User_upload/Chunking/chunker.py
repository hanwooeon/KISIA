from __future__ import annotations
import re
import json
from pathlib import Path

_TABLE_SEP = re.compile(r'^\|[-| :]+\|$')
_TABLE_ROW = re.compile(r'^\|(.+)\|$')

IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.tiff'}


def _parse_row(line: str) -> list[str] | None:
    if _TABLE_SEP.match(line):
        return None
    if not _TABLE_ROW.match(line):
        return None
    return [c.strip() for c in line.split('|')[1:-1]]


def _nullable(val: str) -> str | None:
    return None if val in ('-', 'None', '') else val


def _chunk_plain_text(text: str, source: str) -> list[dict]:
    """이미지 OCR 결과처럼 헤딩/테이블 없는 평문을 청킹."""
    chunks = []
    chunk_id = 1
    current_section = '본문'
    current_lines: list[str] = []

    def flush():
        nonlocal chunk_id
        content = '\n'.join(current_lines).strip()
        if content:
            chunks.append({
                'chunk_id': chunk_id,
                'source': source,
                'section': current_section,
                'content': content,
            })
            chunk_id += 1
        current_lines.clear()

    for line in text.split('\n'):
        stripped = line.strip()
        if not stripped:
            continue
        # 짧고 단독으로 서있는 줄을 섹션 헤딩 후보로 간주
        if len(stripped) <= 20 and re.search(r'[가-힣]', stripped) and not re.search(r'[:：]', stripped):
            if current_lines:
                flush()
            current_section = stripped
        else:
            current_lines.append(stripped)

    flush()
    return chunks


def _chunk_structured(text: str, source: str) -> list[dict]:
    """## 헤딩 + 테이블 구조의 점검표 마크다운을 청킹."""
    chunks = []
    chunk_id = 1
    current_date = None
    current_area = None
    headers: list[str] | None = None

    for line in text.split('\n'):
        if re.match(r'^## ', line):
            current_date = line.lstrip('#').strip()
            current_area = None
            headers = None
        elif re.match(r'^### ', line):
            current_area = line.lstrip('#').strip()
            headers = None
        elif line.startswith('|'):
            cells = _parse_row(line)
            if cells is None:
                continue
            if headers is None:
                headers = cells
                continue
            if len(cells) != len(headers):
                continue

            row = dict(zip(headers, cells))
            chunks.append({
                'chunk_id': chunk_id,
                'source': source,
                'inspection_date': current_date,
                'inspection_area': current_area,
                'inspection_item': row.get('점검항목'),
                'criteria': row.get('점검기준'),
                'result': row.get('결과'),
                'deficiency': _nullable(row.get('미흡내용', '')),
                'action': _nullable(row.get('조치내용', '')),
                'action_date': _nullable(row.get('조치완료일', '')),
                'content': (
                    f"점검일: {current_date} | 점검구역: {current_area} | "
                    f"점검항목: {row.get('점검항목')} | "
                    f"점검기준: {row.get('점검기준')} | "
                    f"결과: {row.get('결과')}"
                    + (f" | 미흡내용: {row.get('미흡내용')}" if _nullable(row.get('미흡내용', '')) else '')
                    + (f" | 조치내용: {row.get('조치내용')}" if _nullable(row.get('조치내용', '')) else '')
                ),
            })
            chunk_id += 1

    return chunks


def chunk_markdown(text: str, source: str) -> list[dict]:
    ext = Path(source).suffix.lower()
    if ext in IMAGE_EXTENSIONS:
        return _chunk_plain_text(text, source)
    return _chunk_structured(text, source)


def save_chunks(chunks: list[dict], output_path: str):
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
