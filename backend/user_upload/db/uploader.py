from __future__ import annotations
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_client: Client | None = None

_METADATA_KEYS = {
    'inspection_date', 'inspection_area', 'inspection_item',
    'criteria', 'result', 'deficiency', 'action', 'action_date',
    'section', 'page_no', 'subsection',
}
_SKIP_KEYS = {'chunk_id', 'source', 'content', 'embedding'}


def _to_row(chunk: dict, inspection_no: int, user_selection: str | None = None) -> dict:
    metadata = {k: v for k, v in chunk.items() if k in _METADATA_KEYS and v is not None}
    return {
        'inspection_no':  inspection_no,
        'chunk_id':       chunk['chunk_id'],
        'evidence_name':  chunk['source'],
        'content':        chunk['content'],
        'metadata':       metadata or None,
        'embedding':      chunk.get('embedding'),
        'user_selection': user_selection,
    }


def to_export_rows(chunks: list[dict], inspection_no: int, user_selection: str | None = None) -> list[dict]:
    return [_to_row(c, inspection_no, user_selection) for c in chunks]


def _get_client() -> Client:
    global _client
    if _client is None:
        url = os.environ['SUPABASE_URL']
        key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY') or os.environ['SUPABASE_ANON_KEY']
        _client = create_client(url, key)
    return _client


def _next_inspection_no() -> int:
    client = _get_client()
    result = client.table('증적 데이터 테이블').select('inspection_no').order('inspection_no', desc=True).limit(1).execute()
    if result.data:
        return result.data[0]['inspection_no'] + 1
    return 1


def upload_chunks(chunks: list[dict], inspection_no: int | None = None, user_selection: str | None = None) -> int:
    client = _get_client()
    if inspection_no is None:
        inspection_no = _next_inspection_no()
    rows = [_to_row(c, inspection_no, user_selection) for c in chunks]
    client.table('증적 데이터 테이블').insert(rows).execute()
    return inspection_no
