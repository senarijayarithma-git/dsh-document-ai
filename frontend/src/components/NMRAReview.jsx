import { API } from "../config";
import { useCallback, useEffect, useState } from 'react'

export default function NMRAReview({
  token,
  employee,
  onLogout,
  attachmentId,
}) {
  const [summary, setSummary] = useState(null)
  const [items, setItems] = useState([])
  const [searchTerm, setSearchTerm] = useState('')
  const [issueFilter, setIssueFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [verifying, setVerifying] = useState(false)
  const [approving, setApproving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [selectedItem, setSelectedItem] = useState(null)
  const [isEditing, setIsEditing] = useState(false)

  const [correctionForm, setCorrectionForm] = useState({
    item_code: '',
    product_description: '',
    page_number: 1,
    row_number: '',
    correction_reason: '',
  })

  const role = String(employee?.role || '').toUpperCase()
  const canCorrect = ['ADMIN', 'REVIEWER'].includes(role)

  const headers = {
    Authorization: `Bearer ${token}`,
  }

  const handleUnauthorized = useCallback((response) => {
    if (response.status === 401) {
      onLogout?.()
      return true
    }

    return false
  }, [onLogout])

  const loadReview = useCallback(async () => {
    if (attachmentId == null) {
     setLoading(false)
     setSummary(null)
     setItems([])
     setSelectedItem(null)
     setIsEditing(false)
     setError('')
     return
  }

  try {
      setLoading(true)
      setError('')

      const [summaryResponse, itemsResponse] = await Promise.all([
        fetch(`${API}/nmra/attachments/${attachmentId}/review-summary`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }),
        fetch(`${API}/nmra/attachments/${attachmentId}/items`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }),
      ])

      if (
        handleUnauthorized(summaryResponse) ||
        handleUnauthorized(itemsResponse)
      ) {
        return
      }

      if (!summaryResponse.ok || !itemsResponse.ok) {
        throw new Error('Unable to load NMRA review data.')
      }

      const summaryData = await summaryResponse.json()
      const itemsData = await itemsResponse.json()

      setSummary(summaryData)
      setItems(itemsData.items || [])

      setSelectedItem((current) => {
        if (!current) return null

        return (
          (itemsData.items || []).find(
            (item) => item.id === current.id
          ) || null
        )
      })
    } catch (err) {
      setError(err.message || 'Unable to load review data.')
    } finally {
      setLoading(false)
    }
  }, [token, handleUnauthorized, attachmentId])

  useEffect(() => {
  const startReview = async () => {
    await loadReview()
  }

  const task = Promise.resolve().then(startReview)

  return () => {
    void task
  }
}, [loadReview])

  function openCorrection(item) {
    setSelectedItem(item)

    setCorrectionForm({
      item_code: item.item_code ?? '',
      product_description: item.product_description ?? '',
      page_number: item.page_number ?? 1,
      row_number: item.row_number ?? '',
      correction_reason: '',
    })

    setError('')
    setSuccess('')
    setIsEditing(true)
  }

  async function submitCorrection(event) {
    event.preventDefault()

    if (!canCorrect) {
      setError('Your account does not have permission to correct records.')
      return
    }

    if (summary?.attachment_status !== 'PENDING') {
      setError('Only pending attachments can be corrected.')
      return
    }

    if (!selectedItem) return

    try {
      setSaving(true)
      setError('')
      setSuccess('')

      const response = await fetch(
        `${API}/nmra/attachments/${attachmentId}/items/${selectedItem.id}`,
        {
          method: 'PATCH',
          headers: {
            ...headers,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            item_code: correctionForm.item_code.trim(),
            product_description:
              correctionForm.product_description.trim() || null,
            page_number: Number(correctionForm.page_number),
            row_number:
              correctionForm.row_number === ''
                ? null
                : Number(correctionForm.row_number),
            correction_reason: correctionForm.correction_reason.trim(),
          }),
        }
      )

      if (handleUnauthorized(response)) return

      if (response.status === 403) {
        throw new Error(
          'Access denied. Your account cannot correct NMRA records.'
        )
      }

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(
          data.detail || 'Correction could not be saved.'
        )
      }

      setIsEditing(false)
      setSuccess('Correction saved successfully.')
      await loadReview()
    } catch (err) {
      setError(err.message || 'Correction failed.')
    } finally {
      setSaving(false)
    }
  }

