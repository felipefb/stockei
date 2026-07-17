/**
 * Stockei — Captura e streaming de câmera
 * getUserMedia 640x480@30fps → frames JPEG 640x640 (80%) → backend a 3 FPS.
 */

// Vazio = mesma origem (portal servido pelo backend); sobrescreva com window.STOCKEI_API.
const API_BASE =
  (typeof window !== "undefined" && window.STOCKEI_API) || "";
const TARGET_SIZE = 640;
const JPEG_QUALITY = 0.8;
const STREAM_FPS = 3;

const IS_BROWSER = typeof document !== "undefined";

const els = !IS_BROWSER ? {} : {
  video: document.getElementById("video"),
  overlay: document.getElementById("overlay"),
  canvas: document.getElementById("capture-canvas"),
  start: document.getElementById("btn-start"),
  stop: document.getElementById("btn-stop"),
  frame: document.getElementById("btn-frame"),
  stream: document.getElementById("chk-stream"),
  status: document.getElementById("status-badge"),
  error: document.getElementById("error-box"),
  loading: document.getElementById("loading"),
  detections: document.getElementById("detections"),
};

let mediaStream = null;
let streamTimer = null;

function setStatus(text, cls) {
  els.status.textContent = text;
  els.status.className = `badge ${cls}`;
}

function showError(message) {
  els.error.textContent = message;
  els.error.hidden = false;
}

function clearError() {
  els.error.hidden = true;
}

async function startCamera() {
  clearError();
  try {
    // facingMode "environment" = câmera traseira no celular (notebooks ignoram)
    const constraints = {
      video: {
        facingMode: { ideal: "environment" },
        width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 30 },
      },
      audio: false,
    };
    mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
    els.video.srcObject = mediaStream;
    els.start.disabled = true;
    els.stop.disabled = false;
    els.frame.disabled = false;
    setStatus("Câmera ativa", "online");
  } catch (err) {
    if (err.name === "NotAllowedError") {
      showError("Permissão de câmera negada. Autorize o acesso nas configurações do navegador.");
    } else if (err.name === "NotFoundError") {
      showError("Nenhuma câmera encontrada neste dispositivo.");
    } else {
      showError(`Erro ao acessar câmera: ${err.message}`);
    }
    setStatus("Erro", "error");
  }
}

function stopCamera() {
  if (streamTimer) toggleStreaming(false);
  els.stream.checked = false;
  if (mediaStream) {
    mediaStream.getTracks().forEach((t) => t.stop());
    mediaStream = null;
  }
  els.video.srcObject = null;
  els.start.disabled = false;
  els.stop.disabled = true;
  els.frame.disabled = true;
  setStatus("Câmera desligada", "offline");
}

/** Extrai frame atual como Blob JPEG 640x640. */
function captureFrame() {
  const canvas = els.canvas;
  canvas.width = TARGET_SIZE;
  canvas.height = TARGET_SIZE;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(els.video, 0, 0, TARGET_SIZE, TARGET_SIZE);
  return new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", JPEG_QUALITY));
}

async function sendFrame() {
  const blob = await captureFrame();
  if (!blob) return;
  els.loading.hidden = false;
  try {
    const form = new FormData();
    form.append("frame", blob, "frame.jpg");
    const resp = await fetch(`${API_BASE}/process-frame`, { method: "POST", body: form });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    renderDetections(await resp.json());
    clearError();
  } catch (err) {
    showError(`Falha ao enviar frame: ${err.message}`);
  } finally {
    els.loading.hidden = true;
  }
}

function renderDetections(result) {
  els.detections.innerHTML = "";
  const items = result.detections || [];
  if (items.length === 0) {
    els.detections.innerHTML = "<li class='empty'>Nenhum produto detectado</li>";
    return;
  }
  for (const det of items) {
    const li = document.createElement("li");
    li.textContent = `${det.class_name} — ${(det.confidence * 100).toFixed(1)}%`;
    els.detections.appendChild(li);
  }
  drawBoxes(items);
}

function drawBoxes(items) {
  const overlay = els.overlay;
  overlay.width = els.video.clientWidth;
  overlay.height = els.video.clientHeight;
  const ctx = overlay.getContext("2d");
  ctx.clearRect(0, 0, overlay.width, overlay.height);
  ctx.strokeStyle = "#22c55e";
  ctx.lineWidth = 2;
  ctx.font = "12px sans-serif";
  ctx.fillStyle = "#22c55e";
  const sx = overlay.width / TARGET_SIZE;
  const sy = overlay.height / TARGET_SIZE;
  for (const det of items) {
    const [x1, y1, x2, y2] = det.bbox;
    ctx.strokeRect(x1 * sx, y1 * sy, (x2 - x1) * sx, (y2 - y1) * sy);
    ctx.fillText(det.class_name, x1 * sx + 2, y1 * sy - 4);
  }
}

function toggleStreaming(enabled) {
  if (enabled && mediaStream) {
    streamTimer = setInterval(sendFrame, 1000 / STREAM_FPS);
    setStatus(`Transmitindo (${STREAM_FPS} FPS)`, "streaming");
  } else {
    clearInterval(streamTimer);
    streamTimer = null;
    if (mediaStream) setStatus("Câmera ativa", "online");
  }
}

if (IS_BROWSER) {
  els.start.addEventListener("click", startCamera);
  els.stop.addEventListener("click", stopCamera);
  els.frame.addEventListener("click", sendFrame);
  els.stream.addEventListener("change", (e) => toggleStreaming(e.target.checked));
}

// Exporta para testes (Node)
if (typeof module !== "undefined") {
  module.exports = { TARGET_SIZE, JPEG_QUALITY, STREAM_FPS };
}
