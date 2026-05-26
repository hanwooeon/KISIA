from pathlib import Path
from Parshing.parser import parse_file
from Parshing.cleaner import clean_markdown


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

output_path = pdf_path.parent / f"{pdf_path.stem}.md"
output_path.write_text(cleaned, encoding='utf-8')
print(f"저장 완료 → {output_path}")