async function verifyItem(item) {
  if (!canCorrect || summary?.attachment_status !== 'PENDING') {
    setError('You cannot verify items in this attachment.')
    return
  }

  if (item.review_status !== 'UNREVIEWED') {
    setError('This item has already been reviewed.')
    return
  }

  if (item.row_number == null || item.row_number < 1) {
    setError(
      'This item has no valid row number. Correct it before verification.'
    )
    return
  }

  try {
    setVerifying(true)
    setError('')
    setSuccess('')

    const response = await fetch(
      `${API}/nmra/attachments/${attachmentId}/items/${item.id}/verify`,
      {
        method: 'POST',
        headers,
      }
    )

    if (handleUnauthorized(response)) return

    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(
        typeof data.detail === 'string'
          ? data.detail
          : 'Item verification failed.'
      )
    }

    await loadReview()
    setSuccess('Item verified successfully.')
  } catch (err) {
    setError(err.message || 'Item verification failed.')
  } finally {
    setVerifying(false)
  }
}

async function approveAttachment() {
  if (!canCorrect || summary?.attachment_status !== 'PENDING') {
    setError('You do not have permission to approve this attachment.')
    return
  }

  const eligible =
    summary.total_candidates > 0 &&
    summary.unreviewed === 0 &&
    summary.reviewed === summary.total_candidates &&
    items.every(
      (item) =>
        item.review_status === 'REVIEWED' &&
        Number.isInteger(item.row_number) &&
        item.row_number >= 1
    )

  if (!eligible) {
    setError(
      'Approval blocked. Every candidate must be reviewed and have a valid row number.'
    )
    return
  }

  const confirmed = window.confirm(
    `Approve attachment "${summary.filename}"?\n\n` +
    `This will approve ${summary.total_candidates} reviewed items.`
  )

  if (!confirmed) return

  try {
    setApproving(true)
    setError('')
    setSuccess('')

    const response = await fetch(
      `${API}/nmra/attachments/${attachmentId}/approve`,
      {
        method: 'POST',
        headers,
      }
    )

    if (handleUnauthorized(response)) return

    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(
        typeof data.detail === 'string'
          ? data.detail
          : 'Attachment approval failed.'
      )
    }

    await loadReview()
    setSuccess('Attachment approved successfully.')
    setIsEditing(false)
  } catch (err) {
    setError(err.message || 'Attachment approval failed.')
  } finally {
    setApproving(false)
  }
}

  const filteredItems = items.filter((item) => {
    const search = searchTerm.trim().toLowerCase()

    const matchesSearch =
      String(item.item_code || '').toLowerCase().includes(search) ||
      String(item.evidence_text || '').toLowerCase().includes(search)

    const missingRow = item.row_number === null

    const suspiciousRow =
      item.row_number !== null &&
      (item.row_number < 1 || item.row_number > 117)

    const matchesFilter =
      issueFilter === 'all' ||
      (issueFilter === 'missing' && missingRow) ||
      (issueFilter === 'suspicious' && suspiciousRow) ||
      (issueFilter === 'unreviewed' &&
        item.review_status === 'UNREVIEWED')

    return matchesSearch && matchesFilter
  })
  if (attachmentId == null) {
    return (
      <section className="nmra-review">
        <h2>NMRA Attachment Review</h2>
        <p>
         No attachment selected. Open My Documents,
         choose a registration, and click Review Items
         beside the attachment you want to review.
        </p>
      </section>
    )
  }
  if (loading) {
    return <p>Loading NMRA attachment review...</p>
  }

  if (error && !summary) {
    return <p role="alert">Error: {error}</p>
  }

  if (!summary) {
    return <p>No NMRA review data available.</p>
  }

  return (
    <section className="nmra-review">
      <h2>NMRA Attachment Review</h2>

      <p>{summary.filename}</p>

      <p>
        Logged in as: <strong>{employee?.full_name}</strong>
        {' '}({role})
      </p>

      <p>
        Attachment status:{' '}
        <strong>{summary.attachment_status}</strong>
      </p>

      <div className="nmra-summary">
        <p>Total candidates: {summary.total_candidates}</p>
        <p>Unreviewed: {summary.unreviewed}</p>
        <p>Reviewed: {summary.reviewed}</p>
        <p>Missing row numbers: {summary.missing_row_numbers}</p>
      </div>

{canCorrect && summary.attachment_status === 'PENDING' && (
  <div style={{ marginTop: '16px', marginBottom: '20px' }}>
    <button
      type="button"
      onClick={approveAttachment}
      disabled={
        approving ||
        saving ||
        verifying ||
        summary.total_candidates === 0 ||
        summary.unreviewed > 0 ||
        summary.reviewed !== summary.total_candidates ||
        summary.missing_row_numbers > 0
      }
    >
      {approving ? 'Approving...' : 'Approve Attachment'}
    </button>

    <p style={{ fontSize: '13px', color: '#64748b' }}>
      Approval requires every candidate to be reviewed
      and every row number to be valid.
    </p>
  </div>
)}

      {!canCorrect && (
        <p
          style={{
            padding: '12px',
            background: '#fef3c7',
            color: '#92400e',
            borderRadius: '8px',
          }}
        >
          Read-only access. Your VIEWER role cannot correct NMRA records.
        </p>
      )}

      {error && (
        <p role="alert" style={{ color: '#dc2626' }}>
          {error}
        </p>
      )}

      {success && (
        <p role="status" style={{ color: '#15803d' }}>
          {success}
        </p>
      )}

      <h3>Extracted Item Codes</h3>
      {items.length === 0 && (
        <p>
          No extracted item candidates are available for this attachment.
          The PDF may still have searchable page text in My Documents.
        </p>
      )}

      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        <input
          type="search"
          placeholder="Search by item code or OCR evidence..."
          value={searchTerm}
          onChange={(event) => setSearchTerm(event.target.value)}
          style={{
            width: '100%',
            maxWidth: '450px',
            padding: '12px',
            border: '1px solid #ccc',
            borderRadius: '8px',
          }}
        />

        <select
          value={issueFilter}
          onChange={(event) => setIssueFilter(event.target.value)}
          style={{
            padding: '12px',
            border: '1px solid #ccc',
            borderRadius: '8px',
          }}
        >
          <option value="all">All Records</option>
          <option value="missing">Missing Row Numbers</option>
          <option value="suspicious">Out-of-Range Rows</option>
          <option value="unreviewed">Unreviewed Records</option>
        </select>
      </div>

      <p>
        Showing {filteredItems.length} of {items.length} records
      </p>

      {selectedItem && (
        <div
          style={{
            marginTop: '24px',
            padding: '20px',
            border: '1px solid #ccc',
            borderRadius: '10px',
          }}
        >
          <h3>Selected NMRA Item</h3>

          <p>
            <strong>Item Code:</strong> {selectedItem.item_code}
          </p>

          <p>
            <strong>Description:</strong>{' '}
            {selectedItem.product_description || 'Not available'}
          </p>

          <p>
            <strong>Page:</strong> {selectedItem.page_number}
          </p>

          <p>
            <strong>Row:</strong>{' '}
            {selectedItem.row_number ?? 'Needs review'}
          </p>

          <p>
            <strong>Review Status:</strong>{' '}
            {selectedItem.review_status}
          </p>

          <p><strong>Original OCR Evidence:</strong></p>

          <pre
            style={{
              whiteSpace: 'pre-wrap',
              overflowWrap: 'anywhere',
              padding: '12px',
              background: '#f5f5f5',
              borderRadius: '8px',
            }}
          >
            {selectedItem.evidence_text || 'No OCR evidence available'}
          </pre>

          {canCorrect &&
            summary.attachment_status === 'PENDING' &&
            selectedItem.review_status === 'UNREVIEWED' && (
              <button
                type="button"
                onClick={() => verifyItem(selectedItem)}
                disabled={verifying || saving}
                style={{ marginRight: '10px' }}
              >
                {verifying ? 'Verifying...' : 'Verify Item'}
              </button>
            )}
          {canCorrect && (
            <button
              type="button"
              onClick={() => openCorrection(selectedItem)}
              disabled={summary.attachment_status !== 'PENDING'}
              style={{ marginRight: '10px' }}
            >
              Edit / Correct
            </button>
          )}

          <button
            type="button"
            onClick={() => {
              setSelectedItem(null)
              setIsEditing(false)
            }}
          >
            Close Details
          </button>

          {isEditing && canCorrect && (
            <form
              onSubmit={submitCorrection}
              style={{
                display: 'grid',
                gap: '12px',
                marginTop: '20px',
                marginBottom: '20px',
                maxWidth: '500px',
              }}
            >
              <h4>Correct NMRA Item</h4>

              <label>
                Item Code
                <input
                  type="text"
                  required
                  maxLength={150}
                  value={correctionForm.item_code}
                  onChange={(event) =>
                    setCorrectionForm({
                      ...correctionForm,
                      item_code: event.target.value,
                    })
                  }
                />
              </label>

              <label>
                Product Description
                <textarea
                  maxLength={500}
                  value={correctionForm.product_description}
                  onChange={(event) =>
                    setCorrectionForm({
                      ...correctionForm,
                      product_description: event.target.value,
                    })
                  }
                />
              </label>

              <label>
                Page Number
                <input
                  type="number"
                  required
                  min="1"
                  step="1"
                  value={correctionForm.page_number}
                  onChange={(event) =>
                    setCorrectionForm({
                      ...correctionForm,
                      page_number: event.target.value,
                    })
                  }
                />
              </label>

              <label>
                Row Number (optional)
                <input
                  type="number"
                  min="1"
                  step="1"
                  value={correctionForm.row_number}
                  onChange={(event) =>
                    setCorrectionForm({
                      ...correctionForm,
                      row_number: event.target.value,
                    })
                  }
                />
              </label>

              <label>
                Correction Reason
                <textarea
                  required
                  minLength={10}
                  maxLength={1000}
                  placeholder="Explain what you verified against the original PDF..."
                  value={correctionForm.correction_reason}
                  onChange={(event) =>
                    setCorrectionForm({
                      ...correctionForm,
                      correction_reason: event.target.value,
                    })
                  }
                />
              </label>

              <div style={{ display: 'flex', gap: '10px' }}>
                <button type="submit" disabled={saving}>
                  {saving ? 'Saving...' : 'Save Correction'}
                </button>

                <button
                  type="button"
                  disabled={saving}
                  onClick={() => setIsEditing(false)}
                >
                  Cancel
                </button>
              </div>

              <p style={{ fontSize: '13px', color: '#64748b' }}>
                Corrections are recorded separately from the original OCR
                evidence. Saving a correction does not approve the attachment.
              </p>
            </form>
          )}
        </div>
      )}

      <div style={{ overflowX: 'auto', marginTop: '20px' }}>
        <table>
          <thead>
            <tr>
              <th>Item Code</th>
              <th>Page</th>
              <th>Row</th>
              <th>OCR Evidence</th>
              <th>Review Status</th>
              <th>Action</th>
            </tr>
          </thead>

          <tbody>
            {filteredItems.map((item) => (
              <tr key={item.id}>
                <td>{item.item_code}</td>
                <td>{item.page_number}</td>
                <td>
                  {item.row_number === null
                    ? 'Needs review'
                    : item.row_number}
                </td>
                <td>{item.evidence_text}</td>
                <td>{item.review_status}</td>
                <td>
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedItem(item)
                      setIsEditing(false)
                      setError('')
                      setSuccess('')
                    }}
                  >
                    View Details
                  </button>
                </td>
              </tr>
            ))}

            {filteredItems.length === 0 && (
              <tr>
                <td colSpan="6">No matching records found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <p>
        These are OCR candidates only. The attachment must be reviewed
        and approved before regulatory verification.
      </p>
    </section>
  )
}
