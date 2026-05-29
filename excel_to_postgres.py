import os
os.environ["PGPASSFILE"] = ""
os.environ["PGSYSCONFDIR"] = ""

import json
import pandas as pd
import psycopg2
import psycopg2.extras
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

EXCEL_PATH = r"C:\Users\이수민\Desktop\alldata.xlsx"
DB_NAME = "postgres"
DB_HOST = "db.egyivijauaxjrrelibrf.supabase.co"
DB_PORT = 5432
DB_USER = "postgres"
DB_PASSWORD = ""

VECTOR_DIM = 1024  # BGE-M3 임베딩 차원

# 테이블별 설정
TABLE_CONFIG = {
    "항목 정리 테이블": {
        "pk": "항목번호",
        "rename": {},
        "serial_pk": False,
        "col_order_swap": ("키워드", "필수확인요소"),
        "field_types": {"키워드 임베딩": f"vector({VECTOR_DIM})"},
    },
    "가이드 전처리 테이블": {
        "pk": "가이드 청크ID",
        "rename": {"청크ID": "가이드 청크ID", "청크 임베딩": "가이드 청크 임베딩"},
        "serial_pk": False,
        "field_types": {"메타데이터": "JSONB", "가이드 청크 임베딩": f"vector({VECTOR_DIM})"},
    },
    "점검 결과 테이블": {
        "pk": "점검 번호",
        "rename": {},
        "serial_pk": True,
        "field_types": {"유사도 일치율": "FLOAT"},
    },
}

# FK 제약: (테이블, 컬럼, 참조 테이블, 참조 컬럼)
FOREIGN_KEYS = []

TABLE_ORDER = [
    "항목 정리 테이블",
    "가이드 전처리 테이블",
    "점검 결과 테이블",
]


def get_pg_type(col, dtype, config):
    custom = config.get("field_types", {})
    if col in custom:
        return custom[col]
    if pd.api.types.is_integer_dtype(dtype):
        return "INTEGER"
    if pd.api.types.is_float_dtype(dtype):
        return "FLOAT"
    if pd.api.types.is_bool_dtype(dtype):
        return "BOOLEAN"
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "TIMESTAMP"
    return "TEXT"


def create_database():
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASSWORD,
        dbname="postgres"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
    if cur.fetchone():
        print(f"데이터베이스 '{DB_NAME}' 이미 존재합니다.")
    else:
        cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
        print(f"데이터베이스 '{DB_NAME}' 생성 완료.")
    cur.close()
    conn.close()


def connect_db():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASSWORD,
        dbname=DB_NAME
    )


def enable_pgvector(cur):
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    print("pgvector 확장 활성화 완료.")


def create_table(cur, table_name, df):
    config = TABLE_CONFIG[table_name]
    pk_col = config["pk"]
    serial_pk = config["serial_pk"]
    unique_cols = config.get("unique", [])
    is_composite = isinstance(pk_col, list)

    columns = []

    if serial_pk:
        columns.append(sql.SQL("{} SERIAL PRIMARY KEY").format(sql.Identifier(pk_col)))

    for col, dtype in zip(df.columns, df.dtypes):
        pg_type = get_pg_type(col, dtype, config)
        if not serial_pk and not is_composite and col == pk_col:
            columns.append(
                sql.SQL("{} {} PRIMARY KEY").format(sql.Identifier(col), sql.SQL(pg_type))
            )
        elif col in unique_cols:
            columns.append(
                sql.SQL("{} {} UNIQUE").format(sql.Identifier(col), sql.SQL(pg_type))
            )
        else:
            columns.append(
                sql.SQL("{} {}").format(sql.Identifier(col), sql.SQL(pg_type))
            )

    if is_composite:
        columns.append(
            sql.SQL("PRIMARY KEY ({})").format(
                sql.SQL(", ").join(sql.Identifier(c) for c in pk_col)
            )
        )

    cur.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(sql.Identifier(table_name)))
    cur.execute(
        sql.SQL("CREATE TABLE {} ({})").format(
            sql.Identifier(table_name),
            sql.SQL(", ").join(columns)
        )
    )


