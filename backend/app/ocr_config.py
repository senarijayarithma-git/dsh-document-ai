import os
import shutil

import pytesseract


def configure_tesseract() -> str:
    configured_path = os.getenv("TESSERACT_CMD")

    if configured_path:
        command = configured_path
    else:
        command = shutil.which("tesseract")

        if not command and os.name == "nt":
            windows_path = (
                r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            )

            if os.path.isfile(windows_path):
                command = windows_path

    if not command:
        raise RuntimeError(
            "Tesseract OCR is not installed or configured."
        )

    pytesseract.pytesseract.tesseract_cmd = command

    return command