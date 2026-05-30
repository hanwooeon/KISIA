from __future__ import annotations
import re
import json
from pathlib import Path

_TABLE_SEP = re.compile(r'^\|[-| :]+\|$')
_TABLE_ROW = re.compile(r'^\|(.+)\|$')
_HEADING = re.compile(r'^\*\*\d+\.\s+.+\*\*$|^#{1,3}\s+.+')
_ARTICLE_HEADING = re.compile(r'^#{1,6}\s+(\d+)\.\s+(.+)')
_SUBSECTION_HEADING = re.compile(r'^#{1,6}\s+([가나다라마바사아자차카타파하])\s*\.\s+(.+)')
_ARTICLE_HEADING_PLAIN = re.compile(r'^(\d+)\.\s+(.+)')
_SUBSECTION_HEADING_PLAIN = re.compile(r'^([가나다라마바사아자차카타파하])\s*\.\s+(.+)')
_HEADING_LABELS = {'section_header', 'title', 'page_header'}

_hybrid_chunker = None

def _get_chunker():
    global _hybrid_chunker
    if _hybrid_chunker is None:
        from docling.chunking import HybridChunker
        _hybrid_chunker = HybridChunker(tokenizer="BAAI/bge-m3", max_tokens=512)
    return _hybrid_chunker

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
                'chunk_id': f"{Path(source).stem}-{chunk_id:04d}",
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
            'chunk_id': f"{Path(source).stem}-{chunk_id:04d}",
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
    current_article_no = ''
    current_article_title = ''
    current_subsection = ''
    current_lines: list[str] = []

    def flush():
        nonlocal chunk_id
        content = '\n'.join(current_lines).strip()
        if content:
            chunk: dict = {
                'chunk_id': f"{Path(source).stem}-{chunk_id:04d}",
                'source': source,
                'section': current_section,
                'content': content,
            }
            if current_article_no:
                chunk['article_no'] = current_article_no
                chunk['article_title'] = current_article_title
            if current_subsection:
                chunk['subsection'] = current_subsection
            chunks.append(chunk)
            chunk_id += 1
        current_lines.clear()

    for line in text.split('\n'):
        stripped = line.strip()
        article_m = _ARTICLE_HEADING.match(stripped)
        subsection_m = _SUBSECTION_HEADING.match(stripped)

        if article_m:
            if current_lines:
                flush()
            current_article_no = article_m.group(1)
            current_article_title = article_m.group(2).strip()
            current_section = f"{current_article_no}. {current_article_title}"
            current_subsection = ''
        elif subsection_m:
            if current_lines:
                flush()
            current_subsection = subsection_m.group(1)
            current_section = re.sub(r'[#*]+\s*', '', stripped).strip()
        elif _HEADING.match(stripped):
            if current_lines:
                flush()
            current_section = re.sub(r'[#*]+\s*', '', stripped).strip()
        else:
            if stripped:
                current_lines.append(stripped)

    flush()
    return chunks


# ── 형식 4: Docling 요소 기반 (일반 문서 - 메타데이터 포함) ────────────────

