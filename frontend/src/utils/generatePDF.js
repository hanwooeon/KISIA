import html2pdf from 'html2pdf.js'

function pct(v) { return (v * 100).toFixed(1) + '%' }

function barHtml(score, color) {
  const w = Math.round(score * 100)
  return `
    <div style="display:flex;align-items:center;gap:8px;">
      <div style="flex:1;height:8px;background:#F1F5F9;border-radius:4px;overflow:hidden;">
        <div style="width:${w}%;height:100%;background:${color};border-radius:4px;"></div>
      </div>
      <span style="font-size:11px;font-weight:700;color:${color};min-width:40px;text-align:right;">${pct(score)}</span>
    </div>`
}

function itemDetailHtml(r) {
  const okColor = '#059669'
  const failColor = '#DC2626'
  const gColor = r.guide_similarity >= 0.7 ? okColor : failColor
  const rColor = r.required_similarity >= 0.65 ? okColor : failColor
  const isOk = r.is_compliant

  return `
  <div style="margin-bottom:24px;padding:18px;border:1px solid #E2E8F0;border-radius:8px;border-left:4px solid ${isOk ? okColor : failColor};page-break-inside:avoid;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
        <span style="background:#0F2557;color:white;padding:3px 10px;border-radius:5px;font-size:11px;font-weight:800;">${r.control_id}</span>
        <span style="font-size:15px;font-weight:800;color:#1E293B;">${r.control_name}</span>
        <span style="font-size:10px;color:#64748B;background:#F1F5F9;border:1px solid #E2E8F0;padding:2px 8px;border-radius:20px;">${r.category || ''}</span>
      </div>
      <span style="font-size:11px;font-weight:700;padding:4px 12px;border-radius:20px;background:${isOk ? '#DCFCE7' : '#FEE2E2'};color:${isOk ? '#15803D' : '#DC2626'};">
        ${isOk ? '✓ 적합' : '✕ 부적합'}
      </span>
    </div>
    <div style="display:flex;align-items:center;gap:8px;padding:8px 0;border-top:1px solid #F1F5F9;border-bottom:1px solid #F1F5F9;margin-bottom:12px;">
      <span style="font-size:10px;background:#F1F5F9;color:#64748B;padding:2px 8px;border-radius:4px;font-weight:700;">증적파일</span>
      <span style="font-size:12px;font-weight:600;color:#1E293B;">${r.evidence_name}</span>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:12px;">
      <div>
        <div style="font-size:10px;font-weight:700;color:#64748B;margin-bottom:5px;">가이드라인 유사도 <span style="color:#94A3B8;">(기준: 70% 이상)</span></div>
        ${barHtml(r.guide_similarity, gColor)}
      </div>
      <div>
        <div style="font-size:10px;font-weight:700;color:#64748B;margin-bottom:5px;">필수확인요소 유사도 <span style="color:#94A3B8;">(기준: 65% 이상)</span></div>
        ${barHtml(r.required_similarity, rColor)}
      </div>
    </div>
    <div style="margin-bottom:${r.improvement ? '10px' : '0'};">
      <div style="font-size:10px;font-weight:800;color:#64748B;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">판단 근거</div>
      <p style="font-size:11px;color:#374151;line-height:1.7;margin:0;">${r.judgment_reason}</p>
    </div>
    ${r.improvement ? `
    <div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:6px;padding:10px 12px;">
      <div style="font-size:10px;font-weight:800;color:#D97706;margin-bottom:4px;">⚠ 보완사항</div>
      <p style="font-size:11px;color:#92400E;line-height:1.65;margin:0;">${r.improvement}</p>
    </div>` : ''}
  </div>`
}

