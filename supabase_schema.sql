-- Supabase SQL Editor에서 실행하세요

-- pgvector 확장 활성화 (최초 1회)
CREATE EXTENSION IF NOT EXISTS vector;

-- 기존 테이블 있으면 삭제 후 재생성
DROP TABLE IF EXISTS document_chunks;

CREATE TABLE document_chunks (
    id              BIGSERIAL PRIMARY KEY,   -- DB 내부 순번
    chunk_id        INTEGER     NOT NULL,    -- 증적 청크ID (파일 내 청크 번호)
    user_id         TEXT,                    -- 사용자ID (GUI 연동 후 채움)
    evidence_name   TEXT        NOT NULL,    -- 증적명 (파일명)
    content         TEXT        NOT NULL,    -- 청크 내용
    metadata        JSONB,                   -- 메타데이터 (점검일, 구역, 항목 등)
    embedding       VECTOR(1024),            -- 증적 청크 임베딩
    user_selection  TEXT,                    -- 사용자 선택 항목 (GUI 연동 후 채움)
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 벡터 유사도 검색 인덱스 (데이터 적재 후 생성 권장)
-- CREATE INDEX ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 유사도 검색 함수
DROP FUNCTION IF EXISTS match_chunks(vector, integer);
CREATE OR REPLACE FUNCTION match_chunks(
    query_embedding VECTOR(1024),
    match_count     INT DEFAULT 5
)
RETURNS TABLE (
    id              BIGINT,
    evidence_name   TEXT,
    content         TEXT,
    metadata        JSONB,
    similarity      FLOAT
)
LANGUAGE SQL STABLE
AS $$
    SELECT id, evidence_name, content, metadata,
           1 - (embedding <=> query_embedding) AS similarity
    FROM document_chunks
    ORDER BY embedding <=> query_embedding
    LIMIT match_count;
$$;
