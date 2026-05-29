import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import './EvidenceUploadPage.css'

export default function EvidenceUploadPage({ selectedControls, onAnalysisComplete }) {
  const [files, setFiles] = useState({})
  const [uploadIds, setUploadIds] = useState({})
  const [uploadStatus, setUploadStatus] = useState({})
  const [dragging, setDragging] = useState(null)
  const [analyzing, setAnalyzing] = useState(false)
  const fileRefs = useRef({})
  const navigate = useNavigate()

  if (!selectedControls || selectedControls.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '80px 24px' }}>
        <div style={{ fontSize: '3rem', marginBottom: 16 }}>⚠️</div>
        <p style={{ color: '#64748B', marginBottom: 20 }}>선택된 항목이 없습니다.</p>
        <button className="btn-primary" onClick={() => navigate('/')}>항목 선택으로 돌아가기</button>
      </div>
    )
  }

  const handleFile = (controlId, file) => {
    if (!file) return
    setFiles(prev => ({ ...prev, [controlId]: file }))
    setUploadStatus(prev => ({ ...prev, [controlId]: 'uploading' }))
    // TODO: B팀 증적 업로드 API 연동
    const mockEvidenceId = `ev_${controlId}_${Date.now()}`
    setUploadIds(prev => ({ ...prev, [controlId]: mockEvidenceId }))
    setUploadStatus(prev => ({ ...prev, [controlId]: 'done' }))
  }

  const handleDrop = (e, controlId) => {
    e.preventDefault()
    setDragging(null)
    handleFile(controlId, e.dataTransfer.files[0])
  }

  const handleAnalyze = () => {
    if (Object.keys(uploadIds).length === 0) return
    setAnalyzing(true)
    setTimeout(() => {
      // TODO: C파트 분석 API 연동
      const mockTaskId = `task_${Date.now()}`
      onAnalysisComplete(mockTaskId, selectedControls, files)
      navigate('/result')
      setAnalyzing(false)
    }, 800)
  }

  const uploadedCount = Object.keys(uploadIds).length

  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">증적 파일 업로드</h2>
        <p className="page-desc">
          선택한 {selectedControls.length}개 항목에 대한 증적 파일을 업로드하세요.
          PDF, 이미지(JPG·PNG·TIFF), Word, TXT 파일을 지원합니다.
        </p>
      </div>

      <div className="selected-controls-bar card">
        <span className="bar-label">선택된 항목</span>
        <div className="bar-chips">
          {selectedControls.map(ctrl => (
            <span key={ctrl.control_id} className="bar-chip">
              {ctrl.control_id} {ctrl.control_name}
            </span>
          ))}
        </div>
      </div>

      <div className="upload-grid">
        {selectedControls.map((ctrl) => {
          const controlId = ctrl.control_id
          const status = uploadStatus[controlId]
          const file = files[controlId]

          return (
            <div key={controlId} className={`upload-card card ${status === 'done' ? 'upload-done' : ''}`}>
              <div className="upload-card-header">
                <div>
                  <span className="upload-control-num">{controlId}</span>
                  <span className="upload-control-name">{ctrl.control_name}</span>
                </div>
                {status === 'done' && <span className="badge badge-compliant">✓ 업로드됨</span>}
                {status === 'uploading' && <span className="badge" style={{ background: '#FEF3C7', color: '#B45309' }}>업로드 중</span>}
                {status === 'error' && <span className="badge badge-non-compliant">실패</span>}
              </div>

              <div
                className={`drop-zone ${dragging === controlId ? 'drag-over' : ''} ${status === 'done' ? 'drop-done' : ''}`}
                onDragOver={e => { e.preventDefault(); setDragging(controlId) }}
                onDragLeave={() => setDragging(null)}
                onDrop={e => handleDrop(e, controlId)}
                onClick={() => fileRefs.current[controlId]?.click()}
              >
                {status === 'done' ? (
                  <div className="drop-done-content">
                    <span className="drop-icon done-icon">📄</span>
                    <span className="drop-filename">{file?.name}</span>
                    <span className="drop-replace">클릭하여 교체</span>
                  </div>
                ) : (
                  <div className="drop-empty-content">
                    <span className="drop-icon">📂</span>
                    <p className="drop-text">파일을 드래그하거나 클릭하여 업로드</p>
                    <p className="drop-hint">PDF · JPG · PNG · TIFF · DOCX · TXT</p>
                  </div>
                )}
              </div>

              <input
                type="file"
                ref={el => fileRefs.current[controlId] = el}
                style={{ display: 'none' }}
                accept=".pdf,.jpg,.jpeg,.png,.tiff,.docx,.txt"
                onChange={e => handleFile(controlId, e.target.files[0])}
              />
            </div>
          )
        })}
      </div>

      <div className="page-actions">
        <button className="btn-secondary" onClick={() => navigate('/')}>← 항목 재선택</button>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div className="progress-text">
            <span className="progress-num">{uploadedCount}</span>
            <span style={{ color: '#94A3B8' }}> / {selectedControls.length} 업로드됨</span>
          </div>
          <button
            className="btn-primary"
            disabled={uploadedCount === 0 || analyzing}
            onClick={handleAnalyze}
          >
            {analyzing ? '⏳ 분석 중...' : '분석 시작 →'}
          </button>
        </div>
      </div>
    </div>
  )
}
