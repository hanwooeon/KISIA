import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import './Layout.css'

const steps = [
  { path: '/select', num: '01', label: '항목 선택'   },
  { path: '/upload', num: '02', label: '증적 업로드' },
  { path: '/result', num: '03', label: '결과 보고서' },
]

export default function Layout({ children, maxStep = 0, historyCount = 0, onNewAnalysis }) {
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
          <span className="title-text">ISMS-P 증적 자동 점검 시스템</span>
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
          <div className="sidebar-logo">
            <div className="sidebar-logo-icon">K</div>
            <div className="sidebar-logo-texts">
              <div className="sidebar-logo-title">KISIA</div>
              <div className="sidebar-logo-sub">증적 자동 점검</div>
            </div>
          </div>

          <div className="sidebar-section-label">점검 단계</div>

          <nav className="sidebar-steps">
            {steps.map((step, idx) => {
              const isActive = location.pathname === step.path
              const isDone   = idx < currentIdx
              const isLocked = idx > maxStep || (maxStep === 2 && idx < 2)

              if (isLocked) {
                return (
                  <div key={step.path} className="sidebar-step sidebar-step-locked">
                    <div className="step-num-badge">{step.num}</div>
                    <div className="step-label">{step.label}</div>
                    <div className="step-lock-icon">🔒</div>
                  </div>
                )
              }

              return (
                <Link
                  key={step.path}
                  to={step.path}
                  className={`sidebar-step ${isActive ? 'sidebar-step-active' : ''} ${isDone ? 'sidebar-step-done' : ''}`}
                  onClick={() => { if (idx === 0 && currentIdx === 2) onNewAnalysis?.() }}
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
            className={`sidebar-history-btn ${isHistoryPage ? 'active' : ''}`}>
            <span>📋</span>
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
