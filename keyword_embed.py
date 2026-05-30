import pandas as pd
import json
import numpy as np
from sentence_transformers import SentenceTransformer

EXCEL_PATH = r"C:\Users\이수민\Desktop\data.xlsx"
SHEET_NAME = "항목 정리 테이블"
MODEL_NAME = "BAAI/bge-m3"
OUTPUT_JSON = r"d:\code\KISIA\embeddings.json"
OUTPUT_NPY = r"d:\code\KISIA\embeddings.npy"


def load_data(path, sheet):
    df = pd.read_excel(path, sheet_name=sheet)
    print(f"로드된 행 수: {len(df)}")
    print(f"컬럼 목록: {list(df.columns)}")
    return df


def embed_keywords(df, model):
    keywords = df["키워드"].fillna("").tolist()
    print(f"\n임베딩 시작 (총 {len(keywords)}개)...")
    vectors = model.encode(keywords, show_progress_bar=True, normalize_embeddings=True)
    return keywords, vectors


def build_results(df, keywords, vectors):
    results = []
    for i, row in df.iterrows():
        results.append({
            "항목번호": str(row.get("항목번호", "")),
            "항목명": str(row.get("항목명", "")),
            "키워드": keywords[i],
            "embedding": vectors[i].tolist(),
        })
    return results


def main():
    print("데이터 로드 중...")
    df = load_data(EXCEL_PATH, SHEET_NAME)

    print(f"\nBGE-M3 모델 로드 중: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    keywords, vectors = embed_keywords(df, model)
    results = build_results(df, keywords, vectors)

    # JSON 저장
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nJSON 저장 완료: {OUTPUT_JSON}")

    # numpy 배열로도 저장 (벡터 연산용)
    np.save(OUTPUT_NPY, vectors)
    print(f"벡터 배열 저장 완료: {OUTPUT_NPY}")

    # 샘플 출력
    sample = results[0].copy()
    sample["embedding"] = f"[dim={len(results[0]['embedding'])}] {results[0]['embedding'][:3]}..."
    print("\n[첫 번째 항목 샘플]")
    print(json.dumps(sample, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
