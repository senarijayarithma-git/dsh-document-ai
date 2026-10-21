# DSH Document AI - starter project

## Scope
This is a LOCAL prototype: PDF text extraction and deterministic comparison of pre-structured invoice, packing-list and AWB data. It does **not** yet perform OCR, LLM extraction, Outlook ingestion, database persistence, authentication, or official NMRA verification.

## Setup (Windows PowerShell)
```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```
Visit http://127.0.0.1:8000/docs

## Test
In a second terminal inside `backend`:
```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Database setup (PostgreSQL)
Run in psql as an administrator:
```sql
CREATE ROLE dsh_user LOGIN PASSWORD 'REPLACE_WITH_LONG_RANDOM_PASSWORD';
CREATE DATABASE dsh_document_ai OWNER dsh_user;
```
For a local **development-only** schema bootstrap, set DATABASE_URL from `.env.example`, then in `backend` run:
```powershell
.\.venv\Scripts\python.exe -c "import os; from sqlalchemy import create_engine; from app.models import Base; Base.metadata.create_all(create_engine(os.environ['DATABASE_URL']))"
```
Use Alembic migrations and role-based access controls before production.

## Design rules
- One email is a candidate shipment package, not a guaranteed unique shipment.
- A PDF can contain multiple logical document types (NMRA certificate + import licence).
- OCR is required for scanned AWB and NMRA samples.
- Distinguish `PASS`, `REVIEW`, `FAIL`, `NOT_VERIFIED`.
- Official licence authenticity/status is never inferred from the scan alone.
- Document and line-item evidence must reference page and source file.
- Never upload real customer data to a third-party AI API without DSH authorisation and approved data handling.