export async function downloadFullPDF(results, dateStr) {
  const total = results.length
  const compliant = results.filter(r => r.is_compliant).length
  const rate = total > 0 ? Math.round((compliant / total) * 100) : 0
  const nonCompliant = total - compliant

  const tableRows = results.map((r, i) => `
    <tr style="background:${i % 2 === 0 ? '#F8FAFC' : 'white'};">
      <td style="padding:7px 10px;font-size:11px;font-weight:700;color:#0F2557;">${r.control_id}</td>
      <td style="padding:7px 10px;font-size:11px;color:#1E293B;">${r.control_name}</td>
      <td style="padding:7px 10px;font-size:10px;color:#64748B;">${r.category || ''}</td>
      <td style="padding:7px 10px;font-size:11px;font-weight:700;color:${r.guide_similarity >= 0.7 ? '#059669' : '#DC2626'};text-align:center;">${pct(r.guide_similarity)}</td>
      <td style="padding:7px 10px;font-size:11px;font-weight:700;color:${r.required_similarity >= 0.65 ? '#059669' : '#DC2626'};text-align:center;">${pct(r.required_similarity)}</td>
      <td style="padding:7px 10px;text-align:center;">
        <span style="font-size:10px;font-weight:700;padding:2px 9px;border-radius:10px;background:${r.is_compliant ? '#DCFCE7' : '#FEE2E2'};color:${r.is_compliant ? '#15803D' : '#DC2626'};">
          ${r.is_compliant ? '적합' : '부적합'}
        </span>
      </td>
    </tr>`).join('')

  const html = `
  <div style="font-family:'Malgun Gothic','Apple SD Gothic Neo',sans-serif;color:#1E293B;padding:30px 36px;max-width:800px;margin:0 auto;">
    <!-- Header -->
    <div style="text-align:center;margin-bottom:28px;padding-bottom:20px;border-bottom:3px solid #0F2557;">
      <div style="font-size:11px;color:#64748B;letter-spacing:2px;margin-bottom:6px;">한국인터넷진흥원 KISIA</div>
      <div style="font-size:22px;font-weight:900;color:#0F2557;margin-bottom:8px;">ISMS-P 증적 자동 점검 결과 보고서</div>
      <div style="font-size:11px;color:#94A3B8;">생성일시: ${dateStr} &nbsp;|&nbsp; 300억 미만 중소기업 간편인증</div>
    </div>

    <!-- Summary -->
    <div style="margin-bottom:28px;">
      <div style="font-size:13px;font-weight:800;color:#0F2557;margin-bottom:12px;padding-bottom:6px;border-bottom:1px solid #E2E8F0;">1. 점검 결과 요약</div>
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;">
        ${[
          { label:'전체 항목', val:`${total}개`, color:'#1E293B', bg:'#F8FAFC', border:'#E2E8F0' },
          { label:'적합', val:`${compliant}개`, color:'#059669', bg:'#F0FDF4', border:'#86EFAC' },
          { label:'부적합', val:`${nonCompliant}개`, color:'#DC2626', bg:'#FEF2F2', border:'#FCA5A5' },
          { label:'적합률', val:`${rate}%`, color:'#2563EB', bg:'#EFF6FF', border:'#93C5FD' },
        ].map(s => `
          <div style="background:${s.bg};border:1px solid ${s.border};border-radius:8px;padding:14px;text-align:center;">
            <div style="font-size:10px;color:#94A3B8;font-weight:600;margin-bottom:4px;">${s.label}</div>
            <div style="font-size:22px;font-weight:900;color:${s.color};">${s.val}</div>
          </div>`).join('')}
      </div>
    </div>

    <!-- Table -->
    <div style="margin-bottom:28px;">
      <div style="font-size:13px;font-weight:800;color:#0F2557;margin-bottom:12px;padding-bottom:6px;border-bottom:1px solid #E2E8F0;">2. 항목별 점검 결과 목록</div>
      <table style="width:100%;border-collapse:collapse;font-size:11px;">
        <thead>
          <tr style="background:#0F2557;color:white;">
            <th style="padding:8px 10px;text-align:left;font-weight:700;">항목번호</th>
            <th style="padding:8px 10px;text-align:left;font-weight:700;">항목명</th>
            <th style="padding:8px 10px;text-align:left;font-weight:700;">카테고리</th>
            <th style="padding:8px 10px;text-align:center;font-weight:700;">가이드 유사도</th>
            <th style="padding:8px 10px;text-align:center;font-weight:700;">필수 유사도</th>
            <th style="padding:8px 10px;text-align:center;font-weight:700;">판정</th>
          </tr>
        </thead>
        <tbody>${tableRows}</tbody>
      </table>
    </div>

    <!-- Per-item details -->
    <div>
      <div style="font-size:13px;font-weight:800;color:#0F2557;margin-bottom:16px;padding-bottom:6px;border-bottom:1px solid #E2E8F0;">3. 항목별 상세 결과</div>
      ${results.map(r => itemDetailHtml(r)).join('')}
    </div>

    <!-- Footer -->
    <div style="margin-top:24px;padding-top:12px;border-top:1px solid #E2E8F0;text-align:center;font-size:10px;color:#94A3B8;">
      본 보고서는 KISIA ISMS-P 증적 자동 점검 시스템에 의해 생성되었습니다. &nbsp;|&nbsp; ${dateStr}
    </div>
  </div>`

  const container = document.createElement('div')
  container.innerHTML = html
  document.body.appendChild(container)

  await html2pdf().set({
    margin: [8, 8, 8, 8],
    filename: `ISMS-P_전체보고서_${dateStr.replace(/[: ]/g, '-')}.pdf`,
    image: { type: 'jpeg', quality: 0.97 },
    html2canvas: { scale: 2, useCORS: true, logging: false },
    jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
    pagebreak: { mode: ['avoid-all', 'css'] },
  }).from(container).save()

  document.body.removeChild(container)
}

export async function downloadItemPDF(r, dateStr) {
  const html = `
  <div style="font-family:'Malgun Gothic','Apple SD Gothic Neo',sans-serif;color:#1E293B;padding:30px 36px;max-width:800px;margin:0 auto;">
    <!-- Header -->
    <div style="display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:20px;padding-bottom:16px;border-bottom:3px solid #0F2557;">
      <div>
        <div style="font-size:10px;color:#64748B;letter-spacing:1.5px;margin-bottom:4px;">KISIA · ISMS-P 증적 점검 결과</div>
        <div style="font-size:18px;font-weight:900;color:#0F2557;">항목별 상세 보고서</div>
      </div>
      <div style="font-size:10px;color:#94A3B8;">${dateStr}</div>
    </div>
    ${itemDetailHtml(r)}
    <div style="margin-top:24px;padding-top:12px;border-top:1px solid #E2E8F0;text-align:center;font-size:10px;color:#94A3B8;">
      KISIA ISMS-P 증적 자동 점검 시스템 &nbsp;|&nbsp; ${dateStr}
    </div>
  </div>`

  const container = document.createElement('div')
  container.innerHTML = html
  document.body.appendChild(container)

  await html2pdf().set({
    margin: [8, 8, 8, 8],
    filename: `ISMS-P_${r.control_id}_${r.control_name}_${dateStr.replace(/[: ]/g, '-')}.pdf`,
    image: { type: 'jpeg', quality: 0.97 },
    html2canvas: { scale: 2, useCORS: true, logging: false },
    jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
  }).from(container).save()

  document.body.removeChild(container)
}
