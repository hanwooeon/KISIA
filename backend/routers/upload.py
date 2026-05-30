from __future__ import annotations
import os
import uuid
import json
import tempfile
from fastapi import APIRouter, UploadFile, File, Form

router = APIRouter()

# 임시 파일 매핑을 디스크에 저장 (서버 재시작해도 유지)
_STORE_PATH = os.path.join(tempfile.gettempdir(), 'kisia_temp_store.json')


def _load_store() -> dict:
    if os.path.exists(_STORE_PATH):
        try:
            with open(_STORE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_store(store: dict):
    with open(_STORE_PATH, 'w', encoding='utf-8') as f:
        json.dump(store, f, ensure_ascii=False)


@router.post("/evidence/upload")
async def upload_evidence(
    control_id: str = Form(...),
    file: UploadFile = File(...),
):
    """파일을 임시 저장만 함 (빠름) - 서버 재시작해도 유지됨"""
    suffix = os.path.splitext(file.filename)[-1]
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(await file.read())
    tmp.close()

    temp_id = str(uuid.uuid4())
    store = _load_store()
    store[temp_id] = {
        'path':       tmp.name,
        'filename':   file.filename,
        'control_id': control_id,
    }
    _save_store(store)

    return {
        'temp_id':    temp_id,
        'filename':   file.filename,
        'control_id': control_id,
    }


def get_temp_file(temp_id: str) -> dict | None:
    return _load_store().get(temp_id)


def remove_temp_file(temp_id: str):
    store = _load_store()
    info = store.pop(temp_id, None)
    if info:
        _save_store(store)
        if os.path.exists(info['path']):
            os.remove(info['path'])
