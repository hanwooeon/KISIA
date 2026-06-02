from __future__ import annotations
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        url = os.environ['SUPABASE_URL']
        key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY') or os.environ['SUPABASE_ANON_KEY']
        _client = create_client(url, key)
    return _client


# ── 가이드 전처리 테이블 ──────────────────────────────────────────
def get_guide_chunks(control_id: str) -> list[dict]:
    """항목번호에 해당하는 가이드 청크 + 임베딩 반환"""
    result = (
        _get_client()
        .table('가이드 전처리 테이블')
        .select('*')
        .eq('항목번호', control_id)
        .execute()
    )
    return result.data


# ── 항목 정리 테이블 ──────────────────────────────────────────────
def get_control_info(control_id: str) -> dict | None:
    """항목번호에 해당하는 키워드 임베딩 + 필수확인요소 반환"""
    result = (
        _get_client()
        .table('항목 정리 테이블')
        .select('*')
        .eq('항목번호', control_id)
        .single()
        .execute()
    )
    return result.data


# ── 증적 데이터 테이블 ────────────────────────────────────────────
def delete_evidence_chunks(control_id: str) -> None:
    """분석 시작 전 해당 항목의 기존 증적 청크를 모두 삭제"""
    _get_client().table('증적 데이터 테이블').delete().eq('user_selection', control_id).execute()


def get_evidence_chunks(control_id: str) -> dict[int, list[dict]]:
    """
    user_selection이 control_id인 증적 청크를
    { inspection_no: [chunk, ...] } 형태로 반환 (파일별 그룹)
    """
    result = (
        _get_client()
        .table('증적 데이터 테이블')
        .select('*')
        .eq('user_selection', control_id)
        .execute()
    )

    grouped: dict[int, list[dict]] = {}
    for chunk in result.data:
        no = chunk['inspection_no']
        grouped.setdefault(no, []).append(chunk)
    return grouped


# ── 점검 결과 테이블 ──────────────────────────────────────────────
def _next_result_no() -> int:
    """점검 결과 테이블의 현재 최대 점검번호 + 1 반환 (비어있으면 1)"""
    result = (
        _get_client()
        .table('점검 결과 테이블')
        .select('*')
        .execute()
    )
    if result.data:
        return max(row['점검 번호'] for row in result.data) + 1
    return 1


def save_result(
    control_id: str,
    evidence_name: str,
    guide_similarity: float,
    keyword_similarity: float,
    is_compliant: bool,
    judgment_reason: str,
    verdict: str | None = None,
    improvement: str | None = None,
    user_id: str | None = None,
) -> None:
    """분석 결과를 점검 결과 테이블에 저장"""
    display_verdict = verdict if verdict in ('적합', '부분 적합', '부적합') else ('적합' if is_compliant else '부적합')
    next_no = _next_result_no()
    _get_client().table('점검 결과 테이블').insert({
        '점검 번호':      next_no,
        '증적명':         evidence_name,
        '사용자 선택 항목': control_id,
        '유사도 일치율':   round((guide_similarity + keyword_similarity) / 2, 4),
        '적합/부적합':    display_verdict,
        '판단근거':       judgment_reason,
        '개선사항':       improvement,
    }).execute()
