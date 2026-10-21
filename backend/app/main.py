from .ai_extraction import (
    extract_structured_data,
    DOCUMENT_SCHEMAS,
)

from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from .schemas import Invoice, PackingList, AirWaybill
from .validation import validate_shipment


from .adapter import (
    convert_invoice,
    convert_packing_list,
    convert_air_waybill,
)

import pymupdf
import pytesseract
from PIL import Image
import io

from .cache import (
    generate_cache_key,
    get_cached_result,
    save_cached_result,
)

from .report import build_verification_report

app = FastAPI(title='DSH Document AI - Local Prototype')

class ValidationRequest(BaseModel):
    invoice: Invoice
    packing_list: PackingList
    air_waybill: AirWaybill

@app.get('/health')
def health():
    return {'status': 'ok'}


@app.post("/documents/extract-text")
async def extract_text(file: UploadFile = File(...)):
    data = await file.read(10 * 1024 * 1024 + 1)

    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(413, "File exceeds 10 MB limit")

    if not data.startswith(b"%PDF-"):
        raise HTTPException(400, "Expected a PDF")

    pytesseract.pytesseract.tesseract_cmd = (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )

    pages = []

    try:
        with pymupdf.open(stream=data, filetype="pdf") as pdf:
            if pdf.page_count > 30:
                raise HTTPException(413, "More than 30 pages")

            for page_number, page in enumerate(pdf, start=1):
                text = page.get_text("text").strip()
                method = "pdf_text"

                if not text:
                    pix = page.get_pixmap(
                        matrix=pymupdf.Matrix(2, 2),
                        alpha=False
                    )

                    image = Image.open(
                        io.BytesIO(pix.tobytes("png"))
                    )

                    text = pytesseract.image_to_string(
                        image,
                        lang="eng"
                    ).strip()

                    method = "ocr"

                pages.append({
                    "page": page_number,
                    "text": text,
                    "method": method
                })

    except HTTPException:
        raise
    except pytesseract.TesseractNotFoundError:
        raise HTTPException(
            500,
            "Tesseract OCR is not installed or path is incorrect"
        )
    except Exception as exc:
        print("PDF processing error:", repr(exc), flush=True)
        raise HTTPException(
            status_code=500,
            detail="PDF text extraction failed. Check backend logs."
    )


    return {
        "filename": file.filename,
        "pages": pages,
        "needs_ocr": any(
            p["method"] == "ocr" and not p["text"]
            for p in pages
        )
    }

@app.post('/shipments/validate')
def validate(payload: ValidationRequest):
    return {'findings': [f.model_dump(mode='json') for f in validate_shipment(payload.invoice, payload.packing_list, payload.air_waybill)]}


class StructuredExtractionRequest(BaseModel):
    document_type: str
    text: str



@app.post("/documents/extract-structured")
def extract_structured(
    payload: StructuredExtractionRequest
):
    if payload.document_type not in DOCUMENT_SCHEMAS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported document type"
        )

    if not payload.text.strip():
        raise HTTPException(
            status_code=400,
            detail="Document text cannot be empty"
        )

    try:
        result = extract_structured_data(
            text=payload.text,
            document_type=payload.document_type,
        )

        return result.model_dump(mode="json")

    except Exception as exc:
        print(
            "Gemini extraction error:",
            type(exc).__name__,
            str(exc),
            flush=True
        )

        raise HTTPException(
            status_code=502,
            detail="Gemini extraction failed. Check VS Code terminal."
        )

@app.post("/documents/upload-and-extract")
async def upload_and_extract(
    file: UploadFile = File(...),
    document_type: str = "invoice"
):
    # Only supported document types
    if document_type not in DOCUMENT_SCHEMAS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported document type"
        )

    # Read the uploaded PDF
    data = await file.read(10 * 1024 * 1024 + 1)

    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="File exceeds 10 MB limit"
        )

    if not data.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a PDF file"
        )

    pages = []

    try:
        with pymupdf.open(stream=data, filetype="pdf") as pdf:
            if pdf.page_count > 30:
                raise HTTPException(
                    status_code=413,
                    detail="PDF exceeds 30 pages"
                )

            for page in pdf:
                text = page.get_text("text").strip()

                # OCR for scanned pages
                if not text:
                    pix = page.get_pixmap(
                        matrix=pymupdf.Matrix(2, 2),
                        alpha=False
                    )

                    image = Image.open(
                        io.BytesIO(pix.tobytes("png"))
                    )

                    text = pytesseract.image_to_string(
                        image,
                        lang="eng"
                    ).strip()

                pages.append(text)

    except HTTPException:
        raise
    except pytesseract.TesseractNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="Tesseract OCR is not installed or configured"
        )
    except Exception as exc:
        print("PDF processing error:", repr(exc), flush=True)
        raise HTTPException(
            status_code=500,
            detail="PDF processing failed"
        )

    # Combine text from all PDF pages
    combined_text = "\n\n".join(pages).strip()

    if not combined_text:
        raise HTTPException(
            status_code=422,
            detail="No readable text found in PDF"
        )


    # Create a unique key for this PDF and document type
    cache_key = generate_cache_key(data, document_type)

    # Check whether this PDF was already processed
    cached_data = get_cached_result(cache_key)

    if cached_data is not None:
        print(f"Cache HIT: {document_type}", flush=True)
        extracted_data = cached_data
        from_cache = True

    else:
        print(f"Cache MISS: {document_type}", flush=True)

        # Only call Gemini when there is no saved result
        try:
            result = extract_structured_data(
                text=combined_text,
                document_type=document_type
            )

        except Exception as exc:
            print("Gemini extraction error:", repr(exc), flush=True)
            raise HTTPException(
                status_code=502,
                detail="Gemini extraction failed. Check backend logs."
            )

        extracted_data = result.model_dump(mode="json")

        # Save successful extraction for future requests
        save_cached_result(cache_key, extracted_data)
        from_cache = False

    return {
        "filename": file.filename,
        "document_type": document_type,
        "pages_processed": len(pages),
        "from_cache": from_cache,
        "extracted_data": extracted_data
    }


