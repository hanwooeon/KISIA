import os
os.environ["PGPASSFILE"] = ""
os.environ["PGSYSCONFDIR"] = ""

import json
import psycopg2
from psycopg2 import sql

DB_NAME = "postgres"
DB_HOST = "aws-1-ap-northeast-2.pooler.supabase.com"
DB_PORT = 5432
DB_USER = "postgres.egyivijauaxjrrelibrf"
DB_PASSWORD = "wjdqhqhdks@"

KEYWORD_EMBED_PATH = r"d:\code\KISIA\keyword_embed.json"


def connect_db():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASSWORD,
        dbname=DB_NAME
    )


def to_vector_str(embedding):
    return f"[{', '.join(str(v) for v in embedding)}]"


def main():
    with open(KEYWORD_EMBED_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    conn = connect_db()
    cur = conn.cursor()

    for item in data:
        cur.execute(
            sql.SQL("UPDATE {} SET {} = %s::vector WHERE {} = %s").format(
                sql.Identifier("항목 정리 테이블"),
                sql.Identifier("키워드 임베딩"),
                sql.Identifier("항목번호"),
            ),
            (to_vector_str(item["embedding"]), item["항목번호"])
        )

    conn.commit()
    cur.close()
    conn.close()
    print(f"키워드 임베딩 업데이트 완료: {len(data)}개 항목")


if __name__ == "__main__":
    main()
