# INVEXA — Setup and Verification

## Prerequisites

- Python 3.12+
- Node.js 18+
- MongoDB Atlas cluster (or local MongoDB)
- **Tesseract-OCR** (required for bill OCR)
- **Poppler** (required only if you upload PDF bills)

### Installing Tesseract (Windows)

1. Download from https://github.com/UB-Mannheim/tesseract/wiki
2. Run the installer. Keep the default path `C:\Program Files\Tesseract-OCR\`.
3. Open a NEW terminal and verify:


You should see a version number. If it says "not recognised", the
installer didn't add it to PATH — the `.env` path below will still
work.

### Installing Poppler (Windows, PDFs only)

1. Download from https://github.com/oschwartz10612/poppler-windows/releases
2. Extract the zip to `C:\poppler\`. The final folder must be
   `C:\poppler\Library\bin\`.
3. No PATH change needed — the app reads the path from `.env`.

## Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt