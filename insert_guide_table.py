import os
os.environ["PGPASSFILE"] = ""
os.environ["PGSYSCONFDIR"] = ""

import json
import psycopg2
import psycopg2.extras
from psycopg2 import sql

DB_NAME = "postgres"
DB_HOST = "db.egyivijauaxjrrelibrf.supabase.co"
DB_PORT = 5432
DB_USER = "postgres"
DB_PASSWORD = ""

GUIDE_CHUNK_EMBED_PATH = r"d:\code\KISIA\guide_chunk_embed.json"
CHUNKS_WITH_META_PATH = r"d:\code\KISIA\chunk_with_meta.json"


def connect_db():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASSWORD,
        dbname=DB_NAME
    )


def to_vector_str(embedding):
    return f"[{', '.join(str(v) for v in embedding)}]"


def get_content(chunk):
    field = chunk["metadata"]["청크유형"]
    return chunk.get(field, "")


def main():
    with open(GUIDE_CHUNK_EMBED_PATH, "r", encoding="utf-8") as f:
        embed_data = json.load(f)

    with open(CHUNKS_WITH_META_PATH, "r", encoding="utf-8") as f:
        chunk_data = json.load(f)

    chunk_map = {c["guide_chunk_id"]: c for c in chunk_data}

    conn = connect_db()
    cur = conn.cursor()

    cur.execute(sql.SQL("DELETE FROM {}").format(sql.Identifier("가이드 전처리 테이블")))
    print("기존 데이터 삭제 완료")

    insert_query = sql.SQL(
        "INSERT INTO {} ({}, {}, {}, {}, {}) VALUES (%s, %s, %s, %s, %s::vector)"
    ).format(
        sql.Identifier("가이드 전처리 테이블"),
        sql.Identifier("가이드 청크ID"),
        sql.Identifier("항목번호"),
        sql.Identifier("청크 내용"),
        sql.Identifier("메타데이터"),
        sql.Identifier("가이드 청크 임베딩"),
    )

    count = 0
    for entry in embed_data:
        chunk_id = entry["guide_chunk_id"]
        항목번호 = entry["항목번호"]
        embedding = to_vector_str(entry["embedding"])

        chunk = chunk_map.get(chunk_id, {})
        content = get_content(chunk) if chunk else ""
        metadata = psycopg2.extras.Json(chunk.get("metadata", {}))

        cur.execute(insert_query, (chunk_id, 항목번호, content, metadata, embedding))
        count += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"가이드 전처리 테이블 삽입 완료: {count}개 행")


if __name__ == "__main__":
    main()
