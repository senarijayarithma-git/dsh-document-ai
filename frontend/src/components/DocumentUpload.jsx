import { useState } from 'react'
import InvoiceResults from './InvoiceResults'
import { API } from "../config";

function DocumentUpload({ token, onLogout }) {
  const [selectedFile, setSelectedFile] = useState(null)
  const [extractionResult, setExtractionResult] = useState(null)

  function handleFileChange(event) {
    const file = event.target.files[0]
    setSelectedFile(file || null)
    setExtractionResult(null)
  }
  async function handleUpload() {
  if (!selectedFile) return

  const formData = new FormData()
  formData.append('file', selectedFile)


try {

const response = await fetch(
  `${API}/documents/upload-and-extract`,
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
    throw new Error(JSON.stringify(data))
  }

    setExtractionResult(data)
    console.log('Upload successful:', data)
    alert('Document uploaded and extracted successfully!')

  } catch (error) {
    console.error('Upload failed:', error)
    alert('Document upload failed. Check the browser console.')
  }
}
  return (
    <section className="upload-section">
      <h2> Upload Document</h2>

      <p>
        Select a logistics document to process using AI.
      </p>

      <div className="upload-box">
        <input
          type="file"
          accept=".pdf"
          onChange={handleFileChange}
        />

        {selectedFile && (
          <p>
            Selected file: <strong>{selectedFile.name}</strong>
          </p>
        )}

        <button type="button" disabled={!selectedFile} onClick={handleUpload}>
            Upload and Extract
        </button>
      </div>
      {extractionResult && (
  <div className="extraction-results">
    <h3> Extraction Results</h3>

    <p>
      <strong>Filename:</strong>{' '}
      {extractionResult.filename}
    </p>

    <p>
      <strong>Document Type:</strong>{' '}
      {extractionResult.document_type}
    </p>

    <p>
      <strong>Pages Processed:</strong>{' '}
      {extractionResult.pages_processed}
    </p>

    <p>
      <strong>Extraction Source:</strong>{' '}
      {extractionResult.extraction_source}
    </p>

    <h4>Extracted Data</h4>

    {extractionResult.document_type === 'invoice' &&
    extractionResult.extracted_data ? (
        <InvoiceResults data={extractionResult.extracted_data} />
    ) : (
        <pre>
        {JSON.stringify(
            extractionResult.extracted_data ?? extractionResult,
            null,
            2
        )}
        </pre>
    )}
        </div>
     )}
    </section>
  )
}

export default DocumentUpload
