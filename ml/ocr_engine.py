"""
Stockei - Engine de OCR para datas de validade.

Produção: Tesseract (pytesseract) + pré-processamento OpenCV.
Sem as libs instaladas, MockOCR permite desenvolvimento/testes.

Endpoint: POST /ocr/date (montado no app de detecção ou standalone).
"""

import logging
import time

from fastapi import APIRouter, File, UploadFile

from ml.date_validation import extract_date

logger = logging.getLogger("stockei.ocr")


class TesseractOCR:
    """OCR real: OpenCV (pré-processamento) + Tesseract."""

    def __init__(self):
        import cv2  # noqa: F401
        import pytesseract  # noqa: F401

        self._cv2 = cv2
        self._tess = pytesseract

    def read_text(self, image_bytes: bytes) -> str:
        import numpy as np

        cv2 = self._cv2
        img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        # Pré-processamento: cinza -> contraste (CLAHE) -> denoise -> binariza
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        gray = cv2.fastNlMeansDenoising(gray, h=10)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        config = "--psm 7 -c tessedit_char_whitelist=0123456789/-.VALENC: "
        return self._tess.image_to_string(binary, config=config)


class MockOCR:
    """Fallback: 'lê' texto embutido nos bytes (para testes) ou retorna vazio."""

    def read_text(self, image_bytes: bytes) -> str:
        try:
            return image_bytes.decode("utf-8", errors="ignore")
        except Exception:
            return ""


def load_ocr():
    try:
        engine = TesseractOCR()
        logger.info("Tesseract OCR carregado")
        return engine
    except Exception as exc:
        logger.warning("Tesseract indisponível (%s); usando MockOCR", exc)
        return MockOCR()


ocr = load_ocr()

router = APIRouter()


@router.post("/ocr/date")
async def ocr_date(image: UploadFile = File(...)):
    """Extrai data de validade da imagem. Retorna data + confiança ou erro."""
    start = time.perf_counter()
    data = await image.read()
    text = ocr.read_text(data)
    result = extract_date(text)
    latency_ms = round((time.perf_counter() - start) * 1000, 2)

    confidence = 0.95 if result["valid"] else (0.4 if result["raw"] else 0.0)
    logger.info("ocr/date: valid=%s raw=%r %.1fms", result["valid"], result["raw"], latency_ms)
    return {**result, "confidence": confidence, "latency_ms": latency_ms}
