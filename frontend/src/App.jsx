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
  const [apiResults, setApiResults] = useState(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [historyResults, setHistoryResults] = useState(null)
  const [analyses, setAnalyses] = useState(() => {
    try { return JSON.parse(localStorage.getItem('kisia_history') || '[]') } catch { return [] }
  })

  const handleAnalysisComplete = (id, controls, files, results) => {
    setTaskId(id)
    setUploadedFiles(files || {})
    setApiResults(results || null)
  }

  const handleSaveHistory = (entry) => {
    const newHistory = [entry, ...analyses].slice(0, 50)
    setAnalyses(newHistory)
    localStorage.setItem('kisia_history', JSON.stringify(newHistory))
  }

  const handleViewHistory = (entry) => {
    if (entry.fullResults?.length > 0) {
      setHistoryResults(entry.fullResults)
      setSelectedControls(entry.fullResults.map(r => ({
        control_id: r.control_id,
        control_name: r.control_name,
        category: r.category || '',
        keywords: r.keywords || [],
      })))
      setTaskId('history')
      setApiResults(null)
    }
  }

  const handleNewAnalysis = () => {
    setSelectedControls([])
    setTaskId(null)
    setUploadedFiles({})
    setHistoryResults(null)
    setApiResults(null)
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
      <Layout maxStep={maxStep} historyCount={analyses.length} onNewAnalysis={handleNewAnalysis} isAnalyzing={isAnalyzing}>
        <Routes>
          <Route path="/" element={<HomePage lastAnalysis={analyses[0]} />} />
          <Route path="/select" element={<ControlSelectPage onSelectControls={setSelectedControls} />} />
          <Route path="/upload" element={
            <EvidenceUploadPage selectedControls={selectedControls} onAnalysisComplete={handleAnalysisComplete} onAnalyzingChange={setIsAnalyzing} />
          } />
          <Route path="/result" element={
            <ResultReportPage taskId={taskId} selectedControls={selectedControls}
              uploadedFiles={uploadedFiles} apiResults={apiResults}
              historyResults={historyResults}
              onSaveHistory={handleSaveHistory} onNewAnalysis={handleNewAnalysis} />
          } />
          <Route path="/history" element={
            <HistoryPage analyses={analyses} onDelete={handleDeleteHistory} onClearAll={handleClearAllHistory} onViewHistory={handleViewHistory} onNewAnalysis={handleNewAnalysis} />
          } />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}
