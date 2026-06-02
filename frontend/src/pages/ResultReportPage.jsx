import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { downloadFullPDF, downloadItemPDF } from '../utils/generatePDF'
import './ResultReportPage.css'

// ── 3단계 판정 색상 정의 ──────────────────────────────────────────
const VERDICT_STYLE = {
  '적합':      { color: '#059669', bg: '#DCFCE7', border: '#86EFAC', dotColor: '#059669', icon: '✓' },
  '부분 적합': { color: '#D97706', bg: '#FEF3C7', border: '#FDE68A', dotColor: '#D97706', icon: '△' },
  '부적합':    { color: '#DC2626', bg: '#FEE2E2', border: '#FCA5A5', dotColor: '#DC2626', icon: '✕' },
}

// 히스토리 호환: verdict 필드 없는 구버전 대응
function getVerdict(r) {
  if (r.verdict) return r.verdict
  if (r.overall?.verdict) return r.overall.verdict
  return r.is_compliant ? '적합' : '부적합'
}

function getRiskLevel(verdict) {
  if (verdict === '적합') return 'LOW'
  if (verdict === '부분 적합') return 'MEDIUM'
  return 'HIGH'
}

const RISK = {
  LOW:    { label: '양호', color: '#059669', bg: '#DCFCE7', border: '#86EFAC' },
  MEDIUM: { label: '주의', color: '#D97706', bg: '#FEF3C7', border: '#FDE68A' },
  HIGH:   { label: '미흡', color: '#DC2626', bg: '#FEE2E2', border: '#FCA5A5' },
}

function generateDetailedReason(ctrl_name, guide_sim, req_sim, verdict) {
  const g = (guide_sim * 100).toFixed(0)
  const r = (req_sim * 100).toFixed(0)
  if (verdict === '적합') {
    return `제출된 증적자료는 「${ctrl_name}」 항목의 인증기준을 충족하는 것으로 판단됩니다. 가이드라인 유사도(${g}%)가 기준치(70%)를 상회하고, 필수확인요소 유사도(${r}%)가 기준치(65%)를 만족하여 해당 항목의 이행 여부가 충분히 입증되었습니다.`
  }
  if (verdict === '부분 적합') {
    return `제출된 증적자료는 「${ctrl_name}」 항목의 핵심 요건을 대체로 충족합니다. 다만 일부 보완을 통해 심사 리스크를 낮출 수 있습니다. 아래 보완 권고사항을 참고하시기 바랍니다.`
  }
  const issues = []
  if (guide_sim < 0.75) issues.push(`가이드라인 유사도(${g}%)가 기준치(75%)에 미달`)
  if (req_sim < 0.75) issues.push(`필수확인요소 유사도(${r}%)가 기준치(75%)에 미달`)
  return `제출된 증적자료는 「${ctrl_name}」 항목의 인증기준을 충족하지 못하는 것으로 판단됩니다. ${issues.join(', ')}하여 현재 증적만으로는 해당 항목의 이행 여부를 충분히 입증하기 어렵습니다. 하기 개선 권고사항을 참고하여 증적을 보완하시기 바랍니다.`
}

function generateImprovement(ctrl_name) {
  return `「${ctrl_name}」 항목의 필수확인요소를 충족하는 내용이 포함된 증적자료를 추가 제출하거나 기존 증적을 보완하시기 바랍니다.`
}

