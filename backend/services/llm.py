from __future__ import annotations
import os
import re
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


def _parse_json(text: str) -> dict:
    """응답 텍스트에서 JSON 추출 (마크다운 코드블록 포함 대응)"""
    if not text:
        return {}
    # ```json ... ``` 또는 ``` ... ``` 블록 추출
    m = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if m:
        text = m.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # { } 범위만 추출 재시도
        m2 = re.search(r'\{[\s\S]*\}', text)
        if m2:
            try:
                return json.loads(m2.group())
            except json.JSONDecodeError:
                pass
    return {}

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
    return _client


def _build_evidence_text(ev_chunks: list[dict], filename: str = '', max_chunks: int = 10) -> str:
    """증적 내용을 페이지/섹션 출처 정보와 함께 정리 (LLM 인용 가능 형식)"""
    parts = []
    for i, chunk in enumerate(ev_chunks[:max_chunks]):
        meta = chunk.get('metadata') or {}
        if isinstance(meta, str):
            meta = json.loads(meta)

        page       = meta.get('page_no', '')
        section    = meta.get('section', '') or ''
        subsection = meta.get('subsection', '') or ''

        # "Ⅰ. 개요 > 3. 방법론" 형태의 계층 섹션은 가장 구체적인 마지막 항목만 사용
        if ' > ' in section:
            section = section.split(' > ')[-1].strip()

        # subsection이 있으면 더 구체적이므로 우선 사용
        display_section = subsection if subsection else section

        # 출처 라벨 구성: 파일명 + 페이지 + 섹션
        src_parts = []
        if filename:
            src_parts.append(filename)
        if page:
            src_parts.append(f"p.{page}")
        if display_section:
            src_parts.append(f"「{display_section}」")

        src_label = ' · '.join(src_parts) if src_parts else f'내용 {i+1}'
        parts.append(f"[출처: {src_label}]\n{chunk['content']}")

    return '\n\n'.join(parts)


def summarize_file(
    control_id: str,
    control_name: str,
    evidence_chunks: list[dict],
    filename: str,
) -> dict:
    """
    단일 파일 내용 분석 — 판단 없음, 빠른 호출
    Returns: {description, confirmed, missing}
    """
    evidence_text = _build_evidence_text(evidence_chunks[:6], filename)

    prompt = f"""다음은 ISMS-P 인증 항목 "{control_id} {control_name}"에 제출된 증적 파일입니다.

파일명: {filename}

내용:
{evidence_text}

이 파일을 분석하여 아래 JSON 형식으로 응답하세요.

description: 이 파일이 어떤 문서인지 1~2문장 (문서 종류, 날짜/기간, 핵심 내용)
confirmed: 이 파일에서 확인할 수 있는 내용 2~4개 — 구체적으로 (날짜·이름·의결사항·페이지 등 명시, 각 항목 25자 이내)
missing: 이 항목 기준으로 이 파일 단독으로는 확인하기 어려운 부분 0~2개 (없으면 빈 배열, 20자 이내)

주의사항:
- 기술 용어 없이 쉽게 써주세요.
- missing은 이 파일이 "나쁘다"는 게 아니라 다른 파일로 보완될 수 있는 부분입니다.
- "~이 없음" 또는 "~이 포함되지 않음" 형태로 중립적으로 써주세요.
- ⚠️ "[ 이미지/서명 ]"은 서명란에 도장·직인·서명 이미지가 실제로 존재한다는 의미입니다.
  텍스트로 추출되지 않을 뿐이므로 "서명 없음"으로 판단하지 마세요. "서명(도장) 확인됨"으로 처리하세요.

{{
  "description": "...",
  "confirmed": ["항목1", "항목2", "항목3"],
  "missing": ["항목1"] 또는 []
}}"""

    response = _get_client().chat.completions.create(
        model=os.environ.get('OPENAI_MODEL', 'gpt-4o-mini'),
        messages=[
            {'role': 'system', 'content': (
                '당신은 친절한 ISMS-P 인증 전문가입니다. '
                '인증을 처음 준비하는 실무 담당자도 바로 이해할 수 있도록 '
                '쉽고 따뜻한 말투로 설명하세요. '
                '전문 용어는 반드시 괄호로 풀어 쓰고, 항상 한국어로 응답하세요.'
            )},
            {'role': 'user', 'content': prompt},
        ],
        response_format={'type': 'json_object'},
        max_completion_tokens=350,
        temperature=0.1,
    )
    _SIGNATURE_KEYWORDS = {'서명', '도장', '직인', '날인', '서명란', '날인란'}

    result = json.loads(response.choices[0].message.content)
    missing = [
        item for item in (result.get('missing') or [])
        if not any(kw in item for kw in _SIGNATURE_KEYWORDS)
    ]
    return {
        'description': result.get('description', ''),
        'confirmed':   result.get('confirmed') or [],
        'missing':     missing,
    }


