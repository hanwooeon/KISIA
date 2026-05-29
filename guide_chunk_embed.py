import json
import numpy as np
from sentence_transformers import SentenceTransformer

INPUT_PATH = r"d:\code\KISIA\chunk_with_meta.json"
OUTPUT_JSON = r"d:\code\KISIA\guide_chunk_embed.json"
OUTPUT_NPY = r"d:\code\KISIA\guide_chunk_embed.npy"

MODEL_NAME = "BAAI/bge-m3"


def get_content(chunk):
    field = chunk["metadata"]["청크유형"]
    return chunk.get(field, "")


def main():
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    print(f"총 청크 수: {len(chunks)}")
    print("BGE-M3 모델 로드 중...")
    model = SentenceTransformer(MODEL_NAME)

    ids = [chunk["guide_chunk_id"] for chunk in chunks]
    texts = [get_content(chunk) for chunk in chunks]

    print("임베딩 생성 중...")
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)

    np.save(OUTPUT_NPY, vectors)
    print(f"NPY 저장 완료: {OUTPUT_NPY}")

    results = []
    for chunk, vector in zip(chunks, vectors):
        results.append({
            "guide_chunk_id": chunk["guide_chunk_id"],
            "항목번호": chunk["metadata"]["항목번호"],
            "청크유형": chunk["metadata"]["청크유형"],
            "embedding": vector.tolist(),
        })

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"JSON 저장 완료: {OUTPUT_JSON}")

    print(f"\n[샘플] {results[0]['guide_chunk_id']} ({results[0]['청크유형']})")
    print(f"벡터 차원: {len(results[0]['embedding'])}")


if __name__ == "__main__":
    main()
