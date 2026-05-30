from __future__ import annotations
import sys
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'User_upload'))
from Parshing.parser import parse_file
from Parshing.cleaner import clean_markdown
from Chunking.chunker import chunk_markdown
from Embedding.embedder import embed_texts
from DB.uploader import upload_chunks

from services.db import (
    get_control_info,
    get_guide_chunks,
    get_evidence_chunks,
    save_result,
)
from services.similarity import best_chunk_similarity, keyword_similarity
from services.llm import judge, summarize_file
from routers.upload import get_temp_file, remove_temp_file

router = APIRouter()


class FileItem(BaseModel):
    temp_id: str
    filename: str
    control_id: str


class AnalyzeRequest(BaseModel):
    items: list[FileItem]          # 업로드된 파일 목록
    control_ids: list[str]         # 분석할 항목 목록


def _process_file(temp_id: str, control_id: str) -> int:
    """임시 파일 → OCR/청킹/임베딩 → DB 저장 → inspection_no 반환"""
    info = get_temp_file(temp_id)
    if not info:
        raise HTTPException(status_code=404, detail=f"임시 파일을 찾을 수 없습니다: {temp_id}")

    try:
        raw, elements, doc, page_map = parse_file(info['path'])
        cleaned = clean_markdown(raw)
        chunks = chunk_markdown(cleaned, source=info['filename'], elements=elements, doc=doc, page_map=page_map)

        if not chunks:
            raise HTTPException(status_code=422, detail=f"{info['filename']}에서 텍스트를 추출할 수 없습니다.")

        contents = [c['content'] for c in chunks]
        embeddings = embed_texts(contents)
        for chunk, emb in zip(chunks, embeddings):
            chunk['embedding'] = emb

        inspection_no = upload_chunks(chunks, user_selection=control_id)
        return inspection_no
    finally:
        remove_temp_file(temp_id)


@router.post("/analyze")
async def analyze(body: AnalyzeRequest):
    """
    분석 시작 버튼 클릭 시 실행
    1. 임시 파일 → OCR/청킹/임베딩 → DB 저장
    2. 유사도 계산
    3. LLM 판단
    4. 결과 저장 및 반환
    """
    # ── 1. 파일 처리 (OCR/청킹/임베딩) ──────────────────────────────
    for item in body.items:
        _process_file(item.temp_id, item.control_id)

    # ── 2. 항목별 분석 ───────────────────────────────────────────────
    results = []

    for control_id in body.control_ids:
        control_info = get_control_info(control_id)
        if not control_info:
            results.append({'control_id': control_id, 'error': '항목 정보를 찾을 수 없습니다.'})
            continue

        guide_chunks = get_guide_chunks(control_id)
        if not guide_chunks:
            results.append({'control_id': control_id, 'error': '가이드라인 데이터가 없습니다.'})
            continue

        evidence_by_file = get_evidence_chunks(control_id)
        if not evidence_by_file:
            results.append({'control_id': control_id, 'error': '업로드된 증적 파일이 없습니다.'})
            continue

        import json
        _kw_raw = control_info.get('키워드 임베딩')
        keyword_emb = json.loads(_kw_raw) if isinstance(_kw_raw, str) else _kw_raw
        control_name   = control_info.get('항목명', control_id)
        required_elements = control_info.get('필수확인요소', '')

        # ── 파일별: 내용 요약만 수행 (합격/불합격 판단 없음) ──────────
        file_results = []
        for inspection_no, ev_chunks in evidence_by_file.items():
            filename = ev_chunks[0].get('evidence_name', '알 수 없음')
            guide_sim, _ = best_chunk_similarity(ev_chunks, guide_chunks)
            kw_sim = keyword_similarity(ev_chunks, keyword_emb) if keyword_emb else 0.0

            file_data = summarize_file(
                control_id=control_id,
                control_name=control_name,
                evidence_chunks=ev_chunks,
                filename=filename,
            )

            file_results.append({
                'inspection_no':      inspection_no,
                'filename':           filename,
                'guide_similarity':   round(guide_sim, 4),
                'keyword_similarity': round(kw_sim, 4),
                'file_summary':       file_data.get('description', ''),
                'file_confirmed':     file_data.get('confirmed', []),
                'file_missing':       file_data.get('missing', []),
            })

        # ── 종합 판단: 항상 전체 증적 기반으로 한 번만 ──────────────
        all_ev_chunks = [c for chunks in evidence_by_file.values() for c in chunks]
        guide_sim_all, top_all = best_chunk_similarity(all_ev_chunks, guide_chunks)
        kw_sim_all = keyword_similarity(all_ev_chunks, keyword_emb) if keyword_emb else 0.0

        file_summaries = [
            {'filename': fr['filename'], 'summary': fr.get('file_summary', '')}
            for fr in file_results
        ]
        llm_result = judge(
            control_id=control_id,
            control_name=control_name,
            required_elements=required_elements,
            guide_similarity=guide_sim_all,
            keyword_similarity=kw_sim_all,
            top_guide_chunks=top_all,
            all_guide_chunks=guide_chunks,
            evidence_chunks=all_ev_chunks,
            file_summaries=file_summaries,
        )
        verdict = llm_result.get('verdict', '부적합')
        overall = {
            'guide_similarity':   round(guide_sim_all, 4),
            'keyword_similarity': round(kw_sim_all, 4),
            'verdict':            verdict,
            'is_compliant':       verdict != '부적합',
            'judgment_reason':    llm_result.get('judgment_reason', ''),
            'improvement':        llm_result.get('improvement'),
            'action_items':       llm_result.get('action_items') or [],
        }

        save_result(
            control_id=control_id,
            evidence_name=', '.join(r['filename'] for r in file_results),
            guide_similarity=overall['guide_similarity'],
            keyword_similarity=overall['keyword_similarity'],
            verdict=overall['verdict'],
            is_compliant=overall['is_compliant'],
            judgment_reason=overall['judgment_reason'],
            improvement=overall.get('improvement'),
        )

        results.append({
            'control_id':   control_id,
            'control_name': control_name,
            'file_results': file_results,
            'overall':      overall,
        })

    return {'results': results}
