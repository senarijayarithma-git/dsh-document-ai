import { useState } from 'react'
import { API } from '../config'
function getStatusStyle(status) {
  const styles = {
    PASS: {
      color: '#15803d',
      background: '#dcfce7',
      border: '#16a34a',
    },
    FAIL: {
      color: '#b91c1c',
      background: '#fee2e2',
      border: '#dc2626',
    },
    REVIEW: {
      color: '#b45309',
      background: '#fef3c7',
      border: '#d97706',
    },
    NEEDS_REVIEW: {
      color: '#b45309',
      background: '#fef3c7',
      border: '#d97706',
    },
    NOT_VERIFIED: {
      color: '#475569',
      background: '#f1f5f9',
      border: '#64748b',
    },
  }

  return styles[status] || {
    color: '#475569',
    background: '#f1f5f9',
    border: '#94a3b8',
  }
}
function ShipmentVerification({ token, onLogout }) {
  const [invoiceFile, setInvoiceFile] = useState(null)
  const [packingFile, setPackingFile] = useState(null)
  const [airWaybillFile, setAirWaybillFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

async function handleVerify() {
  if (!invoiceFile || !packingFile || !airWaybillFile) {
    return
  }

  const formData = new FormData()
  formData.append('invoice_file', invoiceFile)
  formData.append('packing_list_file', packingFile)
  formData.append('air_waybill_file', airWaybillFile)

  setLoading(true)
  setError('')
  setResult(null)

  try {
    const response = await fetch(
      `${API}/shipments/upload-and-verify`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      }
    )

    if (response.status === 401) {
      onLogout?.()
      return
    }

    const data = await response.json()

    if (!response.ok) {
      throw new Error(
        typeof data.detail === 'string'
          ? data.detail
          : 'Shipment verification failed.'
      )
    }

    setResult(data)
  } catch (err) {
    setError(err.message || 'Unable to verify shipment.')
  } finally {
    setLoading(false)
  }
}

  return (
    <section className="upload-section">
      <h1>Shipment Verification</h1>

      <p>
        Upload the three shipment documents to begin
        AI-powered verification.
      </p>

      <div className="upload-box">
        <h3>1. Commercial Invoice</h3>
        <input
          type="file"
          accept=".pdf"
          onChange={(event) =>
            setInvoiceFile(event.target.files[0] || null)
          }
        />
        {invoiceFile && <p>Selected: {invoiceFile.name}</p>}

        <h3>2. Packing List</h3>
        <input
          type="file"
          accept=".pdf"
          onChange={(event) =>
            setPackingFile(event.target.files[0] || null)
          }
        />
        {packingFile && <p>Selected: {packingFile.name}</p>}

        <h3>3. Air Waybill</h3>
        <input
          type="file"
          accept=".pdf"
          onChange={(event) =>
            setAirWaybillFile(event.target.files[0] || null)
          }
        />
        {airWaybillFile && (
          <p>Selected: {airWaybillFile.name}</p>
        )}

<button
  type="button"
  onClick={handleVerify}
  disabled={
    loading ||
    !invoiceFile ||
    !packingFile ||
    !airWaybillFile
  }
>
  {loading ? 'Verifying Shipment...' : 'Verify Shipment'}
</button>
{error && (
  <p role="alert" style={{ color: '#dc2626' }}>
    {error}
  </p>
)}


{result && (
  <div className="extraction-results">
    <h2>Shipment Verification Results</h2>

    <h3>Verification Summary</h3>

    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
        gap: '12px',
        marginBottom: '24px',
      }}
    >
      {[
        {
          label: 'Total Checks',
          value: result.summary?.total_checks,
          color: '#1e40af',
          background: '#eff6ff',
        },
        {
          label: 'Passed',
          value: result.summary?.passed,
          color: '#15803d',
          background: '#f0fdf4',
        },
        {
          label: 'Needs Review',
          value: result.summary?.needs_review,
          color: '#b45309',
          background: '#fffbeb',
        },
        {
          label: 'Failed',
          value: result.summary?.failed,
          color: '#b91c1c',
          background: '#fef2f2',
        },
        {
          label: 'Not Verified',
          value: result.summary?.not_verified,
          color: '#475569',
          background: '#f1f5f9',
        },
      ].map((item) => (
        <div
          key={item.label}
          style={{
            padding: '20px 12px',
            backgroundColor: item.background,
            borderRadius: '12px',
            border: `1px solid ${item.color}30`,
            textAlign: 'center',
          }}
        >
          <div
            style={{
              fontSize: '32px',
              fontWeight: '700',
              color: item.color,
            }}
          >
            {item.value ?? '—'}
          </div>

          <div
            style={{
              fontSize: '14px',
              fontWeight: '600',
              color: item.color,
              marginTop: '6px',
            }}
          >
            {item.label}
          </div>
        </div>
      ))}
    </div>

    <h3>Verification Findings</h3>

    {(result.findings || []).map((finding, index) => {
      const statusStyle = getStatusStyle(finding.status)

      return (
        <div
          key={`${finding.rule_code}-${index}`}
          style={{
            padding: '16px',
            marginBottom: '12px',
            border: '1px solid #e2e8f0',
            borderLeft: `5px solid ${statusStyle.border}`,
            borderRadius: '8px',
            textAlign: 'left',
            backgroundColor: '#ffffff',
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '8px',
            }}
          >
            <strong style={{ color: '#1e293b' }}>
              {finding.rule_code}
            </strong>

            <span
              style={{
                padding: '6px 12px',
                borderRadius: '20px',
                fontSize: '12px',
                fontWeight: '700',
                color: statusStyle.color,
                backgroundColor: statusStyle.background,
              }}
            >
              {(finding.status || 'UNKNOWN').replace(/_/g, ' ')}
            </span>
          </div>

          <p
            style={{
              margin: '12px 0 0',
              fontSize: '14px',
              lineHeight: '1.6',
              color: '#475569',
            }}
          >
            {finding.message}
          </p>
        </div>
      )
    })}

    <h3>NMRA Evidence Matching</h3>
    {(result.nmra_matches || []).length === 0 ? (
      <p>No invoice product codes to match.</p>
    ) : (
      result.nmra_matches.map((match, index) => (
        <div
          key={index}
          style={{
            padding: '12px',
            marginBottom: '10px',
            border: '1px solid #e2e8f0',
            borderRadius: '8px',
          }}
        >
          <p>
            <strong>Product Code:</strong>{' '}
            {match.product_code || 'Not provided'}
          </p>
          <p>
            <strong>Match Status:</strong> {match.status}
          </p>

          {(match.evidence || []).map((evidence, i) => (
            <div key={i}>
              <p>Registration: {evidence.d_number}</p>
              <p>Attachment ID: {evidence.attachment_id}</p>
              <p>Page: {evidence.page_number}</p>
              <p>Row: {evidence.row_number}</p>
            </div>
          ))}
        </div>
      ))
    )}

    <p>
      <small>
        NMRA evidence matching is an internal document check.
        It does not establish official regulatory authorization.
      </small>
    </p>
  </div>
)}
      </div>
    </section>
  )
}

export default ShipmentVerification