function generateMockResults(selectedControls, files) {
  return (selectedControls || []).map(ctrl => {
    const fileList = Array.isArray(files?.[ctrl.control_id])
      ? files[ctrl.control_id]
      : files?.[ctrl.control_id] ? [files[ctrl.control_id]] : []

    const file_results = fileList.length > 0
      ? fileList.map((file, i) => ({
          inspection_no:      i + 1,
          filename:           file?.name || `증적파일_${i + 1}`,
          guide_similarity:   +(Math.random() * 0.4 + 0.55).toFixed(2),
          keyword_similarity: +(Math.random() * 0.4 + 0.5).toFixed(2),
          file_summary:       `${ctrl.control_name} 항목과 관련된 증적자료입니다.`,
          file_confirmed:     ['관련 내용이 포함되어 있음', '담당자 정보 확인 가능'],
          file_missing:       i === 0 ? ['서명·날인 정보 없음'] : [],
        }))
      : [{
          inspection_no: 1, filename: '증적파일',
          guide_similarity: 0.65, keyword_similarity: 0.6,
          file_summary: `${ctrl.control_name} 항목과 관련된 증적자료입니다.`,
          file_confirmed: ['관련 내용 포함'],
          file_missing: [],
        }]

    const guide_sim = +(file_results.reduce((s, r) => s + r.guide_similarity, 0) / file_results.length).toFixed(2)
    const req_sim   = +(file_results.reduce((s, r) => s + r.keyword_similarity, 0) / file_results.length).toFixed(2)
    const minSim    = Math.min(guide_sim, req_sim)
    const verdict   = minSim >= 0.75 ? '적합' : minSim >= 0.60 ? '부분 적합' : '부적합'

    const overall = {
      guide_similarity:   guide_sim,
      keyword_similarity: req_sim,
      verdict,
      is_compliant:       verdict !== '부적합',
      judgment_reason:    generateDetailedReason(ctrl.control_name, guide_sim, req_sim, verdict),
      improvement:        verdict === '부적합' ? generateImprovement(ctrl.control_name) : null,
      action_items:       verdict === '부분 적합'
        ? [{ type: '권고', title: '보완 서류 추가', description: '핵심 요건은 확인되나 일부 세부 사항을 보완하면 더 확실하게 통과할 수 있습니다.', example: '관련 문서 참고' }]
        : [],
    }

    return {
      control_id:          ctrl.control_id,
      control_name:        ctrl.control_name,
      category:            ctrl.category,
      keywords:            ctrl.keywords || [],
      file_results,
      overall,
      verdict,
      is_compliant:        overall.is_compliant,
      guide_similarity:    overall.guide_similarity,
      required_similarity: overall.keyword_similarity,
      risk_level:          getRiskLevel(verdict),
      evidence_name:       file_results.map(f => f.filename).join(', '),
      judgment_reason:     overall.judgment_reason,
      improvement:         overall.improvement,
      action_items:        overall.action_items,
    }
  })
}

function ScoreGauge({ label, score, threshold, color }) {
  const pct = Math.round(score * 100)
  const pass = score >= threshold
  return (
    <div className="score-gauge">
      <div className="score-gauge-header">
        <span className="score-gauge-label">{label}</span>
        <span className="score-gauge-val" style={{ color }}>{pct}%</span>
      </div>
      <div className="score-gauge-track">
        <div className="score-gauge-fill" style={{ width: `${pct}%`, background: color }} />
        <div className="score-gauge-threshold" style={{ left: `${threshold * 100}%` }} />
      </div>
      <div className="score-gauge-footer">
        <span className="score-gauge-basis">기준: {threshold * 100}% 이상</span>
        <span className={`score-gauge-result ${pass ? 'pass' : 'fail'}`}>
          {pass ? '✓ 충족' : '✕ 미달'}
        </span>
      </div>
    </div>
  )
}

// ── 보완 권고 / 필수 항목 카드 ────────────────────────────────────
function ActionItemCard({ item }) {
  const isRequired = item.type === '필수'
  return (
    <div className={`action-item-card ${isRequired ? 'action-required' : 'action-recommended'}`}>
      <div className="action-item-header">
        <span className={`action-type-badge ${isRequired ? 'badge-required' : 'badge-recommended'}`}>
          {isRequired ? '⚠ 필수' : '💡 권고'}
        </span>
        <span className="action-item-title">{item.title}</span>
      </div>
      <p className="action-item-desc">{item.description}</p>
      {item.example && (
        <div className="action-item-example">
          <span className="action-example-label">예시 서류</span>
          <span className="action-example-text">{item.example}</span>
        </div>
      )}
    </div>
  )
}

// ── 제출 시 예상 시나리오 박스 (부분 적합용) ───────────────────
function SubmitScenarioBox({ verdict, actionItems }) {
  if (verdict === '적합') return null
  if (verdict === '부분 적합') {
    return (
      <div className="scenario-box scenario-conditional">
        <div className="scenario-icon">📋</div>
        <div className="scenario-body">
          <div className="scenario-title">이 상태로 제출하면 어떻게 되나요?</div>
          <p className="scenario-text">
            현재 증적은 핵심 요건을 충족하고 있어 <strong>통과 가능성이 높습니다.</strong>
            다만 심사관이 아래 보완 항목에 대해 추가 자료를 요청할 수 있습니다.
            미리 준비해 두면 더 빠르고 확실하게 통과할 수 있습니다.
          </p>
        </div>
      </div>
    )
  }
  return (
    <div className="scenario-box scenario-fail">
      <div className="scenario-icon">🚨</div>
      <div className="scenario-body">
        <div className="scenario-title">이 상태로 제출하면 어떻게 되나요?</div>
        <p className="scenario-text">
          핵심 필수확인요소가 증적에서 확인되지 않아 <strong>결함으로 처리될 가능성이 높습니다.</strong>
          아래 보완 사항을 반드시 조치한 후 재제출하시기 바랍니다.
        </p>
      </div>
    </div>
  )
}

