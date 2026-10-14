import BillReviewModal from './BillReviewModal';

// Thin wrapper around BillReviewModal in read-only mode. Kept as
// its own file so the client code reads clearly and so we could
// swap implementations later without touching the invoices page.
export default function BillPreviewModal({ billId, onClose }) {
  return (
    <BillReviewModal
      billId={billId}
      onClose={onClose}
      readOnly={true}
    />
  );
}