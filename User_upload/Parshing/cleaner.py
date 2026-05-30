import re


def is_korean(text):
    return bool(re.search(r'[가-힣ᄀ-ᇿ㄰-㆏]', text))

def is_chinese_noise(text):
    has_chinese = bool(re.search(r'[一-鿿]', text))
    return has_chinese and not is_korean(text)

def is_fragment_noise(text):
    s = text.strip()
    if not s or is_korean(s):
        return False
    if s.startswith(('#', '|', '-', '*', '>')):
        return False
    if '@' in s or 'http' in s:
        return False
    if re.match(r'^[\d./\\_]+$', s):
        return True
    if len(s) <= 10 and re.match(r'^[a-zA-Z0-9\s./]+$', s):
        return True
    return False

def clean_markdown(raw_text: str) -> str:
    cleaned = []
    for line in raw_text.split('\n'):
        s = line.strip()
        if s == '<!-- image -->':
            continue
        if re.match(r'^/[_\\]', s):
            continue
        if is_chinese_noise(s):
            continue
        if is_fragment_noise(s):
            continue
        cleaned.append(line)
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(cleaned))
