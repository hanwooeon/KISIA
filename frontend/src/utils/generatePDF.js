import html2pdf from 'html2pdf.js'

// ── 유틸 ─────────────────────────────────────────────────────────
function pct(v) { return (v * 100).toFixed(1) + '%' }

const VERDICT_STYLE = {
  '적합':      { text: '#065F46', bg: '#ECFDF5', border: '#6EE7B7', label: '적합' },
  '부분 적합': { text: '#92400E', bg: '#FFFBEB', border: '#FCD34D', label: '부분 적합' },
  '부적합':    { text: '#991B1B', bg: '#FEF2F2', border: '#FCA5A5', label: '부적합' },
}

function getVerdict(r) {
  if (r.verdict) return r.verdict
  if (r.overall?.verdict) return r.overall.verdict
  return r.is_compliant ? '적합' : '부적합'
}

// ── judgment_reason 파싱: **라벨:** 블록 → { label, lines[] } ────
function parseReason(text) {
  if (!text) return []
  const blocks = []
  const paragraphs = text.split('\n\n').filter(Boolean)
  for (const para of paragraphs) {
    const m = para.match(/^\*\*(.+?):\*\*\s*([\s\S]*)$/)
    if (m) {
      blocks.push({ label: m[1].trim(), lines: m[2].trim().split('\n').filter(Boolean) })
    } else {
      blocks.push({ label: null, lines: para.split('\n').filter(Boolean) })
    }
  }
  return blocks
}

// 근거 블록의 bullet/arrow 한 줄 → HTML
function lineHtml(line) {
  if (line.startsWith('- ')) {
    return `<div style="display:flex;gap:7px;margin:4px 0;">
      <span style="color:#374151;flex-shrink:0;margin-top:2px;">•</span>
      <span style="font-size:10.5px;color:#374151;line-height:1.7;">${line.slice(2)}</span>
    </div>`
  }
  if (line.startsWith('→ ')) {
    return `<div style="margin:8px 0;padding:8px 12px;background:#F0F4FF;border-left:3px solid #4F46E5;border-radius:0 5px 5px 0;font-size:10.5px;color:#1E293B;font-weight:600;line-height:1.6;">${line.slice(2)}</div>`
  }
  return `<p style="font-size:10.5px;color:#374151;line-height:1.75;margin:4px 0;">${line}</p>`
}

