import { useEffect, useState } from 'react';
import api from '../services/api';
import { timeAgo } from '../utils/time';
import './BillReviewModal.css';

// The CA's review screen. Three stages so the CA always sees one
// clear action: first Extract OCR, then review the extracted data,
// then Generate the XML. Reject opens a popup. Click the bill image
// to open a zoomed lightbox.
//
// The same component is used read-only by the client (readOnly
// prop) so the client sees their bill without any action buttons.

const OCR_FIELDS = [
  { key: 'invoice_number', label: 'Invoice #', required: true },
  { key: 'invoice_date',   label: 'Date' },
  { key: 'vendor_name',    label: 'Vendor',    required: true },
  { key: 'gstin',          label: 'GSTIN' },
  { key: 'taxable_amount', label: 'Taxable' },
  { key: 'cgst',           label: 'CGST' },
  { key: 'sgst',           label: 'SGST' },
  { key: 'igst',           label: 'IGST' },
  { key: 'total_amount',   label: 'Total',     required: true },
];

const VOUCHER_GROUPS = [
  { label: 'Purchase', items: [
    ['purchase', 'Purchase'],  
    ['purchase_return', 'Purchase Return (Debit Note)'],
    ['receipt_note', 'Receipt Note'],
    ['rejection_in', 'Rejection In'],
  ]},
  { label: 'Sales', items: [
    ['sales', 'Sales'],
    ['sales_return', 'Sales Return (Credit Note)'],
    ['delivery_note', 'Delivery Note'],
    ['rejection_out', 'Rejection Out'],
  ]},
  { label: 'Other', items: [
    ['payment', 'Payment'],
    ['receipt', 'Receipt'],
    ['journal', 'Journal'],
    ['expense', 'Expense'],
    ['contra', 'Contra'],
  ]},
];

const REUPLOAD_REASONS = [
  'Image is blurry',
  'Bill is cut off',
  'Wrong bill uploaded',
  'Missing pages',
  'Other',
];

