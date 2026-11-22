
import { useEffect, useState } from 'react'
import DocumentUpload from './components/DocumentUpload'
import NMRAReview from './components/NMRAReview'
import Login from './components/Login'
import './App.css'
import { API } from "./config";
import NMRADocuments from './components/NMRADocuments'
import NMRAUpload from './components/NMRAUpload'
function App() {
  const [activePage, setActivePage] = useState('dashboard')
  const [selectedAttachmentId, setSelectedAttachmentId] = useState(null)
  const [token, setToken] = useState(null)
  const [employee, setEmployee] = useState(null)
  const [authLoading, setAuthLoading] = useState(false)

  useEffect(() => {
    if (!token) {
      return
    }

    let cancelled = false

    async function verifyEmployee() {
      try {
        setAuthLoading(true)

        const response = await fetch(
          `${API}/auth/me`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        )

        if (!response.ok) {
          throw new Error('Session verification failed.')
        }

        const data = await response.json()

        if (!cancelled) {
          setEmployee(data)
        }
      } catch (error) {
        if (!cancelled) {
          console.error('Authentication failed:', error)
          setToken(null)
          setEmployee(null)
        }
      } finally {
        if (!cancelled) {
          setAuthLoading(false)
        }
      }
    }

    verifyEmployee()

    return () => {
      cancelled = true
    }
  }, [token])

  function handleLogin(accessToken) {
    setAuthLoading(true)
    setToken(accessToken)
  }

  function openAttachmentReview(attachmentId) {
    setSelectedAttachmentId(attachmentId)
    setActivePage('nmra-review')
    window.location.hash = 'nmra-review'
  }

  function handleLogout() {
    setToken(null)
    setEmployee(null)
    setSelectedAttachmentId(null)
    setActivePage('dashboard')
  }

  if (!token) {
    return <Login onLogin={handleLogin} />
  }

  if (authLoading || !employee) {
    return (
      <div className="login-container">
        <p>Verifying employee account...</p>
      </div>
    )
  }

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span>📄</span>
          <h2>DSH Document AI</h2>
        </div>

        <nav className="sidebar-nav">
          <a
            href="#dashboard"
            className={`nav-link ${activePage === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActivePage('dashboard')}
          >
            Dashboard
          </a>

          <a
            href="#upload"
            className={`nav-link ${activePage === 'upload' ? 'active' : ''}`}
            onClick={() => setActivePage('upload')}
          >
            Upload Document
          </a>
          {['ADMIN', 'REVIEWER'].includes(
            String(employee.role).toUpperCase()
          ) && (
            <a
              href="#nmra-upload"
              className={`nav-link ${activePage === 'nmra-upload' ? 'active' : ''}`}
              onClick={() => setActivePage('nmra-upload')}
            >
              Upload NMRA Certificate
            </a>
          )}
          <a
            href="#documents"
            className={`nav-link ${activePage === 'documents' ? 'active' : ''}`}
            onClick={() => setActivePage('documents')}
          >
            My Documents
          </a>

          <a
            href="#chatbot"
            className={`nav-link ${activePage === 'chatbot' ? 'active' : ''}`}
            onClick={() => setActivePage('chatbot')}
          >
            AI Chatbot
          </a>

          <a
            href="#nmra-review"
            className={`nav-link ${activePage === 'nmra-review' ? 'active' : ''}`}
            onClick={() => setActivePage('nmra-review')}
          >
            NMRA Review
          </a>
        </nav>

        <div className="sidebar-footer">
          <p>{employee.full_name}</p>
          <p>Role: {employee.role}</p>
          <p>DSH Document AI v1.0</p>
        </div>
      </aside>

      <main className="main-content">
        <header
          style={{
            display: 'flex',
            justifyContent: 'flex-end',
            alignItems: 'center',
            gap: '16px',
            flexWrap: 'wrap',
            marginBottom: '24px',
            padding: '12px 16px',
            background: 'white',
            border: '1px solid #e2e8f0',
            borderRadius: '12px',
          }}
        >
          <div style={{ textAlign: 'right' }}>
            <strong>{employee.full_name}</strong>
            <div style={{ fontSize: '12px', color: '#64748b' }}>
              {employee.role}
            </div>
          </div>

          <button
            type="button"
            onClick={handleLogout}
            style={{
              padding: '10px 18px',
              background: '#dc2626',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: '600',
            }}
          >
            Logout
          </button>
        </header>

        {activePage === 'upload' && (
          <DocumentUpload token={token} onLogout={handleLogout} />
        )}
        {activePage === 'nmra-upload' && (
          <NMRAUpload
            token={token}
            employee={employee}
            onLogout={handleLogout}
          />
        )}
        {activePage === 'nmra-review' && (
          <NMRAReview
          token={token}
          employee={employee}
          onLogout={handleLogout}
          attachmentId={selectedAttachmentId}
          />
        )}

        {activePage === 'documents' && (
          <NMRADocuments
          token={token}
          onLogout={handleLogout}
          onReviewAttachment={openAttachmentReview}
          />
        )}

        {activePage === 'chatbot' && (
          <section>
            <h1>AI Chatbot</h1>
            <p>This page is under development.</p>
          </section>
        )}

        {activePage === 'dashboard' && (
          <>
            <header className="page-header">
              <div>
                <h1>Dashboard</h1>
                <p>
                  Welcome to your AI-powered logistics document
                  processing platform.
                </p>
              </div>

              <span className="header-badge">
                ✨ AI Powered
              </span>
            </header>

            <section className="welcome-card">
              <h2>Welcome to DSH Document AI</h2>
              <p>
                Upload, extract, organize, and understand your
                logistics documents using artificial intelligence.
              </p>
            </section>

            <section className="features-section">
              <h2>Explore Features</h2>

              <div className="feature-grid">
                <div className="feature-card">
                  <div className="feature-icon">📄</div>
                  <h3>Upload Documents</h3>
                  <p>
                    Upload logistics documents for AI-powered
                    processing and extraction.
                  </p>
                </div>

                <div className="feature-card">
                  <div className="feature-icon">🤖</div>
                  <h3>AI Extraction</h3>
                  <p>
                    Automatically extract important information
                    from your documents.
                  </p>
                </div>

                <div className="feature-card">
                  <div className="feature-icon">📁</div>
                  <h3>My Documents</h3>
                  <p>
                    Access and review your previously
                    processed documents.
                  </p>
                </div>

                <div className="feature-card">
                  <div className="feature-icon">💬</div>
                  <h3>AI Chatbot</h3>
                  <p>
                    Ask questions and get intelligent answers
                    about your documents.
                  </p>
                </div>
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  )
}

export default App
