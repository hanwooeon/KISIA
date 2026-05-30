import fitz
import re
import json

PDF_PATH = r"d:\code\KISIA\ISMS-P 항목 내용.pdf"
OUTPUT_PATH = r"d:\code\KISIA\parsing_pdf.json"

VALID_항목번호 = {
    "1.1.1", "1.1.2", "1.1.3", "1.1.4", "1.1.5",
    "1.2.1", "1.3.3", "1.4.2",
    "2.2.3", "2.2.4", "2.3.2",
    "2.4.1", "2.4.3", "2.4.6", "2.4.7",
    "2.5.1", "2.5.2", "2.5.3", "2.5.4",
    "2.6.1", "2.6.2", "2.6.6", "2.6.7",
    "2.7.1",
    "2.8.1", "2.8.3", "2.8.4", "2.8.5",
    "2.9.1", "2.9.3", "2.9.4",
    "2.10.1", "2.10.2", "2.10.3", "2.10.6", "2.10.7", "2.10.8", "2.10.9",
    "2.11.1", "2.11.2", "2.11.5",
    "3.1.1", "3.1.2", "3.1.3", "3.1.4", "3.1.5", "3.1.6", "3.1.7",
    "3.2.1", "3.2.2", "3.2.3", "3.2.4", "3.2.5",
    "3.3.1", "3.3.2", "3.3.3", "3.3.4",
    "3.4.1", "3.4.2",
    "3.5.1", "3.5.2", "3.5.3",
}

PAGE_MARKER_RE = re.compile(r'<<<PAGE:(\d+)>>>')


def get_doc_page_num(page):
    page_height = page.rect.height
    page_width = page.rect.width
    for block in page.get_text("blocks"):
        x0, y0, x1, y1, text, *_ = block
        text_stripped = text.strip()
        if (re.match(r'^\d+$', text_stripped)
                and y0 > page_height * 0.85
                and x0 > page_width * 0.35
                and x1 < page_width * 0.65):
            return int(text_stripped)
    return None


def build_item_page_map(path):
    """항목번호 → 시작 페이지 번호 매핑 (항  목 헤더가 나타나는 페이지 기준)"""
    doc = fitz.open(path)
    item_page_map = {}

    for page in doc:
        doc_page_num = get_doc_page_num(page)
        if doc_page_num is None:
            continue
        page_text = page.get_text()
        # 이 페이지에서 "항  목\n1.1.1 ..." 패턴 탐색
        for m in re.finditer(r'항\s{1,5}목\s*\n\s*(\d+\.\d+\.\d+)', page_text):
            item_num = m.group(1)
            if item_num not in item_page_map:
                item_page_map[item_num] = str(doc_page_num)

    doc.close()
    return item_page_map


def extract_raw_text(path):
    doc = fitz.open(path)
    pages = [page.get_text() for page in doc]
    doc.close()
    return "\n".join(pages)


def remove_artifacts(text):
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        stripped = line.strip()

        # 페이지 마커는 보존
        if PAGE_MARKER_RE.match(stripped):
            cleaned.append(line)
            continue
        # 페이지 번호 단독 줄 스킵
        if re.match(r'^\d+$', stripped):
            continue
        # 사이드바 세로 텍스트: 1글자 한글 줄 스킵
        if len(stripped) <= 1 and re.match(r'^[가-힣 ]*$', stripped):
            continue
        # 알려진 헤더/푸터 패턴 스킵
        if re.match(r'^정보보호 및 개인정보보호 관리체계 인증제도 안내서', stripped):
            continue
        if re.match(r'^제\d+장\s+', stripped):
            continue

        cleaned.append(line)

    return '\n'.join(cleaned)


def split_into_items(text):
    # "항  목" 기준으로 분리, 각 블록 앞의 PAGE 마커도 함께 유지
    parts = re.split(r'항\s{1,5}목\s*\n', text)
    return [p.strip() for p in parts if p.strip()]


def extract_item_header(text):
    match = re.match(r'^(\d+\.\d+\.\d+)\s+(.*?)$', text, re.MULTILINE)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return "", ""


FIELD_MARKERS = [
    ("인증기준",      re.compile(r'^\s*인증\s*기준\s*$', re.MULTILINE)),
    ("주요 확인사항", re.compile(r'^\s*주요\s*확인\s*사항\s*$', re.MULTILINE)),
    ("관련 법규",     re.compile(r'^\s*관련\s*법규\s*$', re.MULTILINE)),
    ("세부 설명",     re.compile(r'^\s*세부\s*설명\s*$', re.MULTILINE)),
    ("증거자료 예시", re.compile(r'^\s*증거\s*자료\s*\n\s*예시\s*$', re.MULTILINE)),
    ("결함사례",      re.compile(r'^\s*결함\s*사례\s*$', re.MULTILINE)),
]


def extract_fields(item_text):
    clean = item_text

    found = []
    for name, pattern in FIELD_MARKERS:
        match = pattern.search(clean)
        if match:
            found.append((match.start(), match.end(), name))

    found.sort(key=lambda x: x[0])

    fields = {}
    for i, (start, end, name) in enumerate(found):
        next_start = found[i + 1][0] if i + 1 < len(found) else len(clean)
        content = clean[end:next_start].strip()
        fields[name] = content

    return fields


def to_list(text, field_name):
    if not text:
        return []

    if field_name == "결함사례":
        parts = re.split(r'사례\s*\d+\s*[:：]\s*', text)
        return [p.strip() for p in parts if p.strip()]

    if field_name == "주요 확인사항":
        items = re.split(r'(?<=\?)\s*\n', text)
        return [item.strip() for item in items if item.strip()]

    if field_name in ("관련 법규", "증거자료 예시"):
        return [line.strip() for line in text.split('\n') if line.strip()]

    if field_name == "세부 설명":
        parts = re.split(r'(?=▶)', text)
        return [p.strip() for p in parts if p.strip()]

    return [text.strip()]


def parse_item(item_text, item_page_map):
    번호, 항목명 = extract_item_header(item_text)
    if not 번호:
        return None

    page = item_page_map.get(번호)
    fields = extract_fields(item_text)

    return {
        "항목번호": 번호,
        "항목명": 항목명,
        "페이지": page,
        "인증기준": fields.get("인증기준", "").strip(),
        "주요 확인사항": to_list(fields.get("주요 확인사항", ""), "주요 확인사항"),
        "관련 법규": to_list(fields.get("관련 법규", ""), "관련 법규"),
        "세부 설명": to_list(fields.get("세부 설명", ""), "세부 설명"),
        "증거자료 예시": to_list(fields.get("증거자료 예시", ""), "증거자료 예시"),
        "결함사례": to_list(fields.get("결함사례", ""), "결함사례"),
    }


def main():
    print("PDF 파싱 중...")
    item_page_map = build_item_page_map(PDF_PATH)
    print(f"페이지 매핑된 항목 수: {len(item_page_map)}")

    raw = extract_raw_text(PDF_PATH)
    cleaned = remove_artifacts(raw)
    items_raw = split_into_items(cleaned)
    print(f"인식된 항목 블록 수: {len(items_raw)}")

    results = []
    for item_text in items_raw:
        parsed = parse_item(item_text, item_page_map)
        if parsed and parsed["항목번호"] in VALID_항목번호:
            results.append(parsed)

    print(f"파싱된 항목 수: {len(results)}")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"저장 완료: {OUTPUT_PATH}")

    if results:
        print("\n[첫 번째 항목 샘플]")
        print(json.dumps(results[0], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
