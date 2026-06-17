import React, { useState } from 'react'
import { uploadFile } from '../api/client.js'

const TABS = [
  { key: 'review', label: 'Review', icon: '📝' },
  { key: 'summary', label: 'Summarize', icon: '📋' },
  { key: 'extract', label: 'Extract', icon: '🔍' },
  { key: 'download', label: 'Download', icon: '💾' },
  { key: 'chat', label: 'Chat', icon: '💬' },
]

function ResultBox({ title, content }) {
  if (!content && title !== 'Research Topic') return null
  return (
    <div className="result-box">
      <div className="result-header">
        <span className="result-title">{title}</span>
        {content && (
          <button className="copy-btn" onClick={() => navigator.clipboard.writeText(content)} title="Copy">📋</button>
        )}
      </div>
      {content ? (
        <div className="result-content">{content}</div>
      ) : (
        <div className="result-placeholder">Run a task above to see results here.</div>
      )}
    </div>
  )
}

export default function AgentTabs({ results, onAgentAction, isLoading, onSend, attachedFiles, fileContexts, children }) {
  const [activeTab, setActiveTab] = useState('review')
  const [docText, setDocText] = useState('')
  const [researchTopic, setResearchTopic] = useState('')
  const [processingAction, setProcessingAction] = useState(null)

  const handleFilePick = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const result = await uploadFile(file)
      const ext = file.name.split('.').pop()?.toLowerCase()
      let text = ''
      if (result.extracted_text) {
        text = `--- File: ${file.name} ---\n${result.extracted_text}`
      } else if (['txt', 'md', 'py', 'js', 'json', 'csv', 'html', 'css', 'xml', 'yaml', 'yml'].includes(ext)) {
        text = `--- File: ${file.name} ---\n${await file.text()}`
      } else {
        text = `[File attached: ${file.name}]`
      }
      setDocText(text)
    } catch (err) {
      console.error('Upload failed:', err)
    }
    e.target.value = ''
  }

  const run = async (action, extra = {}) => {
    if (!docText && action !== 'research') return
    setProcessingAction(action)
    try {
      const text = action === 'research' ? researchTopic : docText
      await onAgentAction(action, text, extra)
    } finally {
      setProcessingAction(null)
    }
  }

  const isBusy = isLoading || processingAction !== null

  const renderResult = (key, title) => {
    const content = results[key]
    return <ResultBox title={title} content={content} />
  }

  return (
    <div className="agent-tabs">
      <div className="tabs-header">
        {TABS.map(t => (
          <button
            key={t.key}
            className={`tab-btn ${activeTab === t.key ? 'tab-active' : ''}`}
            onClick={() => setActiveTab(t.key)}
          >
            <span className="tab-icon">{t.icon}</span>
            <span className="tab-label">{t.label}</span>
          </button>
        ))}
      </div>

      <div className="tab-content">
        {activeTab === 'review' && (
          <div className="tab-pane">
            <div className="tab-pane-header">
              <h3>Document Review</h3>
              <p>Check grammar, improve clarity, and enhance writing quality.</p>
            </div>
            <div className="doc-upload-row">
              <input type="file" id="review-upload" onChange={handleFilePick} accept=".txt,.md,.docx,.pdf" hidden />
              <label htmlFor="review-upload" className="upload-label">
                {docText ? '📎 Change document' : '📁 Upload document'}
              </label>
              {docText && <span className="doc-loaded">✓ Document loaded</span>}
            </div>
            <div className="action-grid">
              <button className="action-btn-primary action-blue" onClick={() => run('check')} disabled={isBusy || !docText}>
                {processingAction === 'check' ? '⏳ Analyzing...' : '🔍 Check & Improve Document'}
              </button>
              <button className="action-btn-secondary action-blue" onClick={() => run('check_quick')} disabled={isBusy || !docText}>
                {processingAction === 'check_quick' ? '⏳...' : '💡 Quick Review Tips'}
              </button>
            </div>
            <div className="results-section">
              {renderResult('review', 'Document Analysis')}
            </div>
          </div>
        )}

        {activeTab === 'summary' && (
          <div className="tab-pane">
            <div className="tab-pane-header">
              <h3>Summarization</h3>
              <p>Generate summaries, bullet points, and key takeaways.</p>
            </div>
            <div className="doc-upload-row">
              <input type="file" id="summary-upload" onChange={handleFilePick} accept=".txt,.md,.docx,.pdf" hidden />
              <label htmlFor="summary-upload" className="upload-label">
                {docText ? '📎 Change document' : '📁 Upload document'}
              </label>
              {docText && <span className="doc-loaded">✓ Document loaded</span>}
            </div>
            <div className="action-grid action-grid-3">
              <button className="action-btn-primary action-teal" onClick={() => run('summarize', { style: 'full' })} disabled={isBusy || !docText}>
                {processingAction === 'summarize-full' ? '⏳...' : '📄 Full Summary'}
              </button>
              <button className="action-btn-secondary action-teal" onClick={() => run('summarize', { style: 'bullet' })} disabled={isBusy || !docText}>
                {processingAction === 'summarize-bullet' ? '⏳...' : '🎯 Bullet Points'}
              </button>
              <button className="action-btn-tertiary action-teal" onClick={() => run('summarize', { style: 'quick' })} disabled={isBusy || !docText}>
                {processingAction === 'summarize-quick' ? '⏳...' : '🚀 Quick Summary'}
              </button>
            </div>
            <div className="results-section">
              {renderResult('summary', 'Full Summary')}
              {renderResult('bulletSummary', 'Bullet Points')}
              {renderResult('quickSummary', 'Quick Summary')}
            </div>
          </div>
        )}

        {activeTab === 'extract' && (
          <div className="tab-pane">
            <div className="tab-pane-header">
              <h3>Information Extraction</h3>
              <p>Extract entities, key facts, and generate structured reports.</p>
            </div>
            <div className="doc-upload-row">
              <input type="file" id="extract-upload" onChange={handleFilePick} accept=".txt,.md,.docx,.pdf" hidden />
              <label htmlFor="extract-upload" className="upload-label">
                {docText ? '📎 Change document' : '📁 Upload document'}
              </label>
              {docText && <span className="doc-loaded">✓ Document loaded</span>}
            </div>
            <div className="action-grid">
              <button className="action-btn-primary action-purple" onClick={() => run('extract', { type: 'entities' })} disabled={isBusy || !docText}>
                {processingAction === 'extract-entities' ? '⏳...' : '🎯 Extract Entities & Facts'}
              </button>
              <button className="action-btn-secondary action-purple" onClick={() => run('extract', { type: 'report' })} disabled={isBusy || !docText}>
                {processingAction === 'extract-report' ? '⏳...' : '📊 Generate Report'}
              </button>
            </div>
            <div className="research-section">
              <div className="research-label">🔎 Research Additional Topic</div>
              <div className="research-row">
                <input
                  className="research-input"
                  placeholder="Enter a topic to research..."
                  value={researchTopic}
                  onChange={e => setResearchTopic(e.target.value)}
                  disabled={isBusy}
                />
                <button
                  className="action-btn-primary action-purple"
                  onClick={() => run('extract', { type: 'research', topic: researchTopic })}
                  disabled={isBusy || !researchTopic.trim()}
                >
                  {processingAction === 'extract-research' ? '⏳...' : '🚀 Research'}
                </button>
              </div>
            </div>
            <div className="results-section">
              {renderResult('extract', 'Extracted Information')}
              {renderResult('report', 'Generated Report')}
              {renderResult('research', 'Research Results')}
            </div>
          </div>
        )}

        {activeTab === 'download' && (
          <div className="tab-pane">
            <div className="tab-pane-header">
              <h3>Download Results</h3>
              <p>Save all processed results for later use.</p>
            </div>
            <div className="download-items">
              {[
                { key: 'review', label: 'Document Analysis', file: 'document_analysis.txt' },
                { key: 'summary', label: 'Full Summary', file: 'summary.txt' },
                { key: 'bulletSummary', label: 'Bullet Points', file: 'bullet_points.txt' },
                { key: 'quickSummary', label: 'Quick Summary', file: 'quick_summary.txt' },
                { key: 'extract', label: 'Extracted Info', file: 'extracted_info.txt' },
                { key: 'report', label: 'Report', file: 'report.txt' },
                { key: 'research', label: 'Research Results', file: 'research.txt' },
              ].map(item => {
                const content = results[item.key]
                if (!content) return null
                return (
                  <div key={item.key} className="download-row">
                    <span className="download-row-label">{item.label}</span>
                    <button className="download-row-btn" onClick={() => {
                      const blob = new Blob([content], { type: 'text/plain' })
                      const url = URL.createObjectURL(blob)
                      const a = document.createElement('a')
                      a.href = url; a.download = item.file; a.click()
                      URL.revokeObjectURL(url)
                    }}>
                      📥 Download
                    </button>
                  </div>
                )
              })}
              {!Object.values(results).some(Boolean) && (
                <div className="download-empty">Run a task in Review, Summarize, or Extract tabs to see results here.</div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'chat' && (
          <div className="tab-pane tab-pane-chat">
            {children}
          </div>
        )}
      </div>
    </div>
  )
}
