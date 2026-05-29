-- Supabase SQL Editor에서 실행하세요

-- pgvector 확장 활성화 (최초 1회)
CREATE EXTENSION IF NOT EXISTS vector;

-- 기존 테이블/함수 삭제
DROP FUNCTION IF EXISTS match_chunks(vector, integer);
DROP TABLE IF EXISTS document_chunks;

CREATE TABLE document_chunks (
    inspection_no   INTEGER     NOT NULL,     -- 점검번호 (파일당 1개, 업로드마다 자동 채번)
    chunk_id        TEXT        NOT NULL,     -- 증적 청크ID (파일명-번호)
    evidence_name   TEXT        NOT NULL,     -- 증적명 (파일명)
    content         TEXT        NOT NULL,     -- 청크 내용
    metadata        JSONB,                    -- 메타데이터
    embedding       VECTOR(1024),             -- 증적 청크 임베딩
    user_selection  TEXT,                     -- 사용자 선택 항목 (GUI 연동 후)
    PRIMARY KEY (inspection_no, chunk_id)
);

-- 유사도 검색 함수
CREATE OR REPLACE FUNCTION match_chunks(
    query_embedding VECTOR(1024),
    match_count     INT DEFAULT 5
)
RETURNS TABLE (
    inspection_no   INTEGER,
    chunk_id        TEXT,
    evidence_name   TEXT,
    content         TEXT,
    metadata        JSONB,
    similarity      FLOAT
)
LANGUAGE SQL STABLE
AS $$
    SELECT inspection_no, chunk_id, evidence_name, content, metadata,
           1 - (embedding <=> query_embedding) AS similarity
    FROM document_chunks
    ORDER BY embedding <=> query_embedding
    LIMIT match_count;
$$;