def judge(
    control_id: str,
    control_name: str,
    required_elements: str,
    guide_similarity: float,
    keyword_similarity: float,
    top_guide_chunks: list[dict],
    all_guide_chunks: list[dict],
    evidence_chunks: list[dict],
    file_summaries: list[dict] | None = None,
) -> dict:
    """
    전체 증적을 종합하여 적합 여부 최종 판단

    Args:
        evidence_chunks: 모든 파일의 청크 합산
        file_summaries:  파일별 요약 [{'filename', 'summary'}]

    Returns:
        {is_compliant, judgment_reason, improvement}
    """
    full_guide_text = '\n'.join(
        f"[가이드 {i+1}]\n{c.get('청크 내용', '')}"
        for i, c in enumerate(all_guide_chunks)
    )

    top_match_text = '\n'.join(
        f"  - 관련도 {c['score']:.2f} | {c['guide_content']}"
        for c in top_guide_chunks
    )

    evidence_text = _build_evidence_text(evidence_chunks)

    # 제출 파일 목록
    file_count = len(file_summaries) if file_summaries else 1
    file_list_text = ''
    if file_summaries:
        file_list_text = f"\n{'═'*60}\n📁 제출된 증적 파일 {file_count}개\n{'═'*60}\n" + '\n'.join(
            f"  [{i+1}] {fs['filename']}\n      ▶ {fs.get('summary', '')}"
            for i, fs in enumerate(file_summaries)
        ) + '\n'

    # 유사도 점수 해석 (점수를 무시하지 않고 판단 근거로 적극 활용)
    guide_pass   = guide_similarity >= 0.75
    keyword_pass = keyword_similarity >= 0.75
    g_pct = f"{guide_similarity:.1%}"
    k_pct = f"{keyword_similarity:.1%}"

    if guide_pass and keyword_pass:
        sim_guide = (
            f"두 점수 모두 기준 충족 (가이드라인 {g_pct} ≥ 75%, 핵심 요소 {k_pct} ≥ 75%).\n"
            "증적이 이 항목을 충분히 다루고 있다는 강한 신호입니다. "
            "필수확인요소가 모두 확인되면 적합, 일부 미흡하면 부분 적합으로 판단하세요."
        )
    elif guide_pass and not keyword_pass:
        sim_guide = (
            f"가이드라인 부합도({g_pct})는 충족하나 핵심 요소 반영도({k_pct})가 기준(75%) 미달.\n"
            "증적 방향은 맞지만 필수확인요소 일부가 명확히 드러나지 않습니다. "
            "필수확인요소 중 미확인 항목이 있으면 부분 적합 또는 부적합으로 판단하세요."
        )
    elif not guide_pass and keyword_pass:
        sim_guide = (
            f"가이드라인 부합도({g_pct})가 기준(75%) 미달. 키워드는 있으나 내용이 부족합니다.\n"
            "증적이 이 항목의 실질적 이행을 입증하는지 엄격히 확인하세요. "
            "이행 실적(결과, 날짜, 담당자, 조치 내용)이 없으면 부적합이 원칙입니다."
        )
    else:
        sim_guide = (
            f"두 점수 모두 기준 미달 (가이드라인 {g_pct} < 75%, 핵심 요소 {k_pct} < 75%).\n"
            "증적이 이 항목을 다루고 있지 않을 가능성이 높습니다. "
            "특별히 명확한 이행 실적이 확인되지 않으면 부적합으로 판단하는 것이 원칙입니다."
        )

    prompt = f"""당신은 10년 경력의 ISMS-P 인증 전문 심사관입니다.
실제 인증 심사 현장에서 결함을 판단하는 기준으로 엄격하게 평가하세요.
담당자가 결과를 신뢰하고 실제 심사에 대비할 수 있도록 정확한 판단이 최우선입니다.

{'═'*60}
📋 심사 항목
{'═'*60}
항목번호: {control_id}
항목명  : {control_name}

{'═'*60}
📖 인증 가이드라인 (이 항목의 공식 심사 기준)
{'═'*60}
{full_guide_text}

{'═'*60}
✅ 필수확인요소 (반드시 증적에서 확인되어야 하는 항목)
{'═'*60}
{required_elements}
{file_list_text}
{'═'*60}
📄 제출된 증적 전체 내용
{'═'*60}
{evidence_text}

{'═'*60}
📊 유사도 분석 결과
{'═'*60}
● 가이드라인 부합도 : {g_pct}  (기준 75% 이상 → {'✅ 충족' if guide_pass else '⚠️ 기준 미달'})
  : 제출 증적이 이 항목의 가이드라인 내용과 얼마나 유사한지를 수치화한 것

● 핵심 요소 반영도 : {k_pct}  (기준 75% 이상 → {'✅ 충족' if keyword_pass else '⚠️ 기준 미달'})
  : 필수확인요소가 증적에 얼마나 잘 반영되어 있는지를 수치화한 것

📌 점수 해석 및 심사 방향:
{sim_guide}

가이드라인과 가장 관련 높은 증적 내용 (참고):
{top_match_text}

{'═'*60}
🎯 판정 기준 — ISMS-P 인증 가이드라인 기반
{'═'*60}
판정의 공식 근거는 위에 제시된 [인증 가이드라인]입니다.
[필수확인요소]는 가이드라인 이해와 점검 정확도를 높이기 위해 보완한 체크리스트로,
가이드라인 요건을 더 세밀하게 확인하는 데 활용하세요.

━━ STEP 1: 가이드라인이 이 항목에서 무엇을 요구하는지 파악하세요 ━━
가이드라인 텍스트를 읽고, 이 항목이 어떤 유형의 증적을 요구하는지 판단하세요.

[문서화·수립이 요건인 경우]
  → 정책서, 지침서, 조직도, 계획서 등이 증적
  예) "정책을 수립하여야 한다", "지정하여야 한다"

[이행·운영 실적이 요건인 경우]
  → 회의록, 점검 결과, 보고서, 처리 내역, 교육 이수 기록 등이 증적
  예) "수행하여야 한다", "점검하여야 한다", "보고하여야 한다"
  → 이 경우 계획서·정책서만으로는 이행을 입증할 수 없습니다 (ISMS-P 심사 원칙)

[두 가지 모두 요건인 경우]
  → 문서화 증적 + 이행 실적 증적이 모두 필요

━━ STEP 2: 가이드라인 요건과 증적을 대조하여 판정하세요 ━━

✅ 적합
  - 가이드라인이 요구하는 내용이 제출 증적에서 모두 명확하게 확인됨
  - 필수확인요소 체크리스트도 충족됨

⚠️ 부분 적합
  - 가이드라인의 핵심 요건은 증적으로 입증되었으나
    일부 세부 사항(날짜 불명확, 버전 미기재, 담당자 누락 등)이 보완되면 더 완전해지는 경우
  - 현재 증적으로 심사 통과 가능성은 있으나 심사관이 추가 자료를 요청할 수 있는 경우

❌ 부적합
  - 가이드라인이 요구하는 핵심 내용이 제출 증적에서 확인되지 않는 경우
  - 이행 실적이 요건인 항목에 계획서·정책서만 제출된 경우
  - 제출 문서가 이 항목의 가이드라인 요건과 실질적 관련이 없는 경우

━━ 유사도 점수의 역할 ━━
가이드라인 부합도 점수는 증적이 가이드라인과 얼마나 유사한지를 수치화한 참고 지표입니다.
ISMS-P 공식 기준이 아니므로 판정의 절대 기준으로 사용하지 마세요.
- 75% 이상: 증적이 가이드라인 내용을 잘 다루고 있을 가능성 높음
- 60~75%: 부분 적합 가능성 — 핵심 요건 충족 여부를 꼼꼼히 확인
- 60% 미만: 증적이 가이드라인과 맞지 않을 수 있음 → 부적합 검토
- 점수와 무관하게, 가이드라인 요건 충족 여부가 최종 판정 기준

{'═'*60}
🔍 심사 원칙
{'═'*60}
1. 판정 근거는 항상 "필수확인요소 X가 Y 증적에서 확인됨/미확인됨"으로 작성하세요.
2. 전체 증적 세트를 함께 평가하되, 각 파일이 어떤 필수확인요소를 입증하는지 명확히 하세요.
3. ⚠️ "[ 이미지/서명 ]"은 도장·직인이 실제 존재한다는 표시입니다. "서명 없음"으로 판단하지 마세요.
4. 판단 근거에 "청크", "내용 번호" 같은 기술 용어는 절대 쓰지 마세요.

{'═'*60}
📝 출력 형식
{'═'*60}
아래 JSON 형식으로만 응답하세요.

judgment_reason 작성 형식 (반드시 준수, 충분히 길고 상세하게 작성):
- 단락 구분: \\n\\n
- 각 단락은 **라벨:** 으로 시작
- 모든 단락을 빠짐없이 작성하세요

━━━ 적합인 경우 ━━━
judgment_reason:
**판정:** 적합입니다. [왜 적합인지 2~3문장으로 친절하게 — 어떤 증적이 어떤 요건을 잘 입증했는지 구체적으로]

**가이드라인 요건 분석:**
이 항목은 [가이드라인이 요구하는 내용을 2~3문장으로 쉽게 풀어서 설명].

**필수확인요소 검토:**
- [필수확인요소 1]: ✅ 확인됨 — 「파일명 · p.X · 섹션명」에서 [구체적으로 어떤 내용이 확인되었는지]
- [필수확인요소 2]: ✅ 확인됨 — 「파일명 · p.X · 섹션명」에서 [구체적 내용]
(필수확인요소마다 하나씩 작성)

**증적 파일별 분석:**
- 「파일명1」: [이 파일에서 이 항목과 관련하여 확인된 내용을 2~3문장으로 구체적으로]
- 「파일명2」: [이 파일에서 확인된 내용]
(제출된 파일마다 하나씩 작성)

**종합 의견:**
[전반적으로 잘 준비된 점을 칭찬하고, 향후 심사 시 유의할 점이 있으면 친절하게 안내. 2~3문장]

action_items: [] (빈 배열)

━━━ 부분 적합인 경우 ━━━
judgment_reason:
**판정:** 부분 적합입니다. [핵심 요건은 어느 정도 충족되어 있고, 어떤 부분이 보완되면 더 완전해지는지 2~3문장으로 친절하게]

**가이드라인 요건 분석:**
이 항목은 [가이드라인이 요구하는 내용을 2~3문장으로 쉽게 풀어서 설명].

**필수확인요소 검토:**
- [필수확인요소 1]: ✅ 확인됨 — 「파일명 · p.X · 섹션명」에서 [구체적 내용]
- [필수확인요소 2]: ⚠️ 일부 미흡 — [어떤 내용이 불명확하거나 부족한지 구체적으로]
- [필수확인요소 3]: ❌ 미확인 — [해당 내용이 왜 확인되지 않는지]
(필수확인요소마다 하나씩 작성)

**증적 파일별 분석:**
- 「파일명1」: [이 파일에서 확인된 내용과 부족한 부분을 2~3문장으로 구체적으로]
- 「파일명2」: [분석 내용]
(제출된 파일마다 하나씩 작성)

**종합 의견:**
[현재 상태를 친절하게 정리하고, 어떤 보완이 이루어지면 확실하게 통과할 수 있는지 구체적으로 안내. 2~3문장]

action_items: (1~3개, type은 모두 "권고")
각 항목: title(짧고 명확하게), description(왜 필요한지 + 추가하면 어떤 효과가 있는지, 3~4문장 친절하게), example(구체적인 문서·서식 예시)

━━━ 부적합인 경우 ━━━
judgment_reason:
**판정:** 부적합입니다. [어떤 핵심 요건이 충족되지 않았는지 2~3문장으로 친절하게 — 담당자가 낙담하지 않도록 보완 가능하다는 희망도 함께]

**가이드라인 요건 분석:**
이 항목은 [가이드라인이 요구하는 내용을 2~3문장으로 쉽게 풀어서 설명].

**필수확인요소 검토:**
- [필수확인요소 1]: ✅ 확인됨 — 「파일명 · p.X · 섹션명」에서 [구체적 내용] (있다면)
- [필수확인요소 2]: ❌ 미확인 — [왜 확인되지 않는지, 어떤 증적이 있어야 하는지]
- [필수확인요소 3]: ❌ 미확인 — [상세 설명]
(필수확인요소마다 하나씩 작성)

**증적 파일별 분석:**
- 「파일명1」: [이 파일이 이 항목과 어떤 관련이 있고 어떤 부분이 부족한지 2~3문장으로]
- 「파일명2」: [분석 내용]
(제출된 파일마다 하나씩 작성)

**종합 의견:**
[부족한 이유를 명확히 하고, 어떤 증적을 추가하면 재심사 시 통과할 수 있는지 구체적이고 희망적으로 안내. 2~3문장]

action_items: (필수 항목 먼저 type: "필수", 보완 권고 type: "권고" 순서, 총 2~4개)
각 항목: title(짧고 명확하게), description(왜 필요한지 + 어떻게 준비하면 되는지, 3~4문장 친절하게), example(구체적인 문서·서식 예시)
━━━━━━━━━━━━

주의사항:
- 전문 용어는 반드시 괄호로 설명. 예: CISO(정보보호 최고책임자)
- 핵심 요소 반영도 수치는 절대 언급하지 마세요.
- 담당자가 읽고 바로 행동할 수 있도록 구체적이고 친절하게 작성하세요.
- judgment_reason은 반드시 모든 단락을 포함하여 충분히 길게 작성하세요.

{{
  "verdict": "적합"(75% 이상) 또는 "부분 적합"(60~75%) 또는 "부적합"(60% 미만),
  "judgment_reason": "**판정:** 내용\\n\\n**근거:**\\n설명\\n- 출처: 내용\\n→ 결론",
  "improvement": "부적합인 경우만: 어떤 요구사항이 미충족인지 + 어떤 문서를 추가하면 되는지. 적합·부분 적합이면 null",
  "action_items": [
    {{
      "type": "필수" 또는 "권고",
      "title": "보완 항목명 (15자 이내)",
      "description": "왜 필요한지 + 추가하면 어떤 효과가 있는지 (2~3문장, 친절하게)",
      "example": "구체적인 문서·서식 예시 (예: 인사발령 통보서, 임명장 등)"
    }}
  ]
}}"""

    response = _get_client().chat.completions.create(
        model=os.environ.get('OPENAI_MODEL', 'gpt-4o-mini'),
        messages=[
            {
                'role': 'system',
                'content': (
                    '당신은 10년 경력의 ISMS-P 인증 전문가이자 친절한 컨설턴트입니다. '
                    '인증을 처음 준비하는 실무 담당자도 결과를 읽고 바로 이해하고 행동할 수 있도록 '
                    '따뜻하고 구체적인 말투로 설명하세요. '
                    '잘된 점은 칭찬하고, 부족한 점은 "이렇게 하면 더 좋아요"처럼 방향을 제시하세요. '
                    '판단 근거는 반드시 가이드라인 요건 + 증적 출처(파일명·페이지·섹션)를 인용하여 '
                    '충분히 길고 상세하게 작성하세요. '
                    '전문 용어는 괄호로 풀어 쓰고(예: CISO(정보보호 최고책임자)), '
                    '항상 한국어로 응답하며, 반드시 유효한 JSON 형식으로만 출력하세요. '
                    '판단 근거는 반드시 \\n\\n 으로 단락을 구분하세요.'
                ),
            },
            {'role': 'user', 'content': prompt},
        ],
        response_format={'type': 'json_object'},
        max_completion_tokens=2000,
        temperature=0.2,
    )

    raw = json.loads(response.choices[0].message.content)
    verdict = raw.get('verdict', '')
    if verdict not in ('적합', '부분 적합', '부적합'):
        verdict = '적합' if raw.get('is_compliant', False) else '부적합'
    return {
        'verdict':          verdict,
        'is_compliant':     verdict != '부적합',
        'judgment_reason':  raw.get('judgment_reason', ''),
        'improvement':      raw.get('improvement'),
        'action_items':     raw.get('action_items') or [],
    }
