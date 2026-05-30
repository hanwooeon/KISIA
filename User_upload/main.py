import os
os.environ.setdefault('KMP_DUPLICATE_LIB_OK', 'TRUE')

from pathlib import Path
from Parshing.parser import parse_file
from Parshing.cleaner import clean_markdown
from Chunking.chunker import chunk_markdown, save_chunks
from Embedding.embedder import embed_texts
from DB.uploader import upload_chunks, to_export_rows


def unique_path(base: Path) -> Path:
    if not base.exists():
        return base
    stem = base.stem
    suffix = base.suffix
    parent = base.parent
    counter = 1
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


folder = input("폴더 경로 입력하세요: ").strip()
filename = input("파일명 입력하세요: ").strip()

pdf_path = Path(folder) / filename

if not pdf_path.exists():
    print(f"오류: '{pdf_path}' 파일을 찾을 수 없습니다.")
    exit(1)

print(f"파싱 중: {pdf_path.name} ...")
raw, elements = parse_file(str(pdf_path))
print(f"파싱 완료 (Docling 요소 {len(elements)}개 추출)")

print("정제 중 ...")
cleaned = clean_markdown(raw)

md_path = unique_path(pdf_path.parent / f"{pdf_path.stem}.md")
md_path.write_text(cleaned, encoding="utf-8")
print(f"마크다운 저장 완료 → {md_path}")

print("청킹 중 ...")
chunks = chunk_markdown(cleaned, source=filename, elements=elements)

output_path = unique_path(pdf_path.parent / f"{pdf_path.stem}_chunks.json")
save_chunks(chunks, str(output_path))
print(f"청킹 완료: {len(chunks)}개 청크 → {output_path}")

print("임베딩 중 ...")
contents = [c['content'] for c in chunks]
embeddings = embed_texts(contents)
print("임베딩 완료")

for chunk, emb in zip(chunks, embeddings):
    chunk['embedding'] = emb

print("DB 업로드 중 ...")
assigned_no = upload_chunks(chunks)
print(f"업로드 완료: {len(chunks)}개 청크 → Supabase (inspection_no={assigned_no})")

full_path = unique_path(pdf_path.parent / f"{pdf_path.stem}_full.json")
rows = [{k: v for k, v in row.items() if k != 'embedding'} for row in to_export_rows(chunks, assigned_no)]
save_chunks(rows, str(full_path))
print(f"전체 데이터 저장 완료 (메타데이터, 임베딩 제외) → {full_path}")
