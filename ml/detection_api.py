"""
Stockei - API de detecção de produtos (YOLOv8)

Produção: carrega YOLOv8 via ultralytics (models/yolov8n.pt ou custom_model.pt),
GPU quando disponível. Sem ultralytics instalado, usa MockDetector determinístico
para desenvolvimento e testes.

Rodar standalone: uvicorn ml.detection_api:app --port 8001
"""

import logging
import os
import time

from fastapi import FastAPI, File, UploadFile

logger = logging.getLogger("stockei.detection")

MODEL_PATH = os.environ.get("STOCKEI_MODEL_PATH", "models/yolov8n.pt")
CONFIDENCE_THRESHOLD = float(os.environ.get("STOCKEI_CONF_THRESHOLD", "0.5"))


class Detection(dict):
    """{class_id, class_name, confidence, bbox:[x1,y1,x2,y2]}"""


class YoloDetector:
    """Detector real via ultralytics (requer `pip install ultralytics`)."""

    def __init__(self, model_path: str = MODEL_PATH):
        from ultralytics import YOLO  # import tardio: dependência pesada

        self.model = YOLO(model_path)
        logger.info("YOLOv8 carregado de %s", model_path)

    def detect(self, image_bytes: bytes) -> list[Detection]:
        import io

        from PIL import Image

        image = Image.open(io.BytesIO(image_bytes))
        results = self.model.predict(image, conf=CONFIDENCE_THRESHOLD, verbose=False)
        detections = []
        for result in results:
            for box in result.boxes:
                detections.append(
                    Detection(
                        class_id=int(box.cls),
                        class_name=result.names[int(box.cls)],
                        confidence=float(box.conf),
                        bbox=[float(v) for v in box.xyxy[0]],
                    )
                )
        return detections


class MockDetector:
    """
    Fallback determinístico para dev/testes sem GPU/ultralytics.
    Gera detecções pseudo-aleatórias estáveis a partir do hash da imagem.
    """

    CLASSES = ["produto_caixa", "produto_garrafa", "produto_lata", "produto_pacote"]

    def detect(self, image_bytes: bytes) -> list[Detection]:
        import hashlib

        seed = int(hashlib.md5(image_bytes).hexdigest()[:8], 16) if image_bytes else 0
        count = seed % 4  # 0-3 detecções
        detections = []
        for i in range(count):
            k = (seed >> (i * 4)) & 0xFF
            x1, y1 = float(k % 400), float((k * 3) % 400)
            detections.append(
                Detection(
                    class_id=k % len(self.CLASSES),
                    class_name=self.CLASSES[k % len(self.CLASSES)],
                    confidence=round(0.55 + (k % 40) / 100, 2),
                    bbox=[x1, y1, x1 + 120.0, y1 + 150.0],
                )
            )
        return detections


def load_detector():
    try:
        return YoloDetector()
    except Exception as exc:  # ImportError ou modelo ausente
        logger.warning("YOLOv8 indisponível (%s); usando MockDetector", exc)
        return MockDetector()


detector = load_detector()

app = FastAPI(title="Stockei Detection API", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok", "detector": type(detector).__name__}


@app.post("/detect")
async def detect(image: UploadFile = File(...)):
    """Recebe imagem, retorna detecções com bounding boxes, classes e confiança."""
    start = time.perf_counter()
    data = await image.read()
    detections = detector.detect(data)
    latency_ms = (time.perf_counter() - start) * 1000
    logger.info("detect: %d objetos em %.1fms", len(detections), latency_ms)
    return {
        "detections": detections,
        "count": len(detections),
        "latency_ms": round(latency_ms, 2),
        "model": type(detector).__name__,
    }
