import axios from 'axios'

// Electron 빌드 환경에서는 직접 localhost:8000 사용, dev는 vite 프록시 사용
const BASE_URL = window?.location?.protocol === 'file:' ? 'http://localhost:8000' : '/api'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
})

// A팀 지식DB에서 항목 목록 조회
export const getControls = () => api.get('/controls')
export const getControl = (controlId) => api.get(`/controls/${controlId}`)

// B팀 증적 업로드 API
const evidenceApi = axios.create({
  baseURL: BASE_URL,
  timeout: 60000,
})

export const uploadEvidence = (userId, controlId, file) => {
  const formData = new FormData()
  formData.append('user_id', userId)
  formData.append('control_id', controlId)
  formData.append('file', file)
  return evidenceApi.post('/evidence/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// C파트: 코사인 유사도 + LLM 분석 요청
export const startAnalysis = (userId, controlIds, evidenceIds) =>
  api.post('/analyze', { user_id: userId, control_ids: controlIds, evidence_ids: evidenceIds })

// C파트: 결과 조회
export const getResult = (taskId) => api.get(`/results/${taskId}`)