// ── 항목 상세 카드 HTML ──────────────────────────────────────────
function itemDetailHtml(r, index) {
  const verdict  = getVerdict(r)
  const vs       = VERDICT_STYLE[verdict] || VERDICT_STYLE['부적합']
  const gPct     = (r.guide_similarity * 100).toFixed(1)
  const gPass    = r.guide_similarity >= 0.7
  const blocks   = parseReason(r.judgment_reason)
  const actionItems = r.action_items || r.overall?.action_items || []

  // 블록별 섹션 추출
  const verdictBlock = blocks.find(b => b.label === '판정')
  const reasonBlock  = blocks.find(b => b.label === '근거')
  const otherBlocks  = blocks.filter(b => b.label !== '판정' && b.label !== '근거' && b.label !== null)

  // 점검 결과 본문: 근거 블록의 첫 줄(설명문)과 bullet 분리
  let reasonIntro = ''
  let reasonBullets = []
  let reasonConclusion = ''
  if (reasonBlock) {
    for (const line of reasonBlock.lines) {
      if (line.startsWith('- ')) reasonBullets.push(line.slice(2))
      else if (line.startsWith('→ ')) reasonConclusion = line.slice(2)
      else if (!reasonBullets.length) reasonIntro += line + ' '
    }
  }

  return `
  <div style="margin-bottom:32px;page-break-inside:avoid;">

    <!-- 항목 헤더 바 -->
    <div style="background:#0F172A;padding:12px 18px;border-radius:6px 6px 0 0;display:flex;justify-content:space-between;align-items:center;">
      <div style="display:flex;align-items:center;gap:10px;">
        <span style="background:white;color:#0F172A;font-size:10px;font-weight:900;padding:3px 10px;border-radius:4px;">${r.control_id}</span>
        <span style="color:white;font-size:13px;font-weight:700;letter-spacing:-0.3px;">${r.control_name}</span>
        ${r.category ? `<span style="color:#94A3B8;font-size:10px;border:1px solid #334155;padding:2px 8px;border-radius:12px;">${r.category}</span>` : ''}
      </div>
      <span style="font-size:11px;font-weight:800;padding:4px 14px;border-radius:20px;background:${vs.bg};color:${vs.text};border:1px solid ${vs.border};">${verdict}</span>
    </div>

    <!-- 카드 본문 -->
    <div style="border:1px solid #E2E8F0;border-top:none;border-radius:0 0 6px 6px;padding:20px 22px;">

      <!-- 증적 파일 & 유사도 -->
      <div style="display:flex;gap:20px;margin-bottom:18px;padding-bottom:14px;border-bottom:1px solid #F1F5F9;">
        <div style="flex:1;">
          <div style="font-size:9px;font-weight:800;color:#94A3B8;letter-spacing:0.8px;margin-bottom:6px;">제출 증적</div>
          <div style="font-size:10.5px;color:#374151;line-height:1.8;">
            ${(r.evidence_name || '').split(', ').map(f => `<div>· ${f}</div>`).join('')}
          </div>
        </div>
        <div style="min-width:140px;">
          <div style="font-size:9px;font-weight:800;color:#94A3B8;letter-spacing:0.8px;margin-bottom:6px;">가이드라인 부합도</div>
          <div style="display:flex;align-items:center;gap:6px;">
            <div style="flex:1;height:6px;background:#E2E8F0;border-radius:3px;overflow:hidden;">
              <div style="width:${gPct}%;height:100%;background:${gPass ? '#059669' : '#DC2626'};border-radius:3px;"></div>
            </div>
            <span style="font-size:11px;font-weight:800;color:${gPass ? '#059669' : '#DC2626'};min-width:38px;text-align:right;">${gPct}%</span>
          </div>
          <div style="font-size:9px;color:#94A3B8;margin-top:3px;">기준: 70% 이상 &nbsp;·&nbsp; ${gPass ? '✓ 충족' : '✕ 미달'}</div>
        </div>
      </div>

      <!-- 판정 요약 -->
      ${verdictBlock ? `
      <div style="margin-bottom:16px;padding:12px 16px;background:#F8FAFC;border-left:4px solid #0F172A;border-radius:0 6px 6px 0;">
        <div style="font-size:9px;font-weight:800;color:#64748B;letter-spacing:0.8px;margin-bottom:5px;">점검 판정</div>
        <div style="font-size:11px;color:#0F172A;font-weight:600;line-height:1.7;">${verdictBlock.lines.join(' ')}</div>
      </div>` : ''}

      <!-- 점검 결과 상세 -->
      ${reasonBlock ? `
      <div style="margin-bottom:16px;">
        <div style="font-size:9px;font-weight:800;color:#64748B;letter-spacing:0.8px;margin-bottom:8px;padding-bottom:5px;border-bottom:1px solid #E2E8F0;">점검 결과</div>
        ${reasonIntro ? `<p style="font-size:10.5px;color:#374151;line-height:1.75;margin:0 0 10px;">${reasonIntro.trim()}</p>` : ''}
        ${reasonBullets.length ? `
        <div style="display:flex;flex-direction:column;gap:2px;margin-bottom:8px;">
          ${reasonBullets.map(b => `
          <div style="display:flex;gap:8px;padding:5px 0;border-bottom:1px solid #F8FAFC;">
            <span style="color:#6366F1;font-size:10px;flex-shrink:0;margin-top:3px;">▸</span>
            <span style="font-size:10.5px;color:#374151;line-height:1.65;">${b}</span>
          </div>`).join('')}
        </div>` : ''}
        ${reasonConclusion ? `
        <div style="padding:10px 14px;background:#EFF6FF;border-radius:5px;border-left:3px solid #3B82F6;">
          <span style="font-size:10.5px;color:#1E3A8A;font-weight:600;line-height:1.65;">${reasonConclusion}</span>
        </div>` : ''}
      </div>` : ''}

      <!-- 기타 블록 -->
      ${otherBlocks.map(b => `
      <div style="margin-bottom:12px;">
        <div style="font-size:9px;font-weight:800;color:#64748B;letter-spacing:0.8px;margin-bottom:6px;">${b.label}</div>
        ${b.lines.map(l => lineHtml(l)).join('')}
      </div>`).join('')}

      <!-- 보완 권고사항 -->
      ${actionItems.length ? `
      <div style="margin-top:14px;padding-top:14px;border-top:1px dashed #E2E8F0;">
        <div style="font-size:9px;font-weight:800;color:#92400E;letter-spacing:0.8px;margin-bottom:8px;">보완 권고사항</div>
        <div style="display:flex;flex-direction:column;gap:8px;">
          ${actionItems.map((item, idx) => `
          <div style="padding:10px 14px;background:${item.type === '필수' ? '#FEF2F2' : '#FFFBEB'};border:1px solid ${item.type === '필수' ? '#FCA5A5' : '#FDE68A'};border-radius:5px;">
            <div style="display:flex;align-items:center;gap:6px;margin-bottom:5px;">
              <span style="font-size:9px;font-weight:800;padding:1px 7px;border-radius:8px;background:${item.type === '필수' ? '#FEE2E2' : '#FEF3C7'};color:${item.type === '필수' ? '#991B1B' : '#92400E'};">${item.type === '필수' ? '필수' : '권고'}</span>
              <span style="font-size:10.5px;font-weight:700;color:#1E293B;">${idx + 1}. ${item.title}</span>
            </div>
            <p style="font-size:10px;color:#374151;line-height:1.65;margin:0 0 ${item.example ? '5px' : '0'};">${item.description}</p>
            ${item.example ? `<div style="font-size:9.5px;color:#4F46E5;padding:3px 0;">참고 서식: ${item.example}</div>` : ''}
          </div>`).join('')}
        </div>
      </div>` : ''}

      <!-- 부적합 개선사항 (legacy) -->
      ${r.improvement && !actionItems.length ? `
      <div style="margin-top:14px;padding:12px 16px;background:#FEF2F2;border:1px solid #FCA5A5;border-radius:5px;">
        <div style="font-size:9px;font-weight:800;color:#991B1B;margin-bottom:5px;letter-spacing:0.8px;">개선 필요사항</div>
        <div style="font-size:10.5px;color:#7F1D1D;line-height:1.7;">${r.improvement}</div>
      </div>` : ''}

    </div>
  </div>`
}

