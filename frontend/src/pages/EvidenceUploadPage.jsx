import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import './EvidenceUploadPage.css'

const BASE_URL = window?.location?.protocol === 'file:' ? 'http://localhost:8000' : '/api'

export default function EvidenceUploadPage({ selectedControls, onAnalysisComplete, onAnalyzingChange }) {
  const [files, setFiles] = useState({})         // { controlId: [file, ...] }
  const [uploadIds, setUploadIds] = useState({})  // { controlId: [{ temp_id, filename }, ...] }
  const [uploadStatus, setUploadStatus] = useState({})
  const [dragging, setDragging] = useState(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [errorMsg, setErrorMsg] = useState(null)
  const fileRefs = useRef({})
  const navigate = useNavigate()

  if (!selectedControls || selectedControls.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '80px 24px' }}>
        <div style={{ width: 48, height: 48, borderRadius: 12, background: '#FEF3C7', margin: '0 auto 16px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#D97706" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        </div>
        <p style={{ color: '#64748B', marginBottom: 20 }}>선택된 항목이 없습니다.</p>
        <button className="btn-primary" onClick={() => navigate('/')}>항목 선택으로 돌아가기</button>
      </div>
    )
  }

  const handleFiles = async (controlId, newFiles) => {
    if (!newFiles || newFiles.length === 0) return
    setUploadStatus(prev => ({ ...prev, [controlId]: 'uploading' }))
    setErrorMsg(null)

    const fileArray = Array.from(newFiles)
    const newNos = []

    for (const file of fileArray) {
      try {
        const formData = new FormData()
        formData.append('control_id', controlId)
        formData.append('file', file)
        const res = await axios.post(`${BASE_URL}/evidence/upload`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
        newNos.push({ temp_id: res.data.temp_id, filename: file.name })
      } catch (err) {
        setUploadStatus(prev => ({ ...prev, [controlId]: 'error' }))
        setErrorMsg(`${controlId} - ${file.name} 업로드 실패: ${err.response?.data?.detail || err.message}`)
        return
      }
    }

    setFiles(prev => ({ ...prev, [controlId]: [...(prev[controlId] || []), ...fileArray] }))
    setUploadIds(prev => ({ ...prev, [controlId]: [...(prev[controlId] || []), ...newNos] }))
    setUploadStatus(prev => ({ ...prev, [controlId]: 'done' }))
  }

  const removeFile = (controlId, fileIndex) => {
    setFiles(prev => {
      const updated = [...(prev[controlId] || [])]
      updated.splice(fileIndex, 1)
      return { ...prev, [controlId]: updated }
    })
    setUploadIds(prev => {
      const updated = [...(prev[controlId] || [])]
      updated.splice(fileIndex, 1)
      if (updated.length === 0) {
        const { [controlId]: _, ...rest } = prev
        return rest
      }
      return { ...prev, [controlId]: updated }
    })
    setUploadStatus(prev => {
      const remaining = (files[controlId] || []).length - 1
      if (remaining <= 0) {
        const { [controlId]: _, ...rest } = prev
        return rest
      }
      return prev
    })
  }

  const handleDrop = (e, controlId) => {
    e.preventDefault()
    setDragging(null)
    handleFiles(controlId, e.dataTransfer.files)
  }

  const handleAnalyze = async () => {
    if (Object.keys(uploadIds).length === 0) return
    setAnalyzing(true)
    onAnalyzingChange?.(true)
    setErrorMsg(null)

    // 업로드된 파일 목록 생성
    const items = Object.entries(uploadIds).flatMap(([controlId, fileList]) =>
      fileList.map(f => ({ temp_id: f.temp_id, filename: f.filename, control_id: controlId }))
    )

    try {
      const res = await axios.post(`${BASE_URL}/analyze`, {
        items,
        control_ids: selectedControls.map(c => c.control_id),
      })

      onAnalysisComplete(null, selectedControls, files, res.data.results)
      navigate('/result')
    } catch (err) {
      setErrorMsg(`분석 실패: ${err.response?.data?.detail || err.message}`)
    } finally {
      setAnalyzing(false)
      onAnalyzingChange?.(false)
    }
  }

  const uploadedCount = Object.keys(uploadIds).length  // 항목 기준 (몇 개 항목에 업로드됐는지)

  if (analyzing) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '60vh', gap: 14 }}>
        <div className="analyze-spinner" />
        <p style={{ fontSize: '1rem', fontWeight: 700, color: '#1E293B', margin: 0 }}>점검 중입니다</p>
        <p style={{ fontSize: '0.82rem', color: '#94A3B8', margin: 0 }}>파일 크기에 따라 수 분이 소요될 수 있습니다</p>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">증적 파일 업로드</h2>
        <p className="page-desc">
          선택한 {selectedControls.length}개 항목에 대한 증적 파일을 업로드하세요.
          PDF, Word(DOCX), 엑셀(XLSX) 파일을 지원합니다.
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
                {status === 'done' && <span className="badge" style={{ background: '#EEF2FF', color: '#4F46E5', border: '1px solid #C7D2FE' }}>업로드 완료</span>}
                {status === 'uploading' && <span className="badge" style={{ background: '#FEF3C7', color: '#B45309' }}>업로드 중</span>}
                {status === 'error' && <span className="badge badge-non-compliant">오류</span>}
              </div>

              <div
                className={`drop-zone ${dragging === controlId ? 'drag-over' : ''} ${status === 'done' ? 'drop-done' : ''}`}
                onDragOver={e => { e.preventDefault(); setDragging(controlId) }}
                onDragLeave={() => setDragging(null)}
                onDrop={e => handleDrop(e, controlId)}
                onClick={() => fileRefs.current[controlId]?.click()}
              >
                {status === 'done' && files[controlId]?.length > 0 ? (
                  <div className="drop-done-content">
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 3, width: '100%' }}>
                      {files[controlId].map((f, i) => (
                        <div key={i} className="drop-file-row">
                          <span className="drop-filename">{f.name}</span>
                          <button
                            className="drop-file-remove"
                            title="파일 삭제"
                            onClick={e => { e.stopPropagation(); removeFile(controlId, i) }}
                          >✕</button>
                        </div>
                      ))}
                    </div>
                    <span className="drop-replace">클릭하여 추가 업로드</span>
                  </div>
                ) : (
                  <div className="drop-empty-content">
                    <div className="drop-upload-icon">
                      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                        <polyline points="17 8 12 3 7 8"/>
                        <line x1="12" y1="3" x2="12" y2="15"/>
                      </svg>
                    </div>
                    <p className="drop-text">파일을 드래그하거나 클릭하여 업로드</p>
                    <p className="drop-hint">PDF · DOCX · XLSX · 여러 파일 동시 업로드 가능</p>
                  </div>
                )}
              </div>

              <input
                type="file"
                ref={el => fileRefs.current[controlId] = el}
                style={{ display: 'none' }}
                accept=".pdf,.docx,.xlsx"
                multiple
                onChange={e => handleFiles(controlId, e.target.files)}
              />
            </div>
          )
        })}
      </div>

      {errorMsg && (
        <div style={{ margin: '12px 0', padding: '10px 14px', background: '#FEF2F2', border: '1px solid #FCA5A5', borderRadius: 8, color: '#DC2626', fontSize: '0.82rem' }}>
          {errorMsg}
        </div>
      )}

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
            {analyzing ? '분석 중...' : '분석 시작 →'}
          </button>
        </div>
      </div>
    </div>
  )
}