def convert_value(col, value, config):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None

    field_types = config.get("field_types", {})
    ftype = field_types.get(col, "")

    if ftype == "JSONB":
        if isinstance(value, dict):
            return psycopg2.extras.Json(value)
        if isinstance(value, str):
            try:
                return psycopg2.extras.Json(json.loads(value))
            except Exception:
                return psycopg2.extras.Json(value)

    if ftype.startswith("vector"):
        if isinstance(value, list):
            return f"[{', '.join(str(v) for v in value)}]"
        if isinstance(value, str):
            return value  # 이미 "[...]" 형식인 경우

    return value


def insert_rows(cur, table_name, df):
    if df.empty:
        return

    config = TABLE_CONFIG[table_name]
    serial_pk = config["serial_pk"]
    pk_col = config["pk"]
    field_types = config.get("field_types", {})

    insert_df = df.copy()
    if serial_pk and pk_col in insert_df.columns:
        insert_df = insert_df.drop(columns=[pk_col])

    cols = [sql.Identifier(c) for c in insert_df.columns]

    # vector 타입 컬럼은 ::vector 캐스팅 필요
    placeholders = []
    for c in insert_df.columns:
        ftype = field_types.get(c, "")
        if ftype.startswith("vector"):
            placeholders.append(sql.SQL("%s::vector"))
        else:
            placeholders.append(sql.Placeholder())

    query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        sql.Identifier(table_name),
        sql.SQL(", ").join(cols),
        sql.SQL(", ").join(placeholders)
    )

    for _, row in insert_df.iterrows():
        values = [convert_value(c, v, config) for c, v in zip(insert_df.columns, row)]
        cur.execute(query, values)


def add_foreign_keys(cur):
    for table, col, ref_table, ref_col in FOREIGN_KEYS:
        fk_name = f"fk_{table}_{col}".replace(" ", "_")
        cur.execute(
            sql.SQL(
                "ALTER TABLE {} ADD CONSTRAINT {} FOREIGN KEY ({}) REFERENCES {} ({})"
            ).format(
                sql.Identifier(table),
                sql.Identifier(fk_name),
                sql.Identifier(col),
                sql.Identifier(ref_table),
                sql.Identifier(ref_col),
            )
        )
        print(f"FK 추가: {table}.{col} → {ref_table}.{ref_col}")


def main():
    print("엑셀 파일 로드 중...")
    xl = pd.ExcelFile(EXCEL_PATH)

    sheets = {}
    for sheet in TABLE_ORDER:
        df = xl.parse(sheet)
        df.columns = [str(c).strip() for c in df.columns]

        rename_map = TABLE_CONFIG[sheet].get("rename", {})
        if rename_map:
            df = df.rename(columns=rename_map)

        swap = TABLE_CONFIG[sheet].get("col_order_swap")
        if swap and swap[0] in df.columns and swap[1] in df.columns:
            cols = list(df.columns)
            i, j = cols.index(swap[0]), cols.index(swap[1])
            cols[i], cols[j] = cols[j], cols[i]
            df = df[cols]

        sheets[sheet] = df
        print(f"[{sheet}] 로드 완료 (행: {len(df)}, 열: {len(df.columns)})")

    # '키워드 임베딩'을 '가이드 전처리 테이블'에서 '항목 정리 테이블' 마지막 컬럼으로 이동
    guide_df = sheets["가이드 전처리 테이블"]
    항목_df = sheets["항목 정리 테이블"]
    if "키워드 임베딩" in guide_df.columns:
        embed_map = (
            guide_df[["항목번호", "키워드 임베딩"]]
            .dropna(subset=["키워드 임베딩"])
            .drop_duplicates(subset=["항목번호"])
        )
        항목_df = 항목_df.merge(embed_map, on="항목번호", how="left")
        sheets["항목 정리 테이블"] = 항목_df
        sheets["가이드 전처리 테이블"] = guide_df.drop(columns=["키워드 임베딩"])
        print("'키워드 임베딩' 컬럼을 '항목 정리 테이블' 마지막으로 이동 완료.")

    create_database()
    conn = connect_db()
    cur = conn.cursor()

    enable_pgvector(cur)
    conn.commit()

    for table_name in TABLE_ORDER:
        df = sheets[table_name]
        print(f"\n[{table_name}] 테이블 생성 중...")
        create_table(cur, table_name, df)
        insert_rows(cur, table_name, df)
        conn.commit()
        print(f"[{table_name}] 저장 완료.")

    print("\nFK 제약 추가 중...")
    add_foreign_keys(cur)
    conn.commit()

    cur.close()
    conn.close()
    print("\n모든 작업 완료.")


if __name__ == "__main__":
    main()
