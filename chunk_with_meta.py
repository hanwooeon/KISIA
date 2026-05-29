import json

INPUT_PATH = r"d:\code\KISIA\parsing_pdf.json"
OUTPUT_PATH = r"d:\code\KISIA\chunk_with_meta.json"

CHUNK_FIELDS = [
    "인증기준",
    "주요 확인사항",
    "관련 법규",
    "세부 설명",
    "증거자료 예시",
    "결함사례",
]


def make_content(value):
    if isinstance(value, list):
        return "\n".join(v for v in value if v)
    return value or ""


def chunk_item(item, chunk_id_start):
    chunks = []
    chunk_id = chunk_id_start

    for field in CHUNK_FIELDS:
        value = item.get(field)
        content = make_content(value)
        if not content.strip():
            continue

        chunks.append({
            "guide_chunk_id": f"guide_chunk_{chunk_id:04d}",
            "metadata": {
                "항목번호": item.get("항목번호", ""),
                "항목명": item.get("항목명", ""),
                "페이지": item.get("페이지"),
                "청크유형": field,
            },
            field: content,
        })
        chunk_id += 1

    return chunks, chunk_id


def main():
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        items = json.load(f)

    all_chunks = []
    chunk_id = 1

    for item in items:
        chunks, chunk_id = chunk_item(item, chunk_id)
        all_chunks.extend(chunks)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    print(f"총 청크 수: {len(all_chunks)}")
    print(f"저장 완료: {OUTPUT_PATH}")

    if all_chunks:
        print("\n[첫 번째 청크 샘플]")
        print(json.dumps(all_chunks[0], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
