from __future__ import annotations
import json
import numpy as np


def _parse_vec(vec) -> list[float]:
    """Supabase가 벡터를 문자열로 반환할 경우 파싱"""
    if isinstance(vec, str):
        return json.loads(vec)
    return vec


def cosine_similarity(vec_a, vec_b) -> float:
    """두 벡터의 코사인 유사도 반환 (0~1)"""
    a = np.array(_parse_vec(vec_a), dtype=np.float32)
    b = np.array(_parse_vec(vec_b), dtype=np.float32)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def best_chunk_similarity(
    evidence_chunks: list[dict],
    guide_chunks: list[dict],
    evidence_key: str = 'embedding',
    guide_key: str = '가이드 청크 임베딩',
) -> tuple[float, list[dict]]:
    """
    증적 청크 전체 vs 가이드 청크 전체 중
    가장 높은 유사도 조합들을 찾아 평균 반환

    Returns:
        (평균 유사도, 상위 매칭 결과 리스트)
    """
    scores = []
    for ev in evidence_chunks:
        ev_emb = ev.get(evidence_key)
        if not ev_emb:
            continue
        for guide in guide_chunks:
            g_emb = guide.get(guide_key)
            if not g_emb:
                continue
            score = cosine_similarity(ev_emb, g_emb)
            scores.append({
                'evidence_chunk_id': ev.get('chunk_id'),
                'guide_chunk_id':    guide.get('가이드 청크ID'),
                'guide_content':     guide.get('청크 내용'),
                'score':             score,
            })

    if not scores:
        return 0.0, []

    scores.sort(key=lambda x: x['score'], reverse=True)
    top = scores[:5]
    avg = float(np.mean([s['score'] for s in top]))
    return avg, top


def keyword_similarity(
    evidence_chunks: list[dict],
    keyword_embedding: list[float],
    evidence_key: str = 'embedding',
) -> float:
    """
    증적 청크 전체 vs 키워드 임베딩
    가장 높은 유사도 반환
    """
    sims = []
    for ev in evidence_chunks:
        ev_emb = ev.get(evidence_key)
        if not ev_emb:
            continue
        sims.append(cosine_similarity(ev_emb, keyword_embedding))

    return float(max(sims)) if sims else 0.0
