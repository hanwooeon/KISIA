import { useState } from 'react'
import { HashRouter as BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import ControlSelectPage from './pages/ControlSelectPage'
import EvidenceUploadPage from './pages/EvidenceUploadPage'
import ResultReportPage from './pages/ResultReportPage'
import HistoryPage from './pages/HistoryPage'

export default function App() {
  const [selectedControls, setSelectedControls] = useState([])
  const [taskId, setTaskId] = useState(null)
  const [uploadedFiles, setUploadedFiles] = useState({})
  const [analyses, setAnalyses] = useState(() => {
    try { return JSON.parse(localStorage.getItem('kisia_history') || '[]') } catch { return [] }
  })

  const handleAnalysisComplete = (id, controls, files) => {
    setTaskId(id)
    setUploadedFiles(files || {})
  }

  const handleSaveHistory = (entry) => {
    const newHistory = [entry, ...analyses].slice(0, 50)
    setAnalyses(newHistory)
    localStorage.setItem('kisia_history', JSON.stringify(newHistory))
  }

  const handleNewAnalysis = () => {
    setSelectedControls([])
    setTaskId(null)
    setUploadedFiles({})
  }

  const handleDeleteHistory = (id) => {
    const newHistory = analyses.filter(a => a.id !== id)
    setAnalyses(newHistory)
    localStorage.setItem('kisia_history', JSON.stringify(newHistory))
  }

  const handleClearAllHistory = () => {
    setAnalyses([])
    localStorage.removeItem('kisia_history')
  }

  const maxStep = taskId ? 2 : selectedControls.length > 0 ? 1 : 0

  return (
    <BrowserRouter>
      <Layout maxStep={maxStep} historyCount={analyses.length} onNewAnalysis={handleNewAnalysis}>
        <Routes>
          <Route path="/" element={<HomePage lastAnalysis={analyses[0]} />} />
          <Route path="/select" element={<ControlSelectPage onSelectControls={setSelectedControls} />} />
          <Route path="/upload" element={
            <EvidenceUploadPage selectedControls={selectedControls} onAnalysisComplete={handleAnalysisComplete} />
          } />
          <Route path="/result" element={
            <ResultReportPage taskId={taskId} selectedControls={selectedControls}
              uploadedFiles={uploadedFiles} onSaveHistory={handleSaveHistory} onNewAnalysis={handleNewAnalysis} />
          } />
          <Route path="/history" element={
            <HistoryPage analyses={analyses} onDelete={handleDeleteHistory} onClearAll={handleClearAllHistory} />
          } />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}
