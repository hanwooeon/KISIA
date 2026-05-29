import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { downloadFullPDF, downloadItemPDF } from '../utils/generatePDF'
import './ResultReportPage.css'

const RISK = {
  LOW:      { label: '양호',   color: '#059669', bg: '#DCFCE7', border: '#86EFAC' },
  MEDIUM:   { label: '주의',   color: '#D97706', bg: '#FEF3C7', border: '#FDE68A' },
  HIGH:     { label: '미흡',   color: '#DC2626', bg: '#FEE2E2', border: '#FCA5A5' },
  CRITICAL: { label: '불량',   color: '#7C2D12', bg: '#FEF2F2', border: '#FECACA' },
}

function getRiskLevel(guide_sim, req_sim, compliant) {
  if (compliant) return 'LOW'
  if (guide_sim < 0.6 && req_sim < 0.55) return 'CRITICAL'
  if (guide_sim < 0.65 || req_sim < 0.58) return 'HIGH'
  return 'MEDIUM'
}

function generateDetailedReason(ctrl_name, guide_sim, req_sim, compliant) {
  const g = (guide_sim * 100).toFixed(0)
  const r = (req_sim * 100).toFixed(0)
  if (compliant) {
    return `제출된 증적자료는 「${ctrl_name}」 항목의 인증기준을 충족하는 것으로 판단됩니다. 가이드라인 유사도(${g}%)가 기준치(70%)를 상회하고, 필수확인요소 유사도(${r}%)가 기준치(65%)를 만족하여 해당 항목의 이행 여부가 충분히 입증되었습니다.`
  }
  const issues = []
  if (guide_sim < 0.7) issues.push(`가이드라인 유사도(${g}%)가 기준치(70%)에 미달`)
  if (req_sim < 0.65) issues.push(`필수확인요소 유사도(${r}%)가 기준치(65%)에 미달`)
  return `제출된 증적자료는 「${ctrl_name}」 항목의 인증기준을 충족하지 못하는 것으로 판단됩니다. ${issues.join(', ')}하여 현재 증적만으로는 해당 항목의 이행 여부를 충분히 입증하기 어렵습니다. 하기 개선 권고사항을 참고하여 증적을 보완하시기 바랍니다.`
}

function generateImprovement(ctrl_name, required_elements) {
  return `「${ctrl_name}」 항목의 필수확인요소를 충족하는 내용이 포함된 증적자료를 추가 제출하거나 기존 증적을 보완하시기 바랍니다. 특히 아래 필수확인요소에 대한 구체적인 이행 내역이 명시된 문서(정책서, 지침, 절차서, 수행 기록 등)를 확보하여 제출하시기 권고드립니다.`
}

