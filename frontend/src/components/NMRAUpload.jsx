
import { useState } from 'react'
import { API } from '../config'

export default function NMRAUpload({ token, employee, onLogout }) {
  const [dNumber, setDNumber] = useState('')
  const [certificate, setCertificate] = useState(null)
  const [attachments, setAttachments] = useState([])
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  const role = String(employee?.role || '').toUpperCase()
  const canUpload = ['ADMIN', 'REVIEWER'].includes(role)

  async function handleSubmit(event) {
    event.preventDefault()

    if (!canUpload || uploading) return

    setError('')
    setResult(null)

    if (!dNumber.trim()) {
      setError('Please enter the NMRA D-number.')
      return
    }

    if (!certificate) {
      setError('Please select a certificate PDF.')
      return
    }

    if (attachments.length > 10) {
      setError('A maximum of 10 attachments is allowed.')
      return
    }

    const allFiles = [certificate, ...attachments]

    if (allFiles.some(file => (
      !file.name.toLowerCase().endsWith('.pdf') ||
      file.size > 10 * 1024 * 1024
    ))) {
      setError('Each file must be a PDF no larger than 10 MiB.')
      return
    }

    const formData = new FormData()
    formData.append('d_number', dNumber.trim().toUpperCase())
    formData.append('certificate', certificate)

    attachments.forEach(file => {
      formData.append('attachments', file)
    })

    try {
      setUploading(true)

      const response = await fetch(`${API}/nmra/upload`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      })

      if (response.status === 401) {
        onLogout?.()
        return
      }

      const data = await response.json()

      if (!response.ok) {
        const detail = data.detail
        throw new Error(
          typeof detail === 'string'
            ? detail
            : JSON.stringify(detail || data)
        )
      }

      setResult(data)
      setDNumber('')
      setCertificate(null)
      setAttachments([])

      // Reset file inputs after successful upload.
    } catch (err) {
      setError(err.message || 'NMRA upload failed.')
    } finally {
      setUploading(false)
    }
  }

  if (!canUpload) {
    return (
      <section>
        <h1>Upload NMRA Certificate</h1>
        <p>
          Your employee role does not permit NMRA uploads.
          Contact an administrator if access is required.
        </p>
      </section>
    )
  }

  return (
    <section style={{ maxWidth: 750 }}>
      <h1>Upload NMRA Certificate</h1>
      <p>
        Upload a registration certificate and optional supporting PDFs.
        A new certificate version will be created for an existing D-number.
      </p>

      <form
        onSubmit={handleSubmit}
        style={{
          display: 'grid',
          gap: 18,
          padding: 24,
          background: 'white',
          border: '1px solid #e2e8f0',
          borderRadius: 12,
        }}
      >
        <label style={{ display: 'grid', gap: 6 }}>
          <strong>NMRA D-number *</strong>
          <input
            value={dNumber}
            onChange={event => setDNumber(event.target.value)}
            placeholder="Enter registration D-number"
            required
            maxLength={100}
            style={{
              padding: 12,
              border: '1px solid #cbd5e1',
              borderRadius: 8,
            }}
          />
        </label>

        <label style={{ display: 'grid', gap: 6 }}>
          <strong>Certificate PDF *</strong>
          <input
            type="file"
            accept=".pdf,application/pdf"
            required
            onChange={event => {
              setCertificate(event.target.files?.[0] || null)
            }}
          />
        </label>

        <label style={{ display: 'grid', gap: 6 }}>
          <strong>Supporting attachments (optional)</strong>
          <input
            type="file"
            accept=".pdf,application/pdf"
            multiple
            onChange={event => {
              setAttachments(Array.from(event.target.files || []))
            }}
          />
          <small>Up to 10 PDFs, maximum 10 MiB each.</small>
        </label>

        {error && (
          <p role="alert" style={{ color: '#b91c1c' }}>
            {error}
          </p>
        )}

        <button type="submit" disabled={uploading}>
          {uploading ? 'Uploading and extracting...' : 'Upload Certificate'}
        </button>
      </form>

      {result && (
        <section
          role="status"
          style={{
            marginTop: 20,
            padding: 20,
            background: '#f0fdf4',
            border: '1px solid #bbf7d0',
            borderRadius: 12,
          }}
        >
          <h2>Certificate uploaded successfully</h2>
          <p>The PDF has been stored and processed.</p>
          <pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>
            {JSON.stringify(result, null, 2)}
          </pre>
          <p>Open My Documents to search for this D-number.</p>
        </section>
      )}
    </section>
  )
}
