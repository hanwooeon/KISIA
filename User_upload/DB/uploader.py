from __future__ import annotations
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_client: Client | None = None

_METADATA_KEYS = {
    'inspection_date', 'inspection_area', 'inspection_item',
    'criteria', 'result', 'deficiency', 'action', 'action_date', 'section',
}
_SKIP_KEYS = {'chunk_id', 'source', 'content', 'embedding'}


def _to_row(chunk: dict) -> dict:
    metadata = {k: v for k, v in chunk.items() if k in _METADATA_KEYS and v is not None}
    return {
        'chunk_id':      chunk['chunk_id'],
        'evidence_name': chunk['source'],
        'content':       chunk['content'],
        'metadata':      metadata or None,
        'embedding':     chunk.get('embedding'),
        'user_id':       None,
        'user_selection': None,
    }


def _get_client() -> Client:
    global _client
    if _client is None:
        url = os.environ['SUPABASE_URL']
        key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY') or os.environ['SUPABASE_ANON_KEY']
        _client = create_client(url, key)
    return _client


def upload_chunks(chunks: list[dict]) -> None:
    client = _get_client()
    rows = [_to_row(c) for c in chunks]
    client.table('document_chunks').insert(rows).execute()
