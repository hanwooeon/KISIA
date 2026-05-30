import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import './HistoryPage.css'

function formatDate(iso) {
  const d = new Date(iso)
  return `${d.getFullYear()}. ${String(d.getMonth()+1).padStart(2,'0')}. ${String(d.getDate()).padStart(2,'0')}  ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

export default function HistoryPage({ analyses, onDelete, onClearAll, onViewHistory, onNewAnalysis }) {
  const navigate = useNavigate()
  const [expanded, setExpanded] = useState({})
  const [confirmClear, setConfirmClear] = useState(false)

  if (!analyses || analyses.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '80px 24px' }}>
        <div style={{ width: 48, height: 48, borderRadius: 12, background: '#F1F5F9', margin: '0 auto 20px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#94A3B8" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M3 7a2 2 0 012-2h3l2 2h7a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"/></svg>
        </div>
        <p style={{ color: '#94A3B8', fontSize: '1rem', marginBottom: 24 }}>아직 점검 내역이 없습니다.</p>
        <button className="btn-primary" onClick={() => navigate('/')}>첫 번째 점검 시작하기</button>
      </div>
    )
  }

  const handleView = (entry) => {
    if (!entry.fullResults) {
      alert('이전 버전에서 저장된 내역은 상세 보기를 지원하지 않습니다.\n새로 점검을 진행해주세요.')
      return
    }
    onViewHistory(entry)
    navigate('/result')
  }

  return (
    <div>
      <div className="page-header" style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start' }}>
        <div>
          <h2 className="page-title">점검 내역</h2>
          <p className="page-desc">지금까지 수행한 ISMS-P 증적 점검 결과 기록입니다.</p>
        </div>
        <div style={{ display:'flex', alignItems:'center', gap:10 }}>
          {confirmClear ? (
            <>
              <span style={{ fontSize:'0.82rem', color:'#DC2626', fontWeight:600 }}>전체 삭제하시겠습니까?</span>
              <button className="btn-secondary" style={{ padding:'7px 14px', fontSize:'0.82rem', color:'#DC2626', borderColor:'#FCA5A5' }}
                onClick={() => { onClearAll(); setConfirmClear(false) }}>확인</button>
              <button className="btn-secondary" style={{ padding:'7px 14px', fontSize:'0.82rem' }}
                onClick={() => setConfirmClear(false)}>취소</button>
            </>
          ) : (
            <button className="btn-secondary" style={{ padding:'7px 14px', fontSize:'0.82rem', color:'#94A3B8', borderColor:'#E2E8F0' }}
              onClick={() => setConfirmClear(true)}>전체 삭제</button>
          )}
        </div>
      </div>

      <div className="history-list">
        {analyses.map((entry, idx) => {
          const isOpen = expanded[idx]
          const { summary, results, date } = entry
          return (
            <div key={entry.id} className="history-entry card">
              <div className="history-entry-top">
                {/* 왼쪽: 번호 + 날짜 + 결과 보기 버튼 */}
                <div
                  className="history-entry-left"
                  onClick={() => setExpanded(prev => ({ ...prev, [idx]: !prev[idx] }))}
                  style={{ flex:1, cursor:'pointer' }}
                >
                  <span className="history-num">#{analyses.length - idx}</span>
                  <div className="history-entry-meta">
                    <span className="history-date">{formatDate(date)}</span>
                    <span className="history-items">{summary.total}개 항목 점검</span>
                  </div>
                </div>

                {/* 오른쪽: 통계 + 결과 보기 + 삭제 */}
                <div className="history-entry-stats">
                  <div className="hstat hstat-ok">
                    <span className="hstat-val">{summary.compliant}</span>
                    <span className="hstat-label">적합</span>
                  </div>
                  <div className="hstat hstat-fail">
                    <span className="hstat-val">{summary.total - summary.compliant}</span>
                    <span className="hstat-label">부적합</span>
                  </div>
                  <div className="hstat hstat-rate">
                    <span className="hstat-val">{summary.rate}%</span>
                    <span className="hstat-label">적합률</span>
                  </div>
                  <div className="history-rate-bar">
                    <div className="history-rate-fill" style={{ width:`${summary.rate}%` }} />
                  </div>

                  {/* 결과 보기 버튼 */}
                  <button
                    className="history-view-btn"
                    onClick={(e) => { e.stopPropagation(); handleView(entry) }}
                    title="상세 결과 보기"
                  >결과 보기</button>

                  <button
                    className="history-expand-btn"
                    onClick={() => setExpanded(prev => ({ ...prev, [idx]: !prev[idx] }))}
                  >{isOpen ? '▲' : '▼'}</button>
                  <button
                    className="history-delete-btn"
                    onClick={(e) => { e.stopPropagation(); onDelete(entry.id) }}
                    title="삭제"
                  >✕</button>
                </div>
              </div>

              {/* 펼쳤을 때 항목 요약 */}
              {isOpen && (
                <div className="history-detail">
                  <div className="history-detail-grid">
                    {results.map((r, ri2) => (
                      <div key={ri2} className={`history-item ${r.is_compliant ? 'hi-ok' : 'hi-fail'}`}>
                        <div className="hi-top">
                          <span className="hi-id">{r.control_id}</span>
                          <span className={`hi-badge ${r.is_compliant ? 'hi-badge-ok' : 'hi-badge-fail'}`}>
                            {r.is_compliant ? '✓ 적합' : '✕ 부적합'}
                          </span>
                        </div>
                        <div className="hi-name">{r.control_name}</div>
                        <div className="hi-scores">
                          <span className="hi-score" style={{ color: r.guide_similarity >= 0.7 ? '#059669' : '#DC2626' }}>
                            가이드 {(r.guide_similarity * 100).toFixed(0)}%
                          </span>
                          <span className="hi-score" style={{ color: r.required_similarity >= 0.65 ? '#059669' : '#DC2626' }}>
                            핵심요소 {(r.required_similarity * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                  <div style={{ textAlign:'center', marginTop:14 }}>
                    <button className="btn-primary" style={{ fontSize:'0.84rem', padding:'8px 20px' }}
                      onClick={() => handleView(entry)}>
                      상세 결과 보기
                    </button>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      <div className="page-actions">
        <button className="btn-secondary" onClick={() => { onNewAnalysis?.(); navigate('/') }}>← 새 분석 시작</button>
        <span style={{ fontSize:'0.82rem', color:'#94A3B8' }}>총 {analyses.length}건 기록됨</span>
      </div>
    </div>
  )
}
