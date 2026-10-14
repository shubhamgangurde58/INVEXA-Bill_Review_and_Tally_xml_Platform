# INVEXA - Bill Review and Tally XML Platform

INVEXA is a web-based bill review and Tally XML platform designed to streamline invoice processing. It brings bill uploads, OCR-assisted data extraction, review, and preparation of accounting data for Tally XML workflows into one project.

# Project Overview

Manual entry of bill information is time-consuming and prone to errors. INVEXA aims to simplify this workflow by extracting information from uploaded bills, allowing users to review it, and supporting Tally-compatible XML processing.

# Key Capabilities

- Bill and invoice upload workflow
- OCR-assisted text extraction using Tesseract
- Support for PDF bill processing with Poppler
- Bill information review before accounting export
- Tally XML-focused workflow
- Separate frontend and backend applications
- MongoDB-backed data storage

> Note: The exact availability and behavior of each feature depend on the current implementation. Check the source code for the latest status.

## Technology Stack

| Layer | Technology |
| --- | --- |
| Frontend | JavaScript / Node.js-based frontend |
| Backend | Python |
| Database | MongoDB (Atlas or local) |
| OCR | Tesseract OCR |
| PDF processing | Poppler |
| Accounting integration | Tally XML |

## Project Structure

```text
INVEXA-Bill_Review_and_Tally_xml_Platform/
├── backend/             # Python backend
├── frontend/            # Frontend application
├── Installations.md     # Setup notes and prerequisites
├── README.md            # Project documentation
├── package-lock.json
└── .gitignore
```

## Prerequisites

Before running the project, install:

- Python 3.12 or newer
- Node.js 18 or newer (includes npm)
- MongoDB Atlas or a local MongoDB instance
- Tesseract OCR for bill text extraction
- Poppler for PDF bill uploads

For Windows-specific OCR and PDF tool installation, see [Installations.md](Installations.md).

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/shubhamgangurde58/INVEXA-Bill_Review_and_Tally_xml_Platform.git
cd INVEXA-Bill_Review_and_Tally_xml_Platform
```

### 2. Set up the backend

```bash
cd backend
python -m venv venv
```

Activate the virtual environment:

**Windows (Command Prompt)**

```bat
venv\Scripts\activate
```

**macOS / Linux**

```bash
source venv/bin/activate
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Configure the backend environment variables using the configuration expected by the application. This may include MongoDB connection details and local paths to Tesseract and Poppler. **Do not commit credentials or `.env` files.**

### 3. Set up the frontend

Open a second terminal from the repository root:

```bash
cd frontend
npm install
```

Use the scripts defined in `frontend/package.json` to start the frontend. Check the backend entry point for its run command.

## Typical Workflow

1. Upload a bill or invoice.
2. Extract text and bill details using OCR.
3. Review and correct extracted information.
4. Prepare the reviewed data for a Tally XML workflow.
5. Use the resulting accounting data according to the application's implemented export or integration process.

## Future Improvements

- More robust validation of extracted invoice fields
- Improved OCR accuracy for varied bill layouts
- Better error reporting and review history
- Expanded Tally XML compatibility and testing
- Automated tests and deployment documentation

## Repository

**Source code:** [INVEXA - Bill Review and Tally XML Platform](https://github.com/shubhamgangurde58/INVEXA-Bill_Review_and_Tally_xml_Platform)

## Author

**Shubham Santosh Gangurde**  
GitHub: [shubhamgangurde58](https://github.com/shubhamgangurde58)
