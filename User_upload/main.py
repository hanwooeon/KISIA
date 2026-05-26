import os
os.environ.setdefault('KMP_DUPLICATE_LIB_OK', 'TRUE')

from pathlib import Path
from Parshing.parser import parse_file
from Parshing.cleaner import clean_markdown
from Chunking.chunker import chunk_markdown, save_chunks


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
raw = parse_file(str(pdf_path))
print("파싱 완료")

print("정제 중 ...")
cleaned = clean_markdown(raw)

md_path = unique_path(pdf_path.parent / f"{pdf_path.stem}.md")
md_path.write_text(cleaned, encoding="utf-8")
print(f"마크다운 저장 완료 → {md_path}")

print("청킹 중 ...")
chunks = chunk_markdown(cleaned, source=filename)

output_path = unique_path(pdf_path.parent / f"{pdf_path.stem}_chunks.json")
save_chunks(chunks, str(output_path))

print(f"청킹 완료: {len(chunks)}개 청크")
print(f"저장 완료 → {output_path}")
