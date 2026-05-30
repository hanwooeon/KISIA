from __future__ import annotations
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

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
    guide_pass   = guide_similarity >= 0.70
    keyword_pass = keyword_similarity >= 0.65
    g_pct = f"{guide_similarity:.1%}"
    k_pct = f"{keyword_similarity:.1%}"

    if guide_pass and keyword_pass:
        sim_guide = (
            f"두 점수가 모두 기준을 충족합니다 (가이드라인 {g_pct} ≥ 70%, 핵심 요소 {k_pct} ≥ 65%).\n"
            "증적이 이 항목의 기준을 잘 다루고 있다는 강한 신호입니다. "
            "필수확인요소가 내용에서 확인되면 적합으로 판단하세요."
        )
    elif guide_pass and not keyword_pass:
        sim_guide = (
            f"가이드라인 부합도({g_pct})는 기준을 넘지만, 핵심 요소 반영도({k_pct})가 기준(65%)에 미달합니다.\n"
            "증적의 전반적인 방향은 맞지만, 필수확인요소 중 일부가 증적에 명확히 드러나지 않을 수 있습니다. "
            "아래 필수확인요소 각각이 증적에서 구체적으로 확인되는지 꼼꼼히 점검하세요."
        )
    elif not guide_pass and keyword_pass:
        sim_guide = (
            f"핵심 요소 반영도({k_pct})는 기준을 충족하지만, 가이드라인 부합도({g_pct})가 기준(70%)에 미달합니다.\n"
            "필수 키워드는 포함되어 있으나 증적의 전반적인 내용이 가이드라인과 충분히 일치하지 않을 수 있습니다. "
            "증적이 이 항목의 실질적 이행을 증명하는지 내용 기반으로 판단하세요."
        )
    else:
        sim_guide = (
            f"두 점수 모두 기준에 미달합니다 (가이드라인 {g_pct} < 70%, 핵심 요소 {k_pct} < 65%).\n"
            "증적이 이 항목을 충분히 다루고 있지 않을 가능성이 높습니다. "
            "단, 여러 파일이 함께 제출된 경우 각각의 내용을 종합하면 요건을 충족할 수도 있으니, "
            "증적 전체를 하나의 세트로 보고 실질적 이행 여부를 확인하세요."
        )

    prompt = f"""당신은 ISMS-P(정보보호 및 개인정보보호 관리체계) 인증 전문 심사관입니다.
인증 담당자가 쉽게 이해할 수 있도록, 쉽고 명확한 한국어로 최종 판단을 작성해주세요.

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
● 가이드라인 부합도 : {g_pct}  (기준 70% 이상 → {'✅ 충족' if guide_pass else '⚠️ 기준 미달'})
  : 제출 증적이 이 항목의 가이드라인 내용과 얼마나 유사한지를 수치화한 것

● 핵심 요소 반영도 : {k_pct}  (기준 65% 이상 → {'✅ 충족' if keyword_pass else '⚠️ 기준 미달'})
  : 필수확인요소가 증적에 얼마나 잘 반영되어 있는지를 수치화한 것

📌 점수 해석 및 심사 방향:
{sim_guide}

가이드라인과 가장 관련 높은 증적 내용 (참고):
{top_match_text}

{'═'*60}
🎯 3단계 판정 기준 (반드시 이 기준으로 판정)
{'═'*60}
✅ 적합    : 필수확인요소가 제출 증적에서 모두 명확하게 확인됨
⚠️ 조건부 적합: 핵심 필수확인요소는 확인되나, 보완하면 심사 리스크를 낮출 수 있는 부분이 있음
             예) 지정문서 있으나 임명일자 없음 / 역할 정의되었으나 서명·직인 없음 / 날짜·버전 불명확
❌ 부적합   : 핵심 필수확인요소 중 하나 이상이 증적에서 확인되지 않음

{'═'*60}
🔍 심사 원칙
{'═'*60}
1. 개별 파일이 아닌 제출된 전체 증적 세트를 함께 평가하세요.
2. 유사도 점수는 참고 지표입니다. 실질적 이행 증거가 있으면 낮은 점수도 적합 가능합니다.
3. 날짜·기간·서명·담당자 등 구체적인 이행 증거를 확인하세요.
4. ⚠️ "[ 이미지/서명 ]"은 도장·직인이 실제 존재한다는 표시입니다. "서명 없음"으로 판단하지 마세요.
5. 판단 근거에 "청크", "내용 번호" 같은 기술 용어는 절대 쓰지 마세요.

{'═'*60}
📝 출력 형식
{'═'*60}
아래 JSON 형식으로만 응답하세요.

judgment_reason 작성 형식 (반드시 준수):
- 단락 구분: \\n\\n
- 각 단락은 **라벨:** 으로 시작
- **근거:** 단락은 반드시 하나만 작성

━━━ 적합인 경우 ━━━
judgment_reason:
**판정:** 적합입니다. 가이드라인 부합도 X%로 기준(70%)을 충족합니다. [이유 1문장]

**근거:**
이 항목은 [가이드라인 요구사항을 쉬운 말로 1문장 설명]합니다.
- 「파일명 · p.X · 섹션명」: [확인된 구체적 내용]
→ [종합 결론 1문장]

action_items: [] (빈 배열)

━━━ 조건부 적합인 경우 ━━━
judgment_reason:
**판정:** 조건부 적합입니다. 핵심 요건은 확인되나 보완하면 더 확실하게 통과할 수 있습니다.

**근거:**
이 항목은 [가이드라인 요구사항]합니다.
- 「파일명 · p.X · 섹션명」: [확인된 내용]
→ [현재 상태 요약 — 무엇이 확인되고 무엇이 아직 부족한지]

action_items: (1~3개, type은 모두 "권고")
각 항목: title(짧고 명확하게), description(왜 필요한지 + 추가하면 어떤 효과가 있는지), example(구체적인 문서 예시)

━━━ 부적합인 경우 ━━━
judgment_reason:
**판정:** 부적합입니다. [핵심 필수확인요소 중 무엇이 없는지 1문장]

**근거:**
이 항목은 [가이드라인 요구사항]을 요구합니다.
- 「파일명 · p.X · 섹션명」: [확인된 내용 또는 "해당 내용 미확인"]
→ [무엇이 부족한지 1문장]

action_items: (필수 항목 먼저, type: "필수" → 보완 권고 type: "권고" 순서)
━━━━━━━━━━━━

주의사항:
- 전문 용어는 괄호로 설명. 예: CISO(정보보호 최고책임자)
- 핵심 요소 반영도는 절대 언급하지 마세요.

{{
  "verdict": "적합" 또는 "조건부 적합" 또는 "부적합",
  "judgment_reason": "**판정:** 내용\\n\\n**근거:**\\n설명\\n- 출처: 내용\\n→ 결론",
  "improvement": "부적합인 경우만: 어떤 요구사항이 미충족인지 + 어떤 문서를 추가하면 되는지. 적합·조건부 적합이면 null",
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
                    '당신은 ISMS-P 인증 보조 점검 도구의 심사 엔진입니다. '
                    '가이드라인 요구사항과 증적 내용을 대조하여 근거 중심으로 판단하세요. '
                    '판단 근거는 가이드라인 인용 + 증적 출처(파일명·페이지·섹션) 형식으로 구체적으로 작성하세요. '
                    '전문 용어는 반드시 괄호로 풀어 쓰고(예: CISO(정보보호 최고책임자)), '
                    '인증을 처음 준비하는 담당자도 이해할 수 있는 명확한 언어를 사용하세요. '
                    '항상 한국어로 응답하며, 반드시 유효한 JSON 형식으로만 출력하세요. '
                    '판단 근거는 반드시 \\n\\n 으로 단락을 구분하세요.'
                ),
            },
            {'role': 'user', 'content': prompt},
        ],
        response_format={'type': 'json_object'},
        temperature=0.2,
    )

    raw = json.loads(response.choices[0].message.content)
    verdict = raw.get('verdict', '')
    if verdict not in ('적합', '조건부 적합', '부적합'):
        verdict = '적합' if raw.get('is_compliant', False) else '부적합'
    return {
        'verdict':          verdict,
        'is_compliant':     verdict != '부적합',
        'judgment_reason':  raw.get('judgment_reason', ''),
        'improvement':      raw.get('improvement'),
        'action_items':     raw.get('action_items') or [],
    }
