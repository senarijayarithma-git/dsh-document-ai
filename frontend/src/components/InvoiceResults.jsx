function InvoiceResults({ data }) {
  if (!data) {
    return null
  }

  const items = Array.isArray(data.items) ? data.items : []

  return (
    <div className="invoice-results">
      <h3>🧾 Invoice Details</h3>

      <div className="invoice-details">
        <p>
          <strong>Invoice Number:</strong>{' '}
          {data.invoice_number || 'Not available'}
        </p>

        <p>
          <strong>Invoice Date:</strong>{' '}
          {data.invoice_date || 'Not available'}
        </p>

        <p>
          <strong>Exporter:</strong>{' '}
          {data.exporter || 'Not available'}
        </p>

        <p>
          <strong>Consignee:</strong>{' '}
          {data.consignee || 'Not available'}
        </p>

        <p>
          <strong>Currency:</strong>{' '}
          {data.currency || 'Not available'}
        </p>
      </div>

      <h4>📦 Invoice Items</h4>

      {items.length > 0 ? (
        <div className="invoice-table-wrapper">
          <table className="invoice-table">
            <thead>
              <tr>
                <th>Product</th>
                <th>Quantity</th>
                <th>Unit Price</th>
                <th>Amount</th>
              </tr>
            </thead>

            <tbody>
              {items.map((item, index) => (
                <tr key={index}>
                  <td>{item.product || 'N/A'}</td>
                  <td>{item.quantity ?? 'N/A'}</td>
                  <td>{item.unit_price ?? 'N/A'}</td>
                  <td>{item.amount ?? 'N/A'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p>No invoice items available.</p>
      )}

      <div className="invoice-total">
        <strong>Total Amount:</strong>{' '}
        {data.currency || ''} {data.total_amount ?? 'Not available'}
      </div>
    </div>
  )
}

export default InvoiceResults