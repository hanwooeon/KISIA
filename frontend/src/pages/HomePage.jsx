import { useNavigate } from 'react-router-dom'
import './HomePage.css'

export default function HomePage({ lastAnalysis }) {
  const navigate = useNavigate()

  const lastDate = lastAnalysis
    ? new Date(lastAnalysis.date).toLocaleDateString('ko-KR', { year:'numeric', month:'2-digit', day:'2-digit' })
    : null

  return (
    <div className="home-wrap">

      {/* 중앙 패널 */}
      <div className="home-center">

        {/* 로고 */}
        <div className="home-logo-area">
          <div className="home-logo-icon">K</div>
          <div className="home-logo-texts">
            <div className="home-logo-title">KISIA ISMS-P</div>
            <div className="home-logo-sub">증적 자동 점검 도구</div>
          </div>
        </div>

        {/* 상태 카드 */}
        <div className="home-status-row">
          <div className="home-stat-card">
            <div className="home-stat-val">62</div>
            <div className="home-stat-label">점검 항목</div>
          </div>
          <div className="home-stat-card">
            <div className="home-stat-val">ISMS-P</div>
            <div className="home-stat-label">인증 기준</div>
          </div>
          <div className="home-stat-card">
            <div className="home-stat-val" style={{ fontSize: lastDate ? '1rem' : '1.4rem' }}>
              {lastDate ?? '—'}
            </div>
            <div className="home-stat-label">최근 점검일</div>
          </div>
        </div>

        {/* 구분선 */}
        <div className="home-divider" />

        {/* 설명 */}
        <p className="home-desc">
          300억 미만 중소기업 간편인증 대상 62개 항목에 대해<br/>
          증적 파일을 업로드하면 AI가 자동으로 적합 여부를 판단합니다.
        </p>

        {/* 메인 버튼 */}
        <button className="home-start-btn" onClick={() => navigate('/select')}>
          <span>점검 시작하기</span>
          <span className="home-start-arrow">→</span>
        </button>

        {lastAnalysis && (
          <button className="home-history-btn" onClick={() => navigate('/history')}>
            이전 점검 내역 보기
          </button>
        )}
      </div>

      {/* 하단 정보 */}
      <div className="home-footer-info">
        <span>300억 미만 중소기업 간편인증 · ISMS-P 2024</span>
      </div>
    </div>
  )
}