// ── 전체 보고서 PDF ──────────────────────────────────────────────
export async function downloadFullPDF(results, dateStr) {
  const total            = results.length
  const compliantCount   = results.filter(r => getVerdict(r) === '적합').length
  const conditionalCount = results.filter(r => getVerdict(r) === '부분 적합').length
  const nonCompliant     = results.filter(r => getVerdict(r) === '부적합').length
  const passCount        = compliantCount + conditionalCount
  const rate             = total > 0 ? Math.round((passCount / total) * 100) : 0

  const tableRows = results.map((r, i) => {
    const verdict = getVerdict(r)
    const vs = VERDICT_STYLE[verdict] || VERDICT_STYLE['부적합']
    const gPass = r.guide_similarity >= 0.7
    return `
    <tr style="background:${i % 2 === 0 ? '#F8FAFC' : 'white'};">
      <td style="padding:8px 10px;font-size:11px;font-weight:700;color:#0F2557;border-bottom:1px solid #F1F5F9;">${r.control_id}</td>
      <td style="padding:8px 10px;font-size:11px;color:#1E293B;border-bottom:1px solid #F1F5F9;">${r.control_name}</td>
      <td style="padding:8px 10px;font-size:10px;color:#64748B;border-bottom:1px solid #F1F5F9;">${r.category || ''}</td>
      <td style="padding:8px 10px;font-size:11px;font-weight:700;color:${gPass ? '#059669' : '#DC2626'};text-align:center;border-bottom:1px solid #F1F5F9;">${pct(r.guide_similarity)}</td>
      <td style="padding:8px 10px;text-align:center;border-bottom:1px solid #F1F5F9;">
        <span style="font-size:10px;font-weight:800;padding:3px 10px;border-radius:12px;background:${vs.bg};color:${vs.text};border:1px solid ${vs.border};">${verdict}</span>
      </td>
    </tr>`
  }).join('')

  const summaryText = (() => {
    const lines = []
    if (nonCompliant > 0) lines.push(`부적합 <strong style="color:#991B1B;">${nonCompliant}개</strong> 항목은 필수확인요소가 충족되지 않아 인증 심사 시 결함으로 처리될 가능성이 있으며, 즉각적인 증적 보완이 요구됩니다.`)
    if (conditionalCount > 0) lines.push(`부분 적합 <strong style="color:#92400E;">${conditionalCount}개</strong> 항목은 핵심 요건은 충족하였으나 보완 권고사항을 참고하여 추가 증적을 사전에 준비하시기 바랍니다.`)
    if (compliantCount > 0) lines.push(`적합 <strong style="color:#065F46;">${compliantCount}개</strong> 항목은 현재 제출된 증적 기준으로 인증 요건을 충족하는 것으로 확인되었습니다.`)
    return lines.join(' ')
  })()

  const html = `
  <div style="font-family:'Malgun Gothic','Apple SD Gothic Neo',sans-serif;color:#1E293B;padding:36px 44px;max-width:800px;margin:0 auto;line-height:1.6;">

    <!-- 표지 -->
    <div style="margin-bottom:36px;padding-bottom:24px;border-bottom:3px solid #0F172A;">
      <div style="font-size:26px;font-weight:900;color:#0F172A;letter-spacing:-0.8px;margin-bottom:4px;">ISMS-P 증적 점검 결과 보고서</div>
      <div style="font-size:12px;color:#64748B;margin-top:10px;">점검 일시: ${dateStr} &nbsp;·&nbsp; 300억 미만 중소기업 간편 인증 기준 적용</div>
    </div>

    <!-- Ⅰ. 개요 -->
    <div style="margin-bottom:28px;">
      <div style="font-size:13px;font-weight:900;color:#0F172A;margin-bottom:10px;display:flex;align-items:center;gap:8px;">
        <span style="display:inline-block;width:3px;height:15px;background:#0F172A;border-radius:2px;"></span>
        Ⅰ. 점검 개요
      </div>
      <table style="width:100%;border-collapse:collapse;font-size:10.5px;">
        <tr style="border-bottom:1px solid #E2E8F0;">
          <td style="padding:8px 12px;width:25%;background:#F8FAFC;font-weight:700;color:#475569;">점검 대상</td>
          <td style="padding:8px 12px;color:#374151;">${results.map(r => `${r.control_id} ${r.control_name}`).join(', ')}</td>
        </tr>
        <tr style="border-bottom:1px solid #E2E8F0;">
          <td style="padding:8px 12px;background:#F8FAFC;font-weight:700;color:#475569;">점검 기준</td>
          <td style="padding:8px 12px;color:#374151;">ISMS-P 인증 기준 (개인정보 보호법 제29조, 정보통신망법 제45조의3)</td>
        </tr>
        <tr style="border-bottom:1px solid #E2E8F0;">
          <td style="padding:8px 12px;background:#F8FAFC;font-weight:700;color:#475569;">점검 방법</td>
          <td style="padding:8px 12px;color:#374151;">코사인 유사도 기반 LLM 자동 판단 (가이드라인 부합도 기준 70% 이상)</td>
        </tr>
        <tr>
          <td style="padding:8px 12px;background:#F8FAFC;font-weight:700;color:#475569;">점검 일시</td>
          <td style="padding:8px 12px;color:#374151;">${dateStr}</td>
        </tr>
      </table>
    </div>

    <!-- Ⅱ. 종합 결과 -->
    <div style="margin-bottom:28px;">
      <div style="font-size:13px;font-weight:900;color:#0F172A;margin-bottom:10px;display:flex;align-items:center;gap:8px;">
        <span style="display:inline-block;width:3px;height:15px;background:#0F172A;border-radius:2px;"></span>
        Ⅱ. 종합 점검 결과
      </div>
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px;">
        ${[
          { label: '점검 항목 수', val: `${total}개`, color: '#0F172A', bg: '#F8FAFC', border: '#E2E8F0' },
          { label: '적합',      val: `${compliantCount}개`, color: '#065F46', bg: '#ECFDF5', border: '#6EE7B7' },
          { label: '부분 적합', val: `${conditionalCount}개`, color: '#92400E', bg: '#FFFBEB', border: '#FCD34D' },
          { label: '부적합',    val: `${nonCompliant}개`, color: '#991B1B', bg: '#FEF2F2', border: '#FCA5A5' },
        ].map(s => `
          <div style="background:${s.bg};border:1px solid ${s.border};border-radius:7px;padding:14px 12px;text-align:center;">
            <div style="font-size:9px;color:#94A3B8;font-weight:700;letter-spacing:0.5px;margin-bottom:6px;text-transform:uppercase;">${s.label}</div>
            <div style="font-size:24px;font-weight:900;color:${s.color};">${s.val}</div>
          </div>`).join('')}
      </div>
      <div style="padding:14px 18px;background:#F0F4FF;border:1px solid #C7D2FE;border-radius:7px;font-size:11px;color:#374151;line-height:1.8;">
        총 <strong>${total}개</strong> 항목을 점검한 결과, 적합·부분 적합 기준 <strong>${rate}%</strong>의 통과율을 기록하였습니다.
        ${summaryText}
      </div>
    </div>

    <!-- Ⅲ. 항목별 목록 -->
    <div style="margin-bottom:28px;">
      <div style="font-size:13px;font-weight:900;color:#0F172A;margin-bottom:10px;display:flex;align-items:center;gap:8px;">
        <span style="display:inline-block;width:3px;height:15px;background:#0F172A;border-radius:2px;"></span>
        Ⅲ. 항목별 점검 결과 현황
      </div>
      <table style="width:100%;border-collapse:collapse;font-size:11px;">
        <thead>
          <tr style="background:#0F172A;color:white;">
            <th style="padding:10px 12px;text-align:left;font-weight:700;font-size:10px;">항목번호</th>
            <th style="padding:10px 12px;text-align:left;font-weight:700;font-size:10px;">항목명</th>
            <th style="padding:10px 12px;text-align:left;font-weight:700;font-size:10px;">카테고리</th>
            <th style="padding:10px 12px;text-align:center;font-weight:700;font-size:10px;">가이드 유사도</th>
            <th style="padding:10px 12px;text-align:center;font-weight:700;font-size:10px;">판정</th>
          </tr>
        </thead>
        <tbody>${tableRows}</tbody>
      </table>
    </div>

    <!-- Ⅳ. 항목별 상세 -->
    <div>
      <div style="font-size:13px;font-weight:900;color:#0F172A;margin-bottom:16px;display:flex;align-items:center;gap:8px;">
        <span style="display:inline-block;width:3px;height:15px;background:#0F172A;border-radius:2px;"></span>
        Ⅳ. 항목별 상세 점검 결과
      </div>
      ${results.map((r, i) => itemDetailHtml(r, i + 1)).join('')}
    </div>

    <!-- 면책 조항 -->
    <div style="margin-top:28px;padding:14px 18px;background:#F8FAFC;border:1px solid #E2E8F0;border-radius:7px;">
      <div style="font-size:9px;font-weight:800;color:#94A3B8;letter-spacing:0.8px;margin-bottom:5px;">유의사항</div>
      <p style="font-size:9.5px;color:#64748B;line-height:1.7;margin:0;">
        본 보고서는 제출된 증적 자료를 기반으로 KISIA ISMS-P 증적 자동 점검 도구가 자동 생성한 예비 점검 결과입니다.
        실제 인증 심사 결과와 상이할 수 있으며, 최종 적합 여부는 공식 심사관의 판단에 따릅니다.
        본 결과는 인증 준비를 위한 내부 검토 목적으로만 활용하시기 바랍니다.
      </p>
    </div>

    <!-- 푸터 -->
    <div style="margin-top:20px;padding-top:14px;border-top:2px solid #E2E8F0;display:flex;justify-content:space-between;align-items:center;">
      <span style="font-size:10px;color:#94A3B8;">ⓒ KISIA · ISMS-P 증적 자동 점검 도구</span>
      <span style="font-size:10px;color:#94A3B8;">${dateStr}</span>
    </div>
  </div>`

  const container = document.createElement('div')
  container.innerHTML = html
  document.body.appendChild(container)

  await html2pdf().set({
    margin: [8, 8, 8, 8],
    filename: `ISMS-P_전체보고서_${dateStr.replace(/[: ]/g, '-')}.pdf`,
    image: { type: 'jpeg', quality: 0.98 },
    html2canvas: { scale: 2, useCORS: true, logging: false },
    jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
    pagebreak: { mode: ['avoid-all', 'css'] },
  }).from(container).save()

  document.body.removeChild(container)
}

// ── 항목 단독 PDF ────────────────────────────────────────────────
export async function downloadItemPDF(r, dateStr) {
  const verdict = getVerdict(r)
  const vs = VERDICT_STYLE[verdict] || VERDICT_STYLE['부적합']

  const html = `
  <div style="font-family:'Malgun Gothic','Apple SD Gothic Neo',sans-serif;color:#1E293B;padding:36px 44px;max-width:800px;margin:0 auto;line-height:1.6;">
    <div style="display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:20px;padding-bottom:16px;border-bottom:3px solid #0F172A;">
      <div>
        <div style="font-size:10px;color:#94A3B8;letter-spacing:2px;margin-bottom:5px;text-transform:uppercase;">KISIA · ISMS-P 증적 점검 결과</div>
        <div style="font-size:20px;font-weight:900;color:#0F172A;">항목별 상세 보고서</div>
      </div>
      <div style="text-align:right;">
        <div style="font-size:10px;color:#94A3B8;margin-bottom:5px;">${dateStr}</div>
        <span style="font-size:11px;font-weight:800;padding:5px 14px;border-radius:20px;background:${vs.bg};color:${vs.text};border:1px solid ${vs.border};">${verdict}</span>
      </div>
    </div>
    ${itemDetailHtml(r, 1)}
    <div style="margin-top:20px;padding:12px 16px;background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;">
      <p style="font-size:9.5px;color:#64748B;line-height:1.7;margin:0;">
        본 보고서는 제출된 증적 자료를 기반으로 KISIA ISMS-P 증적 자동 점검 도구가 자동 생성한 예비 점검 결과입니다.
        실제 인증 심사 결과와 상이할 수 있으며, 최종 적합 여부는 공식 심사관의 판단에 따릅니다.
      </p>
    </div>
    <div style="margin-top:16px;padding-top:12px;border-top:1px solid #E2E8F0;display:flex;justify-content:space-between;font-size:10px;color:#94A3B8;">
      <span>ⓒ KISIA · ISMS-P 증적 자동 점검 도구</span>
      <span>${dateStr}</span>
    </div>
  </div>`

  const container = document.createElement('div')
  container.innerHTML = html
  document.body.appendChild(container)

  await html2pdf().set({
    margin: [8, 8, 8, 8],
    filename: `ISMS-P_${r.control_id}_${r.control_name}_${dateStr.replace(/[: ]/g, '-')}.pdf`,
    image: { type: 'jpeg', quality: 0.98 },
    html2canvas: { scale: 2, useCORS: true, logging: false },
    jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
  }).from(container).save()

  document.body.removeChild(container)
}