def _chunk_from_elements(elements: list[dict], source: str) -> list[dict]:
    chunks = []
    chunk_id = 1
    current_section = '본문'
    current_article_no = ''
    current_article_title = ''
    current_subsection = ''
    current_lines: list[str] = []
    current_start_page: int | None = None
    current_elem_types: set[str] = set()

    def flush():
        nonlocal chunk_id
        content = '\n'.join(current_lines).strip()
        if not content:
            current_lines.clear()
            current_elem_types.clear()
            return
        chunk: dict = {
            'chunk_id': f"{Path(source).stem}-{chunk_id:04d}",
            'source': source,
            'section': current_section,
            'content': content,
            'element_type': 'list' if 'list_item' in current_elem_types else 'paragraph',
        }
        if current_start_page is not None:
            chunk['page_no'] = current_start_page
        if current_article_no:
            chunk['article_no'] = current_article_no
            chunk['article_title'] = current_article_title
        if current_subsection:
            chunk['subsection'] = current_subsection
        chunks.append(chunk)
        chunk_id += 1
        current_lines.clear()
        current_elem_types.clear()

    for elem in elements:
        label = elem.get('label', 'text')
        text = elem.get('text', '').strip()
        page_no = elem.get('page_no')
        if not text:
            continue

        if label in _HEADING_LABELS:
            if current_lines:
                flush()
            article_m = _ARTICLE_HEADING_PLAIN.match(text)
            subsection_m = _SUBSECTION_HEADING_PLAIN.match(text)
            if article_m:
                current_article_no = article_m.group(1)
                current_article_title = article_m.group(2).strip()
                current_section = f"{current_article_no}. {current_article_title}"
                current_subsection = ''
            elif subsection_m:
                current_subsection = text
            else:
                current_section = text
                current_article_no = ''
                current_subsection = ''
            # page_no가 있을 때만 업데이트 (None으로 덮어쓰지 않음)
            if page_no is not None:
                current_start_page = page_no
        else:
            if not current_lines:
                # 첫 본문 요소: page_no 있을 때만 업데이트 (헤딩에서 가져온 페이지 유지)
                if page_no is not None:
                    current_start_page = page_no
            current_elem_types.add(label)
            current_lines.append(text)

    flush()
    return chunks


# ── HybridChunker (docx / pdf) ───────────────────────────────────────────

def _lookup_page(chunk_text: str, page_map: dict[str, int]) -> int | None:
    """chunk 텍스트 앞부분으로 page_map에서 페이지 번호 검색."""
    prefix = chunk_text.strip()[:40]
    for key, pno in page_map.items():
        if prefix.startswith(key[:30]) or key[:30] in prefix:
            return pno
    return None


def _chunk_with_hybrid(doc, source: str, page_map: dict[str, int] | None = None) -> list[dict]:
    chunker = _get_chunker()
    chunks = []
    for i, chunk in enumerate(chunker.chunk(doc), start=1):
        headings = list(chunk.meta.headings) if chunk.meta.headings else []
        if len(headings) > 1:
            section    = ' > '.join(headings[:-1])  # 부모 경로만 (마지막 제외)
            subsection = headings[-1]               # 현재 섹션
        elif headings:
            section    = headings[0]
            subsection = None
        else:
            section    = '본문'
            subsection = None

        # Docling prov에서 페이지 번호 추출 (모든 doc_item 순회)
        page_no = None
        if chunk.meta.doc_items:
            for doc_item in chunk.meta.doc_items:
                prov = getattr(doc_item, 'prov', None)
                if prov:
                    page_no = prov[0].page_no
                    break

        # prov가 없으면 page_map 폴백 (섹션 제목 → 청크 본문 순으로 검색)
        if page_no is None and page_map:
            for heading in headings:
                page_no = _lookup_page(heading, page_map)
                if page_no:
                    break
            if page_no is None:
                page_no = _lookup_page(chunk.text, page_map)

        c = {
            'chunk_id': f"{Path(source).stem}-{i:04d}",
            'source': source,
            'section': section,
            'page_no': page_no,
            'content': chunk.text,
        }
        if subsection:
            c['subsection'] = subsection
        chunks.append(c)
    return chunks


# ── 확장자 기반 분기 ──────────────────────────────────────────────────────

def chunk_markdown(text: str, source: str, elements: list[dict] | None = None, doc=None, page_map: dict[str, int] | None = None) -> list[dict]:
    ext = Path(source).suffix.lower()

    # xlsx: 항상 테이블 구조의 점검 데이터 → 행 단위 청킹
    if ext == '.xlsx':
        for line in text.split('\n'):
            if line.startswith('|') and '점검일' in line and '점검구역' in line:
                return _chunk_flat_table(text, source)
        return _chunk_structured(text, source)

    # docx / pdf: HybridChunker로 의미 단위 청킹
    if doc is not None:
        return _chunk_with_hybrid(doc, source, page_map=page_map)

    # doc 없을 경우 폴백
    if elements:
        return _chunk_from_elements(elements, source)
    return _chunk_general_document(text, source)


def save_chunks(chunks: list[dict], output_path: str):
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
