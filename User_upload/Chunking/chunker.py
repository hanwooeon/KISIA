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


# ── 형식 1: 일반 문서 (계약서, 확인서 등 docx) ──────────────────────────────

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


# ── 형식 6: xlsx 시트별 행 단위 청킹 ─────────────────────────────────────

def _chunk_xlsx_by_rows(text: str, source: str) -> list[dict]:
    chunks = []
    chunk_id = 1
    current_sheet: str | None = None
    current_subsection: str | None = None
    headers: list[str] | None = None
    row_no = 0

    for line in text.split('\n'):
        stripped = line.strip()
        if re.match(r'^## ', stripped):
            current_sheet = stripped.lstrip('#').strip()
            current_subsection = None
            headers = None
            row_no = 0
            continue

        if re.match(r'^### ', stripped):
            current_subsection = stripped.lstrip('#').strip()
            headers = None
            row_no = 0
            continue

        if not stripped.startswith('|'):
            continue

        cells = _parse_row(stripped)
        if cells is None:
            continue

        if headers is None:
            headers = cells
            row_no = 0
            continue

        if len(cells) != len(headers):
            continue

        row = dict(zip(headers, cells))
        content_parts = [f"{k}: {v}" for k, v in row.items() if _nullable(v)]
        content = ' | '.join(content_parts)
        if not content:
            continue

        row_no += 1
        section = current_sheet or '본문'
        if current_subsection:
            section = f"{section} > {current_subsection}"

        chunks.append({
            'chunk_id': f"{Path(source).stem}-{chunk_id:04d}",
            'source': source,
            'section': section,
            'row_no': row_no,
            'content': content,
            'element_type': 'table',
        })
        chunk_id += 1

    return chunks


# ── 확장자 기반 분기 ──────────────────────────────────────────────────────

def chunk_markdown(text: str, source: str, elements: list[dict] | None = None, doc=None, page_map: dict[str, int] | None = None) -> list[dict]:
    ext = Path(source).suffix.lower()

    # xlsx: 시트별 행 단위 청킹 (## SheetName + 테이블 구조)
    if ext == '.xlsx':
        return _chunk_xlsx_by_rows(text, source)

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
