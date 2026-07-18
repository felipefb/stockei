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
    // Câmera traseira no celular. iOS/Safari ignora "ideal", então tentamos
    // "exact" primeiro e caímos para o padrão se o aparelho não tiver traseira.
    const base = { width: { ideal: 1280 }, height: { ideal: 720 }, frameRate: { ideal: 30 } };
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { ...base, facingMode: { exact: "environment" } },
        audio: false,
      });
    } catch (err) {
      if (err.name !== "OverconstrainedError" && err.name !== "NotFoundError") throw err;
      mediaStream = await navigator.mediaDevices.getUserMedia({
        video: base,
        audio: false,
      });
    }
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

/**
 * Extrai o frame atual como Blob JPEG preservando a proporção do vídeo.
 * maxSide 640 para o streaming de detecção; use captureFrameHiRes() para OCR.
 */
function captureFrame(maxSide = TARGET_SIZE) {
  const vw = els.video.videoWidth || TARGET_SIZE;
  const vh = els.video.videoHeight || TARGET_SIZE;
  const scale = Math.min(1, maxSide / Math.max(vw, vh));
  const canvas = els.canvas;
  canvas.width = Math.round(vw * scale);
  canvas.height = Math.round(vh * scale);
  const ctx = canvas.getContext("2d");
  ctx.drawImage(els.video, 0, 0, canvas.width, canvas.height);
  return new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", JPEG_QUALITY));
}

/** Frame em alta resolução (proporção preservada) para OCR de nome/validade. */
function captureFrameHiRes() {
  return captureFrame(1600);
}

async function sendFrame(showLoading = true) {
  const blob = await captureFrame();
  if (!blob) return;
  // No streaming contínuo o "Processando…" piscando 3x/s treme o layout —
  // só aparece na captura manual.
  if (showLoading) els.loading.hidden = false;
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
    if (showLoading) els.loading.hidden = true;
  }
}

function renderDetections(result) {
  const items = result.detections || [];
  // Atualização estável: reaproveita os <li> existentes em vez de recriar a
  // lista inteira — evita reflow/salto de layout a cada frame.
  const list = els.detections;
  if (items.length === 0) {
    if (!list.querySelector(".empty")) {
      list.innerHTML = "<li class='empty'>Nenhum produto detectado</li>";
    }
  } else {
    list.querySelector(".empty")?.remove();
    const lis = list.querySelectorAll("li");
    items.forEach((det, i) => {
      const text = `${det.class_name} — ${(det.confidence * 100).toFixed(1)}%`;
      if (lis[i]) {
        if (lis[i].textContent !== text) lis[i].textContent = text;
      } else {
        const li = document.createElement("li");
        li.textContent = text;
        list.appendChild(li);
      }
    });
    for (let i = items.length; i < lis.length; i++) lis[i].remove();
  }
  drawBoxes(items);
}

function drawBoxes(items) {
  const overlay = els.overlay;
  const w = els.video.clientWidth;
  const h = els.video.clientHeight;
  // Redimensionar um canvas o limpa e força repaint — só quando mudar de fato.
  if (overlay.width !== w || overlay.height !== h) {
    overlay.width = w;
    overlay.height = h;
  }
  const ctx = overlay.getContext("2d");
  ctx.clearRect(0, 0, overlay.width, overlay.height);
  ctx.strokeStyle = "#c6ff3e";
  ctx.lineWidth = 2;
  ctx.font = "12px monospace";
  ctx.fillStyle = "#c6ff3e";
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
    streamTimer = setInterval(() => sendFrame(false), 1000 / STREAM_FPS);
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