function generateMockResults(selectedControls, files) {
  return (selectedControls || []).map(ctrl => {
    const guide_sim = +(Math.random() * 0.4 + 0.55).toFixed(2)
    const req_sim = +(Math.random() * 0.4 + 0.5).toFixed(2)
    const compliant = guide_sim >= 0.7 && req_sim >= 0.65
    const riskLevel = getRiskLevel(guide_sim, req_sim, compliant)

    const elem_results = (ctrl.required_elements || []).map(el => ({
      element: el,
      met: compliant ? true : Math.random() > 0.5,
    }))

    return {
      control_id: ctrl.control_id,
      control_name: ctrl.control_name,
      category: ctrl.category,
      keywords: ctrl.keywords || [],
      evidence_name: files?.[ctrl.control_id]?.name || '증적파일',
      guide_similarity: guide_sim,
      required_similarity: req_sim,
      is_compliant: compliant,
      risk_level: riskLevel,
      elem_results,
      judgment_reason: generateDetailedReason(ctrl.control_name, guide_sim, req_sim, compliant),
      improvement: compliant ? null : generateImprovement(ctrl.control_name, ctrl.required_elements),
      top_chunks: [
        { chunk_id: 'c1', content: '관련 가이드라인 청크 내용 샘플', similarity_score: +(guide_sim - 0.05).toFixed(2) },
        { chunk_id: 'c2', content: '필수확인요소 청크 내용 샘플', similarity_score: +(req_sim - 0.03).toFixed(2) },
      ],
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

export default function ResultReportPage({ taskId, selectedControls, uploadedFiles, onSaveHistory, onNewAnalysis }) {
  const navigate = useNavigate()
  const [selectedIdx, setSelectedIdx] = useState(0)
  const [chunksOpen, setChunksOpen] = useState(false)
  const [pdfLoading, setPdfLoading] = useState(null)
  const savedRef = useRef(false)
  const resultsRef = useRef(null)

  if (!resultsRef.current) {
    resultsRef.current = generateMockResults(selectedControls, uploadedFiles)
  }
  const results = resultsRef.current

  const dateStr = new Date().toLocaleString('ko-KR', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit'
  })

  useEffect(() => {
    if (!savedRef.current && results.length > 0) {
      savedRef.current = true
      const compliantCount = results.filter(r => r.is_compliant).length
      onSaveHistory?.({
        id: Date.now(),
        date: new Date().toISOString(),
        results: results.map(r => ({
          control_id: r.control_id,
          control_name: r.control_name,
          category: r.category,
          is_compliant: r.is_compliant,
          risk_level: r.risk_level,
          guide_similarity: r.guide_similarity,
          required_similarity: r.required_similarity,
        })),
        summary: {
          total: results.length,
          compliant: compliantCount,
          rate: results.length > 0 ? Math.round((compliantCount / results.length) * 100) : 0,
        },
      })
    }
  }, [])

  if (!selectedControls || selectedControls.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '80px 24px' }}>
        <div style={{ fontSize: '3rem', marginBottom: 16 }}>📋</div>
        <p style={{ color: '#64748B', marginBottom: 20 }}>분석 결과가 없습니다.</p>
        <button className="btn-primary" onClick={() => navigate('/')}>처음부터 시작하기</button>
      </div>
    )
  }

  const compliantCount = results.filter(r => r.is_compliant).length
  const total = results.length
  const rate = total > 0 ? Math.round((compliantCount / total) * 100) : 0
  const detail = results[selectedIdx]
  const riskInfo = RISK[detail?.risk_level || 'LOW']

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
        <div className="summary-card card non-card">
          <span className="summary-label">부적합</span>
          <span className="summary-big red">{total - compliantCount}</span>
          <span className="summary-unit">개</span>
        </div>
        <div className="summary-card card rate-card">
          <span className="summary-label">적합률</span>
          <span className="summary-big blue">{rate}</span>
          <span className="summary-unit">%</span>
          <div className="rate-bar"><div className="rate-fill" style={{ width: `${rate}%` }} /></div>
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
            const ri = RISK[r.risk_level]
            return (
              <div
                key={idx}
                className={`result-list-item ${idx === selectedIdx ? 'rli-active' : ''} ${r.is_compliant ? 'rli-ok' : 'rli-fail'}`}
                onClick={() => { setSelectedIdx(idx); setChunksOpen(false) }}
              >
                <span className="rli-dot" style={{ background: ri.color }} />
                <div className="rli-text">
                  <span className="rli-id">{r.control_id}</span>
                  <span className="rli-name">{r.control_name}</span>
                </div>
                <span className="rli-risk-badge" style={{ background: ri.bg, color: ri.color, border: `1px solid ${ri.border}` }}>
                  {ri.label}
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
                  <span className="detail-risk-badge" style={{ background: riskInfo.bg, color: riskInfo.color, border: `1.5px solid ${riskInfo.border}` }}>
                    위험도: {riskInfo.label}
                  </span>
                  <span className={`badge ${detail.is_compliant ? 'badge-compliant' : 'badge-non-compliant'}`}>
                    {detail.is_compliant ? '✓ 적합' : '✕ 부적합'}
                  </span>
                </div>
              </div>

              {/* 증적파일 */}
              <div className="detail-evidence-row">
                <span className="detail-ev-label">제출 증적</span>
                <span className="detail-ev-name">📄 {detail.evidence_name}</span>
              </div>

              {/* 유사도 게이지 */}
              <div className="detail-section">
                <div className="detail-section-title">유사도 분석</div>
                <div className="detail-scores">
                  <ScoreGauge
                    label="가이드라인 유사도"
                    score={detail.guide_similarity}
                    threshold={0.7}
                    color={detail.guide_similarity >= 0.7 ? '#059669' : '#DC2626'}
                  />
                  <ScoreGauge
                    label="필수확인요소 유사도"
                    score={detail.required_similarity}
                    threshold={0.65}
                    color={detail.required_similarity >= 0.65 ? '#059669' : '#DC2626'}
                  />
                </div>
              </div>

              {/* 판단 근거 */}
              <div className="detail-section">
                <div className="detail-section-title">판단 근거</div>
                <div className="detail-reason-box">
                  <p>{detail.judgment_reason}</p>
                </div>
              </div>

              {/* 필수확인요소 충족 현황 */}
              {detail.elem_results?.length > 0 && (
                <div className="detail-section">
                  <div className="detail-section-title">필수확인요소 충족 현황</div>
                  <div className="elem-list">
                    {detail.elem_results.map((el, i) => (
                      <div key={i} className={`elem-item ${el.met ? 'elem-ok' : 'elem-fail'}`}>
                        <span className={`elem-status-badge ${el.met ? 'elem-badge-ok' : 'elem-badge-fail'}`}>
                          {el.met ? '양호' : '미흡'}
                        </span>
                        <span className="elem-text">{el.element}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 개선 권고사항 */}
              {detail.improvement && (
                <div className="detail-section">
                  <div className="detail-section-title warn">개선 권고사항</div>
                  <div className="detail-improvement">
                    <div className="improvement-icon">⚠</div>
                    <p>{detail.improvement}</p>
                  </div>
                </div>
              )}

              {/* 청크 */}
              <button className="chunk-toggle" onClick={() => setChunksOpen(v => !v)}>
                {chunksOpen ? '▲ 참조 청크 숨기기' : '▼ 참조 청크 보기'}
              </button>
              {chunksOpen && (
                <div className="chunk-list">
                  {detail.top_chunks.map(c => (
                    <div key={c.chunk_id} className="chunk-row">
                      <span className="chunk-score-badge">{(c.similarity_score * 100).toFixed(1)}%</span>
                      <span className="chunk-text">{c.content}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* 이전/다음 */}
              <div className="detail-nav">
                <button className="btn-secondary detail-nav-btn" disabled={selectedIdx === 0}
                  onClick={() => { setSelectedIdx(selectedIdx - 1); setChunksOpen(false) }}>
                  ← 이전 항목
                </button>
                <span className="detail-nav-pos">{selectedIdx + 1} / {total}</span>
                <button className="btn-secondary detail-nav-btn" disabled={selectedIdx === total - 1}
                  onClick={() => { setSelectedIdx(selectedIdx + 1); setChunksOpen(false) }}>
                  다음 항목 →
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="page-actions">
        <button className="btn-secondary" onClick={handleNewAnalysis}>← 새 분석 시작</button>
        <div style={{ display: 'flex', gap: 10 }}>
          <button className="btn-secondary" onClick={handleItemPDF} disabled={!!pdfLoading}
            style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            {pdfLoading === 'item' ? '⏳' : '📄'} 현재 항목 PDF
          </button>
          <button className="btn-primary" onClick={handleFullPDF} disabled={!!pdfLoading}
            style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            {pdfLoading === 'full' ? '⏳ 생성 중...' : '📋 전체 보고서 PDF'}
          </button>
        </div>
      </div>
    </div>
  )
}