export default function ResultReportPage({ taskId, selectedControls, uploadedFiles, apiResults, historyResults, onSaveHistory, onNewAnalysis }) {
  const navigate = useNavigate()
  const [selectedIdx, setSelectedIdx] = useState(0)
  const [fileSlideIdx, setFileSlideIdx] = useState(0)
  const [pdfLoading, setPdfLoading] = useState(null)
  const savedRef = useRef(false)
  const resultsRef = useRef(null)

  if (!resultsRef.current) {
    if (historyResults) {
      resultsRef.current = historyResults
    } else if (apiResults) {
      resultsRef.current = apiResults.map(r => {
        const verdict = r.overall?.verdict || (r.overall?.is_compliant ? '적합' : '부적합')
        return {
          control_id:          r.control_id,
          control_name:        r.control_name,
          category:            selectedControls.find(c => c.control_id === r.control_id)?.category || '',
          keywords:            selectedControls.find(c => c.control_id === r.control_id)?.keywords || [],
          file_results:        r.file_results,
          overall:             r.overall,
          verdict,
          is_compliant:        verdict !== '부적합',
          guide_similarity:    r.overall?.guide_similarity ?? 0,
          required_similarity: r.overall?.keyword_similarity ?? 0,
          risk_level:          getRiskLevel(verdict),
          evidence_name:       r.file_results?.map(f => f.filename).join(', ') || '',
          judgment_reason:     r.overall?.judgment_reason || '',
          improvement:         r.overall?.improvement || null,
          action_items:        r.overall?.action_items || [],
        }
      })
    } else {
      resultsRef.current = generateMockResults(selectedControls, uploadedFiles)
    }
  }
  const results = resultsRef.current

  const dateStr = new Date().toLocaleString('ko-KR', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit'
  })

  useEffect(() => { setFileSlideIdx(0) }, [selectedIdx])

  useEffect(() => {
    if (!savedRef.current && results.length > 0 && !historyResults) {
      savedRef.current = true
      const compliantCount   = results.filter(r => r.verdict === '적합').length
      const conditionalCount = results.filter(r => r.verdict === '부분 적합').length
      const passCount        = compliantCount + conditionalCount
      onSaveHistory?.({
        id: Date.now(),
        date: new Date().toISOString(),
        fullResults: results,
        results: results.map(r => ({
          control_id:          r.control_id,
          control_name:        r.control_name,
          category:            r.category,
          verdict:             r.verdict,
          is_compliant:        r.is_compliant,
          risk_level:          r.risk_level,
          guide_similarity:    r.guide_similarity,
          required_similarity: r.required_similarity,
        })),
        summary: {
          total:       results.length,
          compliant:   compliantCount,
          conditional: conditionalCount,
          rate:        results.length > 0 ? Math.round((passCount / results.length) * 100) : 0,
        },
      })
    }
  }, [])

  if (!historyResults && (!selectedControls || selectedControls.length === 0)) {
    return (
      <div style={{ textAlign: 'center', padding: '80px 24px' }}>
        <p style={{ color: '#64748B', marginBottom: 20 }}>분석 결과가 없습니다.</p>
        <button className="btn-primary" onClick={() => navigate('/')}>처음부터 시작하기</button>
      </div>
    )
  }

  const total              = results.length
  const compliantCount     = results.filter(r => getVerdict(r) === '적합').length
  const conditionalCount   = results.filter(r => getVerdict(r) === '부분 적합').length
  const nonCompliantCount  = results.filter(r => getVerdict(r) === '부적합').length
  const passCount          = compliantCount + conditionalCount
  const rate               = total > 0 ? Math.round((passCount / total) * 100) : 0

  const detail      = results[selectedIdx]
  const detailVerdict = getVerdict(detail)
  const verdictStyle  = VERDICT_STYLE[detailVerdict] || VERDICT_STYLE['부적합']
  const actionItems   = detail?.action_items || detail?.overall?.action_items || []

  const handleFullPDF = async () => {
    setPdfLoading('full')
    try { await downloadFullPDF(results, dateStr) } finally { setPdfLoading(null) }
  }

  const handleItemPDF = async () => {
    setPdfLoading('item')
    try { await downloadItemPDF(detail, dateStr) } finally { setPdfLoading(null) }
  }

  const handleNewAnalysis = () => { onNewAnalysis?.(); navigate('/') }

  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">결과 보고서</h2>
        <p className="page-desc">ISMS-P 증적 점검 결과 — 코사인 유사도 기반 LLM 자동 판단</p>
      </div>

      {/* 요약 카드 */}
      <div className="summary-grid">
        <div className="summary-card card">
          <span className="summary-label">전체 항목</span>
          <span className="summary-big">{total}</span>
          <span className="summary-unit">개</span>
        </div>
        <div className="summary-card card compliant-card">
          <span className="summary-label">적합</span>
          <span className="summary-big green">{compliantCount}</span>
          <span className="summary-unit">개</span>
        </div>
        <div className="summary-card card conditional-card">
          <span className="summary-label">부분적합</span>
          <span className="summary-big orange">{conditionalCount}</span>
          <span className="summary-unit">개</span>
        </div>
        <div className="summary-card card non-card">
          <span className="summary-label">부적합</span>
          <span className="summary-big red">{nonCompliantCount}</span>
          <span className="summary-unit">개</span>
        </div>
      </div>

      {/* 2패널 */}
      <div className="result-layout">

        {/* 좌: 목록 */}
        <div className="result-list-panel">
          <div className="result-list-header">
            항목 목록 <span className="list-header-count">{total}개</span>
          </div>
          {results.map((r, idx) => {
            const v = getVerdict(r)
            const vs = VERDICT_STYLE[v] || VERDICT_STYLE['부적합']
            return (
              <div
                key={idx}
                className={`result-list-item ${idx === selectedIdx ? 'rli-active' : ''}`}
                style={idx === selectedIdx ? { borderLeftColor: vs.color, background: vs.bg + '80' } : {}}
                onClick={() => setSelectedIdx(idx)}
              >
                <span className="rli-dot" style={{ background: vs.dotColor }} />
                <div className="rli-text">
                  <span className="rli-id">{r.control_id}</span>
                  <span className="rli-name">{r.control_name}</span>
                </div>
                <span className="rli-risk-badge" style={{
                  background: vs.bg,
                  color:      vs.color,
                  border:     `1px solid ${vs.border}`,
                }}>
                  {vs.icon} {v}
                </span>
              </div>
            )
          })}
        </div>

        {/* 우: 상세 */}
        {detail && (
          <div className="result-detail-panel">
            <div className="detail-card card">

              {/* 헤더 */}
              <div className="detail-header">
                <div className="detail-title-row">
                  <span className="detail-num">{detail.control_id}</span>
                  <span className="detail-name">{detail.control_name}</span>
                  {detail.category && <span className="detail-category">{detail.category}</span>}
                </div>
                <div className="detail-header-right">
                  <span className="verdict-badge" style={{
                    background: verdictStyle.bg,
                    color:      verdictStyle.color,
                    border:     `1.5px solid ${verdictStyle.border}`,
                  }}>
                    {verdictStyle.icon} {detailVerdict}
                  </span>
                </div>
              </div>

              {/* 증적파일 */}
              <div className="detail-evidence-row">
                <span className="detail-ev-label">제출 증적</span>
                <div className="detail-ev-name">
                  {(detail.evidence_name || '').split(', ').map((name, i) => (
                    <div key={i} className="ev-file-row">{name}</div>
                  ))}
                </div>
              </div>

              {/* 제출 시 예상 시나리오 (적합이 아닐 때만) */}
              {detailVerdict !== '적합' && (
                <SubmitScenarioBox verdict={detailVerdict} actionItems={actionItems} />
              )}

              {/* 파일별 내용 요약 — 캐러셀 */}
              {detail.file_results?.length > 0 && (
                <div className="detail-section">
                  <div className="detail-section-title">
                    제출 파일별 내용
                    <span className="file-slide-counter">
                      {fileSlideIdx + 1} / {detail.file_results.length}
                    </span>
                  </div>
                  <div className="file-carousel">
                    <button
                      className="file-carousel-arrow"
                      disabled={fileSlideIdx === 0}
                      onClick={() => setFileSlideIdx(i => Math.max(0, i - 1))}
                    >‹</button>
                    <div className="file-carousel-card">
                      <div className="file-carousel-name">
                        {detail.file_results[fileSlideIdx]?.filename}
                      </div>
                      {detail.file_results[fileSlideIdx]?.file_summary && (
                        <p className="file-carousel-desc">
                          {detail.file_results[fileSlideIdx].file_summary}
                        </p>
                      )}
                      <div className="file-carousel-bullets">
                        {(detail.file_results[fileSlideIdx]?.file_confirmed || []).map((item, i) => (
                          <div key={i} className="fc-bullet fc-confirmed">{item}</div>
                        ))}
                        {(detail.file_results[fileSlideIdx]?.file_missing || []).map((item, i) => (
                          <div key={i} className="fc-bullet fc-missing">{item}</div>
                        ))}
                      </div>
                    </div>
                    <button
                      className="file-carousel-arrow"
                      disabled={fileSlideIdx === detail.file_results.length - 1}
                      onClick={() => setFileSlideIdx(i => Math.min(detail.file_results.length - 1, i + 1))}
                    >›</button>
                  </div>
                  {detail.file_results.length > 1 && (
                    <div className="file-carousel-dots">
                      {detail.file_results.map((_, i) => (
                        <button
                          key={i}
                          className={`file-carousel-dot ${i === fileSlideIdx ? 'dot-active' : ''}`}
                          onClick={() => setFileSlideIdx(i)}
                          title={detail.file_results[i].filename}
                        />
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* 판단 근거 */}
              <div className="detail-section">
                <div className="detail-section-title">판단 근거</div>
                <div className="detail-reason-box">
                  {(detail.judgment_reason || '').split('\n\n').filter(Boolean).map((para, i) => {
                    const labelMatch = para.match(/^\*\*(.+?):\*\*\s*([\s\S]*)$/)
                    if (labelMatch) {
                      const isWarning = labelMatch[1].includes('보완')
                      const body = labelMatch[2].trim()
                      const lines = body.split('\n').filter(Boolean)
                      return (
                        <div key={i} className={`reason-block ${isWarning ? 'reason-block-warn' : ''}`}>
                          <span className={`reason-label ${isWarning ? 'reason-label-warn' : ''}`}>{labelMatch[1]}</span>
                          <div className="reason-body">
                            {lines.map((line, j) => {
                              if (line.startsWith('- '))
                                return <div key={j} className="reason-bullet">{line.slice(2)}</div>
                              if (line.startsWith('→ '))
                                return <div key={j} className="reason-arrow">{line.slice(2)}</div>
                              return <p key={j} className="reason-text" style={{ margin: j > 0 ? '6px 0 0' : 0 }}>{line}</p>
                            })}
                          </div>
                        </div>
                      )
                    }
                    return <p key={i} className="reason-text" style={{ marginTop: i > 0 ? 10 : 0 }}>{para}</p>
                  })}
                </div>
              </div>

              {/* 보완 권고 / 필수 액션 아이템 */}
              {actionItems.length > 0 && (
                <div className="detail-section">
                  <div className={`detail-section-title ${detailVerdict === '부적합' ? 'warn' : 'conditional'}`}>
                    {detailVerdict === '부적합' ? '🚨 필수 보완 사항' : '💡 보완하면 더 좋아요'}
                  </div>
                  <div className="action-items-list">
                    {actionItems.map((item, i) => (
                      <ActionItemCard key={i} item={item} />
                    ))}
                  </div>
                </div>
              )}

              {/* 부적합 개선 권고사항 (legacy improvement 필드) */}
              {detail.improvement && actionItems.length === 0 && (
                <div className="detail-section">
                  <div className="detail-section-title warn">개선 권고사항</div>
                  <div className="detail-improvement">
                    <div>
                      {(detail.improvement || '').split('\n\n').filter(Boolean).map((para, i) => (
                        <p key={i} style={{ margin: i > 0 ? '8px 0 0' : 0, fontSize: '0.88rem', color: '#92400E', lineHeight: 1.7 }}>{para}</p>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* 이전/다음 */}
              {total > 1 && (
                <div className="detail-nav">
                  <button className="btn-secondary detail-nav-btn" disabled={selectedIdx === 0}
                    onClick={() => setSelectedIdx(selectedIdx - 1)}>
                    ← 이전 항목
                  </button>
                  <span className="detail-nav-pos">{selectedIdx + 1} / {total}</span>
                  <button className="btn-secondary detail-nav-btn" disabled={selectedIdx === total - 1}
                    onClick={() => setSelectedIdx(selectedIdx + 1)}>
                    다음 항목 →
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="page-actions">
        <button className="btn-secondary" onClick={handleNewAnalysis}>← 새 분석 시작</button>
        <div style={{ display: 'flex', gap: 10 }}>
          <button className="btn-secondary" onClick={handleItemPDF} disabled={!!pdfLoading}
            style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            현재 항목 PDF
          </button>
          <button className="btn-primary" onClick={handleFullPDF} disabled={!!pdfLoading}
            style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            {pdfLoading === 'full' ? '생성 중...' : '전체 보고서 PDF'}
          </button>
        </div>
      </div>
    </div>
  )
}