export default function BillReviewModal({ billId, onClose, onUpdated, readOnly = false }) {
  const [bill, setBill] = useState(null);
  const [ocr, setOcr] = useState({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [editing, setEditing] = useState(false);
  const [voucher, setVoucher] = useState('purchase');
  const [error, setError] = useState('');
  const [ok, setOk] = useState('');
  const [lightbox, setLightbox] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [showReject, setShowReject] = useState(false);
  const [rejectReason, setRejectReason] = useState(REUPLOAD_REASONS[0]);
  const [rejectNote, setRejectNote] = useState('');
  const [reuploadReason, setReuploadReason] = useState(REUPLOAD_REASONS[0]);
  const [ocrReady, setOcrReady] = useState(true);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api.get(`/invoice/get-by-id/${billId}`),
      api.get('/review/ocr-status').catch(() => ({ data: { ready: true } })),
    ]).then(([billRes, statusRes]) => {
      if (cancelled) return;
      setBill(billRes.data);
      setOcr(billRes.data.ocr || {});
      setVoucher(billRes.data.bill_type || 'purchase');
      setOcrReady(statusRes.data.ready !== false);
    }).catch((err) => {
      if (!cancelled) setError(err.response?.data?.message || 'Could not load the bill.');
    }).finally(() => {
      if (!cancelled) setLoading(false);
    });
    return () => { cancelled = true; };
  }, [billId]);

  useEffect(() => {
    function onKey(e) {
      if (e.key === 'Escape') {
        if (lightbox) setLightbox(false);
        else onClose();
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [lightbox, onClose]);

  function update(field, value) {
    setOcr((prev) => ({ ...prev, [field]: value }));
  }

  async function refresh() {
    const res = await api.get(`/invoice/get-by-id/${billId}`);
    setBill(res.data);
    setOcr(res.data.ocr || {});
    setVoucher(res.data.bill_type || 'purchase');
  }

  async function runOcr() {
    setBusy('ocr'); setError(''); setOk('');
    try {
      await api.post(`/review/reextract/${billId}`);
      await refresh();
      setEditing(false);
      setOk('OCR finished. Review the fields and edit anything that looks wrong.');
    } catch (err) {
      const status = err.response?.status;
      const msg = err.response?.data?.message || 'OCR failed.';
      setError(status === 503 ? `OCR not available: ${msg}` : msg);
    } finally {
      setBusy('');
    }
  }

  async function saveEdits() {
    setBusy('save'); setError(''); setOk('');
    try {
      await api.put(`/review/update-ocr/${billId}`, { ocr });
      await refresh();
      setEditing(false);
      setOk('Fields saved.');
    } catch (err) {
      setError(err.response?.data?.message || 'Could not save.');
    } finally {
      setBusy('');
    }
  }

  function validateForApprove() {
    if (!ocr.invoice_number) return 'Invoice number is required.';
    if (!ocr.vendor_name) return 'Vendor name is required.';
    const total = parseFloat(ocr.total_amount);
    if (!total || total <= 0) return 'Total amount must be greater than 0.';
    return '';
  }

 async function approve() {
  const problem = validateForApprove();
  if (problem) { setError(problem); return; }

  setBusy('approve'); setError(''); setOk('');
  try {
    const res = await api.put(`/review/approve/${billId}`, {
      ocr,
      bill_type: voucher,
    });

    const payload = (res && res.data) ? res.data : res;
    const token = localStorage.getItem('invexa_token');
    const base = 'http://127.0.0.1:5000';

    if (payload && payload.download_url) {
      window.open(`${base}${payload.download_url}?token=${token}`, '_blank');
    }

    setOk('Approved. XML file downloaded.');
    if (onUpdated) onUpdated();
    setTimeout(onClose, 1000);
  } catch (err) {
    const serverMsg = err.response?.data?.message;
    setError(serverMsg || err.message || 'Approve failed.');
    console.error('Approve error:', err);
  } finally {
    setBusy('');
  }
}

  async function confirmReject() {
    const note = rejectNote.trim() || rejectReason;
    if (note.length < 5) {
      setError('Provide a reason (at least 5 characters).');
      return;
    }
    setBusy('reject'); setError('');
    try {
      await api.put(`/review/reject/${billId}`, { remarks: note });
      if (onUpdated) onUpdated();
      onClose();
    } catch (err) {
      setError(err.response?.data?.message || 'Reject failed.');
    } finally {
      setBusy('');
    }
  }

  async function requestReupload() {
    setBusy('reupload'); setError('');
    try {
      await api.put(`/review/request-reupload/${billId}`, { reason: reuploadReason });
      if (onUpdated) onUpdated();
      onClose();
    } catch (err) {
      setError(err.response?.data?.message || 'Could not request reupload.');
    } finally {
      setBusy('');
    }
  }

  async function downloadXml() {
    const token = localStorage.getItem('invexa_token');
    window.open(`http://127.0.0.1:5000/api/xml/download/${billId}?token=${token}`, '_blank');
  }

  if (loading) {
    return (
      <div className="rv-overlay">
        <div className="rv-modal rv-modal--loading">Loading bill…</div>
      </div>
    );
  }

  if (!bill) {
    return (
      <div className="rv-overlay" onClick={onClose}>
        <div className="rv-modal rv-modal--loading" onClick={(e) => e.stopPropagation()}>
          {error || 'Bill not found.'}
        </div>
      </div>
    );
  }

  const token = localStorage.getItem('invexa_token');
  const fileUrl = `http://127.0.0.1:5000/api/invoice/get-file/${bill.id}?token=${token}`;
  const isPdf = (bill.file_extension || '').toLowerCase() === 'pdf';
  const isImage = ['png', 'jpg', 'jpeg'].includes((bill.file_extension || '').toLowerCase());
  const hasOcr = Boolean(ocr.invoice_number || ocr.vendor_name || ocr.total_amount);
  const approveProblem = validateForApprove();

  return (
    <div className="rv-overlay" onClick={onClose}>
      <div className="rv-modal" onClick={(e) => e.stopPropagation()}>

        <header className="rv-head">
          <div>
            <h2 className="rv-head__title">
              {bill.client_name || 'Client'}
              {bill.invoice_number && <span className="rv-head__inv"> · {bill.invoice_number}</span>}
            </h2>
            <p className="rv-head__sub">
              {bill.file_name}
              {bill.uploaded_at && <span> · uploaded {timeAgo(bill.uploaded_at)}</span>}
            </p>
          </div>
          <button className="rv-close" onClick={onClose} aria-label="Close">×</button>
        </header>

        <div className="rv-body">
          <div className="rv-left">
            {isPdf && <iframe src={fileUrl} title="Bill PDF" className="rv-pdf" />}
            {isImage && (
              <img
                src={fileUrl}
                alt="Bill"
                className="rv-img"
                onClick={() => { setLightbox(true); setZoom(1); }}
                title="Click to zoom"
              />
            )}
            {!isPdf && !isImage && <div className="rv-nopreview">Preview not available.</div>}

            <a className="rv-openlink" href={fileUrl} target="_blank" rel="noreferrer">
              Open in new tab ↗
            </a>
          </div>

          <div className="rv-right">
            <div className="rv-right__head">
              <h3 className="rv-right__title">
                {hasOcr || editing ? 'Extracted data' : 'Step 1 — Read this bill'}
              </h3>
              {!readOnly && !ocrReady && (
                <span className="rv-ocr-badge">OCR unavailable</span>
              )}
            </div>

            {!hasOcr && !editing && !readOnly && (
              <div className="rv-start">
                <button
                  className="rv-btn rv-btn--primary rv-btn--lg"
                  onClick={runOcr}
                  disabled={busy === 'ocr' || !ocrReady}
                >
                  {busy === 'ocr' ? 'Reading the bill…' : 'Extract OCR Data'}
                </button>
                <p className="rv-start__hint">
                  Runs Tesseract on the bill and fills in the fields below.
                </p>
              </div>
            )}

            {(hasOcr || editing || readOnly) && (
              <div className="rv-grid">
                {OCR_FIELDS.map((f) => (
                  <label key={f.key} className="rv-field">
                    <span className="rv-field__label">
                      {f.label}
                      {f.required && <em className="rv-req">*</em>}
                    </span>
                    {editing && !readOnly ? (
                      <input
                        value={ocr[f.key] ?? ''}
                        onChange={(e) => update(f.key, e.target.value)}
                      />
                    ) : (
                      <div className="rv-field__value">
                        {ocr[f.key] !== undefined && ocr[f.key] !== '' && ocr[f.key] !== 0
                          ? String(ocr[f.key])
                          : <span className="rv-muted">—</span>}
                      </div>
                    )}
                  </label>
                ))}
              </div>
            )}

            {!readOnly && (hasOcr || editing) && (
              <div className="rv-review-actions">
                {!editing ? (
                  <>
                    <button className="rv-btn rv-btn--ghost rv-btn--sm" onClick={() => setEditing(true)}>
                      Edit fields
                    </button>
                    <button
                      className="rv-btn rv-btn--ghost rv-btn--sm"
                      onClick={runOcr}
                      disabled={busy === 'ocr'}
                    >
                      {busy === 'ocr' ? 'Reading…' : 'Re-extract'}
                    </button>
                  </>
                ) : (
                  <button
                    className="rv-btn rv-btn--primary rv-btn--sm"
                    onClick={saveEdits}
                    disabled={busy === 'save'}
                  >
                    {busy === 'save' ? 'Saving…' : 'Save changes'}
                  </button>
                )}
              </div>
            )}

            {!readOnly && (hasOcr || editing) && (
              <label className="rv-field rv-field--full">
                <span className="rv-field__label">Voucher type</span>
                <select value={voucher} onChange={(e) => setVoucher(e.target.value)}>
                  {VOUCHER_GROUPS.map((group) => (
                    <optgroup key={group.label} label={group.label}>
                      {group.items.map(([value, text]) => (
                        <option key={value} value={value}>{text}</option>
                      ))}
                    </optgroup>
                  ))}
                </select>
              </label>
            )}

            {readOnly && (
              <>
                <div className="rv-readonly-row">
                  <span>Status</span>
                  <span className={`rv-pill rv-pill--${bill.status}`}>
                    {bill.status.replace('_', ' ')}
                  </span>
                </div>
                {bill.remarks && (
                  <div className="rv-remarks">
                    <strong>CA's note:</strong> {bill.remarks}
                  </div>
                )}
              </>
            )}

            {!readOnly && (hasOcr || editing) && (
              <label className="rv-field rv-field--full">
                <span className="rv-field__label">Reason for asking a new photo (used only if you request reupload)</span>
                <select value={reuploadReason} onChange={(e) => setReuploadReason(e.target.value)}>
                  {REUPLOAD_REASONS.map((r) => <option key={r} value={r}>{r}</option>)}
                </select>
              </label>
            )}

            {error && <div className="rv-error">{error}</div>}
            {ok && <div className="rv-ok">{ok}</div>}
          </div>
        </div>

        <footer className="rv-foot">
          <button className="rv-btn rv-btn--ghost" onClick={onClose}>
            {readOnly ? 'Close' : 'Cancel'}
          </button>

          {readOnly ? (
            bill.status === 'approved' && (
              <button className="rv-btn rv-btn--primary" onClick={downloadXml}>
                Download XML
              </button>
            )
          ) : (
            <div className="rv-foot__right">
              <button
                className="rv-btn rv-btn--warn"
                onClick={requestReupload}
                disabled={!!busy || !hasOcr}
              >
                Request new photo
              </button>
              <button
                className="rv-btn rv-btn--danger"
                onClick={() => { setShowReject(true); setRejectNote(''); }}
                disabled={!!busy}
              >
                Reject
              </button>
              <div className="rv-approve-wrap">
                <button
                  className="rv-btn rv-btn--primary"
                  onClick={approve}
                  disabled={!!busy || !!approveProblem}
                  title={approveProblem || 'Approve and download the Tally XML'}
                >
                  {busy === 'approve' ? 'Generating XML…' : 'Generate XML Voucher'}
                </button>
                {approveProblem && hasOcr && (
                  <span className="rv-approve-hint">{approveProblem}</span>
                )}
              </div>
            </div>
          )}
        </footer>
      </div>

      {showReject && (
        <div className="rv-overlay rv-overlay--nested" onClick={() => setShowReject(false)}>
          <div className="rv-confirm" onClick={(e) => e.stopPropagation()}>
            <h3>Why are you rejecting this bill?</h3>
            <div className="rv-chips">
              {REUPLOAD_REASONS.map((r) => (
                <button
                  key={r}
                  className={`rv-chip${rejectReason === r ? ' rv-chip--active' : ''}`}
                  onClick={() => setRejectReason(r)}
                >
                  {r}
                </button>
              ))}
            </div>
            <textarea
              rows={3}
              placeholder="Add any extra detail for the client (optional)"
              value={rejectNote}
              onChange={(e) => setRejectNote(e.target.value)}
            />
            <div className="rv-confirm__actions">
              <button className="rv-btn rv-btn--ghost" onClick={() => setShowReject(false)}>Cancel</button>
              <button className="rv-btn rv-btn--danger" onClick={confirmReject} disabled={busy === 'reject'}>
                {busy === 'reject' ? 'Rejecting…' : 'Confirm rejection'}
              </button>
            </div>
          </div>
        </div>
      )}

      {lightbox && isImage && (
        <div className="rv-lightbox" onClick={() => setLightbox(false)}>
          <div className="rv-lightbox__controls" onClick={(e) => e.stopPropagation()}>
            <button onClick={() => setZoom(1)}>Fit</button>
            <button onClick={() => setZoom(1.5)}>150%</button>
            <button onClick={() => setZoom(2)}>200%</button>
            <button onClick={() => setLightbox(false)}>Close ✕</button>
          </div>
          <img
            src={fileUrl}
            alt="Bill"
            className="rv-lightbox__img"
            style={{ transform: `scale(${zoom})` }}
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </div>
  );
}