# =====================================
# VERIFY EXTRACTED DOCUMENTS
# =====================================

class ExtractedShipmentRequest(BaseModel):
    invoice: dict
    packing_list: dict
    air_waybill: dict


@app.post("/shipments/verify-extracted")
def verify_extracted_shipment(
    request: ExtractedShipmentRequest,
):
    invoice = convert_invoice(request.invoice)

    packing = convert_packing_list(
        request.packing_list
    )

    awb = convert_air_waybill(
        request.air_waybill
    )

    
    findings = validate_shipment(
        invoice,
        packing,
        awb,

    )


    return {
        "total_checks": len(findings),
        "passed": sum(
            f.status == "PASS" for f in findings
        ),
        "needs_review": sum(
            f.status == "REVIEW" for f in findings
        ),
        "not_verified": sum(
            f.status == "NOT_VERIFIED" for f in findings
        ),
        "findings": [
            f.model_dump(mode="json")
            for f in findings
        ],
    }


# =====================================
# AUTOMATIC SHIPMENT VERIFICATION
# =====================================

@app.post("/shipments/upload-and-verify")
async def upload_and_verify_shipment(
    invoice_file: UploadFile = File(...),
    packing_list_file: UploadFile = File(...),
    air_waybill_file: UploadFile = File(...),
):
    import pytesseract
    from io import BytesIO
    from PIL import Image
    from google.genai import errors

    MAX_FILE_SIZE = 10 * 1024 * 1024
    MAX_PAGES = 30

    # Use the same OCR installation as your existing endpoint.
    # Adjust this path if Tesseract is installed elsewhere.
    pytesseract.pytesseract.tesseract_cmd = (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )

    def read_pdf(file_bytes, filename):
        if len(file_bytes) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"{filename} exceeds the 10 MB limit",
            )

        if not file_bytes.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=400,
                detail=f"{filename} is not a valid PDF header",
            )

        try:
            with pymupdf.open(stream=file_bytes, filetype="pdf") as doc:
                if len(doc) > MAX_PAGES:
                    raise HTTPException(
                        status_code=400,
                        detail=f"{filename} exceeds 30 pages",
                    )

                text_parts = []

                for page in doc:
                    page_text = page.get_text("text")

                    if not page_text.strip():
                        pix = page.get_pixmap(dpi=200)
                        image = Image.open(
                            BytesIO(pix.tobytes("png"))
                        )
                        page_text = pytesseract.image_to_string(
                            image
                        )

                    text_parts.append(page_text)

                return "\n".join(text_parts)

        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Could not read {filename}: {exc}",
            )

    files = {
        "invoice": invoice_file,
        "packing_list": packing_list_file,
        "air_waybill": air_waybill_file,
    }

    extracted = {}

    for document_type, uploaded_file in files.items():

        if uploaded_file.content_type != "application/pdf":
            raise HTTPException(
                status_code=400,
                detail=f"{document_type} must be a PDF",
            )

        file_bytes = await uploaded_file.read()

        document_text = read_pdf(
            file_bytes,
            uploaded_file.filename or document_type,
        )

        if not document_text.strip():
            raise HTTPException(
                status_code=422,
                detail=f"No readable text in {document_type}",
            )

        
        # Generate cache key from PDF bytes
        cache_key = generate_cache_key(
            file_bytes,
            document_type,
        )

        cached_data = get_cached_result(cache_key)

        if cached_data is not None:
            print(f"Cache HIT: {document_type}", flush=True)

            extracted[document_type] = cached_data

        else:
            print(f"Cache MISS: {document_type}", flush=True)

            try:
                result = extract_structured_data(
                    document_text,
                    document_type,
                )

            except errors.APIError as exc:
                print(
                    f"Gemini API error for {document_type}: {exc}",
                    flush=True,
                )
                raise HTTPException(
                    status_code=502,
                    detail=(
                        f"Gemini extraction failed for "
                        f"{document_type}: {exc.code}"
                    ),
                )

            except Exception as exc:
                print(
                    f"Extraction error for {document_type}: {exc!r}",
                    flush=True,
                )
                raise HTTPException(
                    status_code=502,
                    detail=(
                        f"Extraction failed for {document_type}. "
                        "Check the backend logs."
                    ),
                )

            extracted_data = result.model_dump(mode="json")

            # Save immediately, before processing the next PDF
            save_cached_result(cache_key, extracted_data)

            extracted[document_type] = extracted_data


    invoice = convert_invoice(extracted["invoice"])

    packing = convert_packing_list(
        extracted["packing_list"]
    )

    awb = convert_air_waybill(
        extracted["air_waybill"]
    )


    findings = validate_shipment(
        invoice,
        packing,
        awb,
        packing_filename=packing_list_file.filename or "unknown_packing_list.pdf",
        awb_filename=air_waybill_file.filename or "unknown_air_waybill.pdf",
        invoice_filename=invoice_file.filename or "unknown_invoice.pdf",
    )


    
    report = build_verification_report(findings)

    return {
        "message": "Shipment verification completed",
        "documents": {
            key: {
                "filename": files[key].filename,
                "extracted_data": extracted[key],
            }
            for key in files
        },
        "summary": {
            "total_checks": report["total_checks"],
            **report["summary"],
        },
        "findings": report["findings"],
        "report": report,
    }
