from __future__ import annotations
import re
import json
from pathlib import Path

_TABLE_SEP = re.compile(r'^\|[-| :]+\|$')
_TABLE_ROW = re.compile(r'^\|(.+)\|$')
_HEADING = re.compile(r'^\*\*\d+\.\s+.+\*\*$|^#{1,3}\s+.+')

IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.tiff'}


def _parse_row(line: str) -> list[str] | None:
    if _TABLE_SEP.match(line):
        return None
    if not _TABLE_ROW.match(line):
        return None
    return [c.strip() for c in line.split('|')[1:-1]]


def _nullable(val: str) -> str | None:
    return None if val in ('-', 'None', '', None) else val


# ── 형식 1: ## 헤딩 + 테이블 (점검표 PDF/기존 xlsx) ──────────────────────────

def _chunk_structured(text: str, source: str) -> list[dict]:
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


# ── 형식 2: 점검일/점검구역이 테이블 컬럼으로 있는 xlsx ──────────────────────

def _chunk_flat_table(text: str, source: str) -> list[dict]:
    chunks = []
    chunk_id = 1
    headers: list[str] | None = None

    for line in text.split('\n'):
        if not line.startswith('|'):
            continue
        cells = _parse_row(line)
        if cells is None:
            continue
        if headers is None:
            headers = cells
            continue
        if len(cells) != len(headers):
            continue

        row = dict(zip(headers, cells))
        date = _nullable(row.get('점검일', ''))
        area = _nullable(row.get('점검구역', ''))
        item = row.get('점검항목')
        criteria = row.get('점검기준')
        result = row.get('결과')

        parts = []
        if date:    parts.append(f"점검일: {date}")
        if area:    parts.append(f"점검구역: {area}")
        if item:    parts.append(f"점검항목: {item}")
        if criteria: parts.append(f"점검기준: {criteria}")
        if result:  parts.append(f"결과: {result}")
        if _nullable(row.get('미흡내용', '')):
            parts.append(f"미흡내용: {row['미흡내용']}")
        if _nullable(row.get('조치내용', '')):
            parts.append(f"조치내용: {row['조치내용']}")

        chunks.append({
            'chunk_id': chunk_id,
            'source': source,
            'inspection_date': date,
            'inspection_area': area,
            'inspection_item': item,
            'criteria': criteria,
            'result': result,
            'deficiency': _nullable(row.get('미흡내용', '')),
            'action': _nullable(row.get('조치내용', '')),
            'action_date': _nullable(row.get('조치완료일', '')),
            'content': ' | '.join(parts),
        })
        chunk_id += 1

    return chunks


# ── 형식 3: 일반 문서 (계약서, 확인서 등 docx) ──────────────────────────────

def _chunk_general_document(text: str, source: str) -> list[dict]:
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
        if _HEADING.match(stripped):
            if current_lines:
                flush()
            current_section = re.sub(r'[#*]+\s*', '', stripped).strip()
        else:
            if stripped:
                current_lines.append(stripped)

    flush()
    return chunks


# ── 형식 4: 이미지 OCR 평문 ────────────────────────────────────────────────

def _chunk_plain_text(text: str, source: str) -> list[dict]:
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
        if len(stripped) <= 20 and re.search(r'[가-힣]', stripped) and not re.search(r'[:：]', stripped):
            if current_lines:
                flush()
            current_section = stripped
        else:
            current_lines.append(stripped)

    flush()
    return chunks


# ── 형식 자동 감지 ────────────────────────────────────────────────────────

def chunk_markdown(text: str, source: str) -> list[dict]:
    ext = Path(source).suffix.lower()

    if ext in IMAGE_EXTENSIONS:
        return _chunk_plain_text(text, source)

    # xlsx: 점검일/점검구역이 테이블 컬럼으로 있는 평면 테이블
    for line in text.split('\n'):
        if line.startswith('|') and '점검일' in line and '점검구역' in line:
            return _chunk_flat_table(text, source)

    # ## 헤딩 + 점검항목 테이블 구조 (점검표 PDF/마크다운)
    if re.search(r'^## ', text, re.MULTILINE) and '점검항목' in text:
        return _chunk_structured(text, source)

    # 그 외 일반 문서
    return _chunk_general_document(text, source)


def save_chunks(chunks: list[dict], output_path: str):
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
