
import { useCallback, useEffect, useState } from 'react'
import { API } from '../config'

export default function NMRADocuments({
  token,
  onLogout,
  onReviewAttachment,
}) {
  const [query, setQuery] = useState('')
  const [registrations, setRegistrations] = useState([])
  const [selected, setSelected] = useState(null)
  const [pages, setPages] = useState([])
  const [activeDocument, setActiveDocument] = useState(null)
  const [pdfUrl, setPdfUrl] = useState(null)
  const [loading, setLoading] = useState(false)
  const [documentLoading, setDocumentLoading] = useState(false)
  const [error, setError] = useState('')

  const request = useCallback(async (path, options = {}) => {
    const response = await fetch(`${API}${path}`, {
      ...options,
      headers: {
        ...options.headers,
        Authorization: `Bearer ${token}`,
      },
    })

    if (response.status === 401) {
      onLogout?.()
      throw new Error('Your session has expired.')
    }

    if (!response.ok) {
      throw new Error(`Request failed (${response.status}).`)
    }

    return response
  }, [token, onLogout])

  const search = useCallback(async (term = '') => {
    setLoading(true)
    setError('')

    try {
      const response = await request(
        `/nmra/registrations?q=${encodeURIComponent(term)}`
      )
      setRegistrations(await response.json())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [request])

  useEffect(() => {
  const startSearch = async () => {
    await search('')
  }

  const task = Promise.resolve().then(startSearch)

  return () => {
    void task
  }
}, [search])

  // Release browser memory whenever a PDF preview changes
  // or the component unmounts.
  useEffect(() => {
    return () => {
      if (pdfUrl) URL.revokeObjectURL(pdfUrl)
    }
  }, [pdfUrl])

  async function selectRegistration(id) {
    setError('')
    setSelected(null)
    setActiveDocument(null)
    setPages([])
    setPdfUrl(null)

    try {
      const response = await request(`/nmra/registrations/${id}`)
      setSelected(await response.json())
    } catch (err) {
      setError(err.message)
    }
  }

  async function openDocument(type, id, filename) {
    setError('')
    setDocumentLoading(true)
    setActiveDocument(null)
    setPages([])
    setPdfUrl(null)

    const base = type === 'certificate'
      ? `/nmra/certificates/${id}`
      : `/nmra/attachments/${id}`

    try {
      const [pagesResponse, pdfResponse] = await Promise.all([
        request(`${base}/pages`),
        request(`${base}/pdf`),
      ])

      const extractedPages = await pagesResponse.json()
      const blob = await pdfResponse.blob()

      if (blob.type && !blob.type.includes('pdf')) {
        throw new Error('The server did not return a PDF.')
      }

      const url = URL.createObjectURL(
        new Blob([blob], { type: 'application/pdf' })
      )

      setPages(extractedPages)
      setPdfUrl(url)
      setActiveDocument({ type, id, filename })
    } catch (err) {
      setError(err.message)
    } finally {
      setDocumentLoading(false)
    }
  }

  return (
    <section style={{ display: 'grid', gap: 20 }}>
      <div>
        <h1>NMRA Document Library</h1>
        <p>Search certificates, attachments, and extracted evidence.</p>
      </div>

      <form
        onSubmit={(event) => {
          event.preventDefault()
          search(query)
        }}
        style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}
      >
        <input
          aria-label="Search NMRA documents"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="D-number, product, or PDF text"
          style={{
            flex: 1,
            minWidth: 220,
            padding: 12,
            border: '1px solid #cbd5e1',
            borderRadius: 8,
          }}
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Searching...' : 'Search'}
        </button>
      </form>

      {error && (
        <p role="alert" style={{ color: '#b91c1c' }}>
          {error}
        </p>
      )}

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: 20,
        alignItems: 'start',
      }}>
        <section style={{
          background: 'white',
          padding: 18,
          borderRadius: 12,
          border: '1px solid #e2e8f0',
        }}>
          <h2>Registrations ({registrations.length})</h2>

          {registrations.length === 0 && !loading && (
            <p>No registrations found.</p>
          )}

          {registrations.map((registration) => (
            <button
              type="button"
              key={registration.id}
              onClick={() => selectRegistration(registration.id)}
              style={{
                display: 'block',
                width: '100%',
                padding: 14,
                marginBottom: 10,
                textAlign: 'left',
                background: selected?.id === registration.id
                  ? '#eff6ff'
                  : '#f8fafc',
                border: '1px solid #cbd5e1',
                borderRadius: 8,
                cursor: 'pointer',
              }}
            >
              <strong>{registration.d_number}</strong>
              <div>{registration.product_name || 'Product not specified'}</div>
            </button>
          ))}
        </section>

        <section style={{
          background: 'white',
          padding: 18,
          borderRadius: 12,
          border: '1px solid #e2e8f0',
        }}>
          <h2>Registration Details</h2>

          {!selected && <p>Select a registration to continue.</p>}

          {selected && (
            <>
              <h3>{selected.d_number}</h3>
              <p>{selected.product_name || 'Product not specified'}</p>
              <p>
                Registration expiry:{' '}
                {selected.registration_expiry || 'Not recorded'}
              </p>
              <p>
                Import licence expiry:{' '}
                {selected.import_licence_expiry || 'Not recorded'}
              </p>

              <h3>Certificate Versions</h3>

              {selected.versions.length === 0 && (
                <p>No certificates uploaded.</p>
              )}

              {selected.versions.map((version) => (
                <div key={version.id} style={{ marginBottom: 12 }}>
                  <button
                    type="button"
                    onClick={() => openDocument(
                      'certificate',
                      version.id,
                      version.filename
                    )}
                  >
                    Version {version.version}: {version.filename}
                  </button>
                  <div>Status: {version.review_status}</div>
                </div>
              ))}

              <h3>Attachments</h3>

              {selected.attachments.length === 0 && (
                <p>No attachments uploaded.</p>
              )}

              {selected.attachments.map((attachment) => (
                <div key={attachment.id} style={{ marginBottom: 12 }}>
                  <button
                    type="button"
                    onClick={() => openDocument(
                      'attachment',
                      attachment.id,
                      attachment.filename
                    )}
                  >
                    {attachment.filename}
                  </button>
                  <div>Status: {attachment.review_status}</div>
		    <button
                type="button"
                onClick={() => onReviewAttachment?.(attachment.id)}
                style={{
                    marginTop: 8,
                    padding: '8px 12px',
                    background: '#2563eb',
                    color: 'white',
                    border: 'none',
                    borderRadius: 6,
                    cursor: 'pointer',
            }}
		  >
            Review Items
		  </button>
                </div>
              ))}
            </>
          )}
        </section>
      </div>

      {documentLoading && <p>Loading document...</p>}

      {activeDocument && (
        <section style={{
          background: 'white',
          padding: 18,
          borderRadius: 12,
          border: '1px solid #e2e8f0',
        }}>
          <h2>{activeDocument.filename}</h2>

          {pdfUrl && (
            <iframe
              title={`PDF preview: ${activeDocument.filename}`}
              src={pdfUrl}
              style={{
                width: '100%',
                height: 550,
                border: '1px solid #cbd5e1',
                borderRadius: 8,
              }}
            />
          )}

          <h3>Extracted Page Evidence</h3>

          {pages.length === 0 && <p>No extracted pages available.</p>}

          {pages.map((page) => (
            <article
              key={page.page_number}
              style={{
                padding: 14,
                marginBottom: 12,
                background: '#f8fafc',
                borderRadius: 8,
              }}
            >
              <strong>
                Page {page.page_number} ({page.method})
              </strong>
              <pre style={{
                whiteSpace: 'pre-wrap',
                overflowWrap: 'anywhere',
                fontFamily: 'inherit',
              }}>
                {page.text || 'No readable text found.'}
              </pre>
            </article>
          ))}
        </section>
      )}
    </section>
  )
}
