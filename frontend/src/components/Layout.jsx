import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import './Layout.css'

const steps = [
  { path: '/select', num: '01', label: '항목 선택'   },
  { path: '/upload', num: '02', label: '증적 업로드' },
  { path: '/result', num: '03', label: '결과 보고서' },
]

export default function Layout({ children, maxStep = 0, historyCount = 0, onNewAnalysis, isAnalyzing = false }) {
  const location = useLocation()
  const [isMaximized, setIsMaximized] = useState(false)
  const currentIdx = steps.findIndex(s => s.path === location.pathname)
  const isHistoryPage = location.pathname === '/history'

  useEffect(() => {
    window.electronAPI?.onMaximizeChange?.(setIsMaximized)
  }, [])

  return (
    <div className="app-frame">

      {/* 커스텀 타이틀바 */}
      <div className="title-bar">
        <div className="title-bar-drag">
          <span className="title-badge">KISIA</span>
          <span className="title-text">ISMS-P 증적 자동 점검 도구</span>
        </div>
        <div className="title-bar-controls">
          <button className="wc-btn wc-min"
            onClick={() => window.electronAPI?.minimize()}>─</button>
          <button className="wc-btn wc-max"
            onClick={() => window.electronAPI?.maximize()}>
            {isMaximized ? '❐' : '□'}
          </button>
          <button className="wc-btn wc-close"
            onClick={() => window.electronAPI?.close()}>✕</button>
        </div>
      </div>

      <div className="app-body">

        {/* 사이드바 */}
        <aside className="sidebar">
          <div className="sidebar-section-label">점검 단계</div>

          {isAnalyzing && (
            <div className="sidebar-analyzing-notice">
              <span className="sidebar-analyzing-dot" />
              점검 진행 중…
            </div>
          )}

          <nav className="sidebar-steps">
            {steps.map((step, idx) => {
              const isActive = location.pathname === step.path
              const isDone   = idx < currentIdx
              const isLocked = isAnalyzing || idx > maxStep || (maxStep === 2 && idx < 2)

              if (isLocked) {
                return (
                  <div key={step.path} className={`sidebar-step sidebar-step-locked ${isAnalyzing ? 'sidebar-step-analyzing' : ''}`}>
                    <div className="step-num-badge">{step.num}</div>
                    <div className="step-label">{step.label}</div>
                  </div>
                )
              }

              return (
                <Link
                  key={step.path}
                  to={step.path}
                  className={`sidebar-step ${isActive ? 'sidebar-step-active' : ''} ${isDone ? 'sidebar-step-done' : ''}`}
                  onClick={() => { if (idx === 0 && (currentIdx === 2 || isHistoryPage)) onNewAnalysis?.() }}
                >
                  {isActive && <div className="step-active-indicator" />}
                  <div className="step-num-badge">{step.num}</div>
                  <div className="step-label-wrap">
                    <div className="step-label">{step.label}</div>
                    {isDone && <div className="step-done-tag">✓ 완료</div>}
                  </div>
                </Link>
              )
            })}
          </nav>

          <div className="sidebar-divider" />

          <Link to="/history"
            className={`sidebar-history-btn ${isHistoryPage ? 'active' : ''} ${isAnalyzing ? 'sidebar-history-disabled' : ''}`}
            onClick={e => isAnalyzing && e.preventDefault()}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
                <path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z"/>
              </svg>
            <span>점검 내역</span>
            {historyCount > 0 && (
              <span className="sidebar-history-count">{historyCount}</span>
            )}
          </Link>

          <div className="sidebar-footer">v0.1.0 · KISIA 2025</div>
        </aside>

        {/* 메인 콘텐츠 */}
        <main className="app-main">
          {children}
        </main>

      </div>
    </div>
  )
}
