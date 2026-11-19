"use strict";

/* === API CONTRACT (docs/api.md) === */
const API_BASE = "/api/v1";
const ENDPOINTS = {
  health: `${API_BASE}/health`,
  predictions: `${API_BASE}/predictions`,
  stats: `${API_BASE}/stats`,
  model: `${API_BASE}/model`,
  logs: `${API_BASE}/logs`,
};

const MAX_IMAGE_BYTES = 10 * 1024 * 1024;
const ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];
const CONTINUOUS_INTERVAL_MS = 1500;
const VIDEO_FRAME_LIMIT = 8;
const HISTORY_PER_PAGE = 10;

/* Okabe-Ito palette: distinguishable without relying on red/green alone. */
const CHART_COLORS = [
  "#E69F00", "#56B4E9", "#009E73", "#F0E442",
  "#0072B2", "#D55E00", "#CC79A7", "#6B4423",
];

const state = {
  stream: null,
  continuousTimer: null,
  predictionInFlight: false,
  selectedImage: null,
  imagePreviewUrl: null,
  selectedVideo: null,
  videoUrl: null,
  videoToken: 0,
  historyPage: 1,
  historyPages: 0,
  charts: { labels: null, sources: null },
};

class ApiError extends Error {
  constructor(message, code = "internal_error", details = null) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.details = details;
  }
}

const el = (id) => document.getElementById(id);

/** Fetch JSON and translate the API error envelope into a Spanish message. */
async function readResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  let payload = null;
  if (contentType.includes("application/json")) {
    try {
      payload = await response.json();
    } catch (error) {
      payload = null;
    }
  }
  if (!response.ok) {
    const error = payload && payload.error ? payload.error : {};
    const fallback = response.status === 413
      ? "El archivo supera el tamaño máximo permitido."
      : "La solicitud no se pudo completar.";
    throw new ApiError(error.message || fallback, error.code || `http_${response.status}`, error.details || null);
  }
  if (payload === null) {
    throw new ApiError("El servidor devolvió una respuesta inesperada.", "bad_response");
  }
  return payload;
}

async function apiGet(url, params = {}) {
  const target = new URL(url, window.location.origin);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== "" && value !== null && value !== undefined) {
      target.searchParams.set(key, String(value));
    }
  });
  let response;
  try {
    response = await fetch(target, { headers: { Accept: "application/json" } });
  } catch (error) {
    throw new ApiError("No se pudo conectar con el servidor. Comprueba que la aplicación esté en marcha.", "network_error");
  }
  return readResponse(response);
}

async function apiPostImage(blob, source, filename) {
  const form = new FormData();
  form.append("image", blob, filename);
  form.append("source", source);
  let response;
  try {
    response = await fetch(ENDPOINTS.predictions, {
      method: "POST",
      body: form,
      headers: { Accept: "application/json" },
    });
  } catch (error) {
    throw new ApiError("No se pudo enviar la imagen. Comprueba la conexión e inténtalo de nuevo.", "network_error");
  }
  return readResponse(response);
}

/* === FEEDBACK AND FORM ERRORS === */
function setStatus(id, message) {
  const node = el(id);
  if (node) node.textContent = message;
}

function setFieldError(fieldId, message) {
  const errorNode = el(`${fieldId}-error`);
  if (errorNode) {
    errorNode.textContent = message;
    errorNode.hidden = false;
  }
  const field = el(fieldId);
  if (field) field.setAttribute("aria-invalid", "true");
}

function clearErrors() {
  el("global-alert").hidden = true;
  el("error-list").replaceChildren();
  document.querySelectorAll(".field-error").forEach((node) => {
    node.hidden = true;
    node.textContent = "";
  });
  document.querySelectorAll("[aria-invalid]").forEach((node) => node.removeAttribute("aria-invalid"));
}

/** Show an announced, focusable error summary with a link to the field. */
function showError(message, fieldId = null) {
  const alertBox = el("global-alert");
  const list = el("error-list");
  const item = document.createElement("li");
  const text = document.createElement("span");
  text.textContent = message;
  item.append(text);

  if (fieldId && el(fieldId)) {
    const link = document.createElement("button");
    link.type = "button";
    link.className = "btn btn-ghost";
    link.textContent = "Ir al campo";
    link.addEventListener("click", () => {
      el(fieldId).focus();
      el(fieldId).scrollIntoView({ block: "center" });
    });
    item.append(link);
    setFieldError(fieldId, message);
  }

  list.replaceChildren(item);
  alertBox.hidden = false;
  alertBox.focus();
}

function updateActionButtons() {
  const busy = state.predictionInFlight;
  el("camera-start").disabled = Boolean(state.stream);
  el("camera-stop").disabled = !state.stream;
  el("camera-capture").disabled = !state.stream || busy;
  el("continuous-start").disabled = !state.stream || Boolean(state.continuousTimer) || busy;
  el("continuous-stop").disabled = !state.continuousTimer;
  el("upload-submit").disabled = !state.selectedImage || busy;
  el("video-analyze").disabled = !state.selectedVideo || busy;
  el("result").setAttribute("aria-busy", String(busy));
}

/* === FORMATTING AND RESULT === */
function formatConfidence(value) {
  return Number.isFinite(value) ? `${(value * 100).toFixed(1)} %` : "—";
}

function formatDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("es-ES", { dateStyle: "medium", timeStyle: "short" });
}

function createTop3Item(item) {
  const row = document.createElement("li");
  const label = document.createElement("span");
  label.textContent = item.label;
  const bar = document.createElement("span");
  bar.className = "top3-bar";
  bar.setAttribute("aria-hidden", "true");
  const fill = document.createElement("span");
  fill.style.width = `${Math.max(0, Math.min(100, Math.round((item.confidence || 0) * 100)))}%`;
  bar.append(fill);
  const value = document.createElement("strong");
  value.textContent = formatConfidence(item.confidence);
  row.append(label, bar, value);
  return row;
}

function renderPrediction(prediction, note = "") {
  el("result-empty").hidden = true;
  el("result-content").hidden = false;
  el("result-label").textContent = prediction.label || "—";
  el("result-confidence-text").textContent = formatConfidence(prediction.confidence);

  const percent = Math.max(0, Math.min(100, Math.round((prediction.confidence || 0) * 100)));
  el("result-confidence-fill").style.width = `${percent}%`;
  el("result-confidence-bar").setAttribute("aria-valuenow", String(percent));
  el("result-confidence-bar").setAttribute("aria-valuetext", formatConfidence(prediction.confidence));

  const list = el("result-top3");
  list.replaceChildren();
  (prediction.top3 || []).forEach((item) => list.append(createTop3Item(item)));

  el("result-source").textContent = prediction.source || "—";
  el("result-inference").textContent = Number.isFinite(prediction.inference_ms)
    ? `${prediction.inference_ms.toFixed(1)} ms`
    : "—";
  el("result-date").textContent = prediction.created_at ? formatDate(prediction.created_at) : "—";
  el("result-note").textContent = note;
  el("result-note").hidden = !note;
}

async function submitFrame(blob, source, filename, note = "") {
  if (state.predictionInFlight) return null;
  state.predictionInFlight = true;
  updateActionButtons();
  try {
    const prediction = await apiPostImage(blob, source, filename);
    renderPrediction(prediction, note);
    await Promise.allSettled([loadHistory(), loadStats()]);
    return prediction;
  } catch (error) {
    showError(error.message);
    return null;
  } finally {
    state.predictionInFlight = false;
    updateActionButtons();
  }
}

/* === CAMERA === */
function cameraMessageFromError(error) {
  const insecure = !window.isSecureContext && !["localhost", "127.0.0.1"].includes(window.location.hostname);
  if (insecure) return "La cámara solo funciona en localhost o con HTTPS. Puedes subir una imagen.";
  switch (error && error.name) {
    case "NotAllowedError":
    case "SecurityError":
      return "Permiso de cámara denegado. Habilítalo en el navegador o sube una imagen.";
    case "NotFoundError":
    case "DevicesNotFoundError":
      return "No se encontró una cámara. Puedes subir una imagen.";
    case "NotReadableError":
    case "TrackStartError":
      return "La cámara está ocupada por otra aplicación. Ciérrala e inténtalo de nuevo.";
    default:
      return "No se pudo iniciar la cámara. Puedes subir una imagen.";
  }
}

async function startCamera() {
  clearErrors();
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    showError("Tu navegador no permite acceder a la cámara. Puedes subir una imagen.");
    return;
  }
  try {
    state.stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" }, audio: false });
    const video = el("camera-preview");
    video.srcObject = state.stream;
    await video.play();
    el("camera-placeholder").hidden = true;
    setStatus("camera-status", "Cámara activa.");
    updateActionButtons();
  } catch (error) {
    state.stream = null;
    stopContinuous();
    const message = cameraMessageFromError(error);
    setStatus("camera-status", message);
    showError(message);
    updateActionButtons();
  }
}

function stopCamera() {
  stopContinuous();
  if (state.stream) {
    state.stream.getTracks().forEach((track) => track.stop());
    state.stream = null;
  }
  const video = el("camera-preview");
  video.srcObject = null;
  el("camera-placeholder").hidden = false;
  setStatus("camera-status", "Cámara detenida. Funciona solo en localhost o con HTTPS.");
  updateActionButtons();
}

function canvasToBlob(canvas, type, quality) {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) resolve(blob);
      else reject(new ApiError("No se pudo capturar la imagen.", "capture_error"));
    }, type, quality);
  });
}

function drawToCanvas(video, maxWidth) {
  const canvas = el("frame-canvas");
  const sourceWidth = video.videoWidth || 640;
  const sourceHeight = video.videoHeight || 480;
  const width = Math.min(sourceWidth, maxWidth);
  const height = Math.round((width * sourceHeight) / sourceWidth);
  canvas.width = width;
  canvas.height = height;
  canvas.getContext("2d").drawImage(video, 0, 0, width, height);
  return canvas;
}

async function captureCameraFrame() {
  const video = el("camera-preview");
  if (!state.stream || video.readyState < 2 || !video.videoWidth) {
    throw new ApiError("La cámara todavía no está lista. Espera un momento e inténtalo de nuevo.", "camera_not_ready");
  }
  return canvasToBlob(drawToCanvas(video, 1280), "image/jpeg", 0.9);
}

function startContinuous() {
  if (!state.stream || state.continuousTimer) return;
  setStatus("continuous-status", "Modo continuo activo: una predicción cada 1,5 s.");
  state.continuousTimer = window.setInterval(async () => {
    if (document.hidden || state.predictionInFlight) return;
    try {
      const frame = await captureCameraFrame();
      await submitFrame(frame, "camera", "continuo.jpg", "Captura del modo continuo.");
    } catch (error) {
      showError(error.message);
    }
  }, CONTINUOUS_INTERVAL_MS);
  updateActionButtons();
}

function stopContinuous() {
  if (state.continuousTimer) {
    window.clearInterval(state.continuousTimer);
    state.continuousTimer = null;
  }
  setStatus("continuous-status", "");
  updateActionButtons();
}

/* === UPLOAD === */
function validateImageFile(file) {
  if (!file) return "Selecciona una imagen.";
  if (!ALLOWED_IMAGE_TYPES.includes(file.type)) return "El archivo debe ser JPEG, PNG o WEBP.";
  if (file.size === 0) return "El archivo está vacío.";
  if (file.size > MAX_IMAGE_BYTES) return "El archivo supera los 10 MB permitidos.";
  return null;
}

function handleImageSelection(event) {
  clearErrors();
  const file = event.target.files[0];
  const problem = validateImageFile(file);
  if (problem) {
    state.selectedImage = null;
    el("upload-preview").hidden = true;
    showError(problem, "image-upload");
    updateActionButtons();
    return;
  }
  state.selectedImage = file;
  if (state.imagePreviewUrl) URL.revokeObjectURL(state.imagePreviewUrl);
  state.imagePreviewUrl = URL.createObjectURL(file);
  el("upload-preview").src = state.imagePreviewUrl;
  el("upload-preview").hidden = false;
  updateActionButtons();
}

async function handleUploadSubmit(event) {
  event.preventDefault();
  clearErrors();
  if (!state.selectedImage) {
    showError("Selecciona una imagen antes de clasificar.", "image-upload");
    return;
  }
  await submitFrame(state.selectedImage, "upload", state.selectedImage.name);
}

/* === VIDEO SAMPLING (browser side only) === */
function handleVideoSelection(event) {
  const file = event.target.files[0] || null;
  state.selectedVideo = file;
  if (state.videoUrl) URL.revokeObjectURL(state.videoUrl);
  state.videoUrl = file ? URL.createObjectURL(file) : null;
  setStatus("video-status", file ? `Video seleccionado: ${file.name}.` : "");
  updateActionButtons();
}

function waitForMetadata(video, url) {
  return new Promise((resolve, reject) => {
    const cleanup = () => {
      video.removeEventListener("loadedmetadata", onLoaded);
      video.removeEventListener("error", onError);
    };
    const onLoaded = () => { cleanup(); resolve(); };
    const onError = () => { cleanup(); reject(new ApiError("El archivo de video no se pudo abrir.", "video_error")); };
    video.addEventListener("loadedmetadata", onLoaded, { once: true });
    video.addEventListener("error", onError, { once: true });
    video.preload = "auto";
    video.src = url;
    video.load();
  });
}

function seekVideo(video, time) {
  return new Promise((resolve, reject) => {
    const cleanup = () => {
      video.removeEventListener("seeked", onSeeked);
      video.removeEventListener("error", onError);
    };
    const onSeeked = () => { cleanup(); resolve(); };
    const onError = () => { cleanup(); reject(new ApiError("No se pudo leer el video.", "video_error")); };
    video.addEventListener("seeked", onSeeked, { once: true });
    video.addEventListener("error", onError, { once: true });
    video.currentTime = time;
  });
}

async function captureVideoFrame(video) {
  const canvas = drawToCanvas(video, 640);
  return canvasToBlob(canvas, "image/jpeg", 0.85);
}

function aggregateResults(results) {
  const counts = new Map();
  results.forEach((item) => {
    const entry = counts.get(item.label) || { label: item.label, count: 0, confidenceSum: 0, top3: item.top3 };
    entry.count += 1;
    entry.confidenceSum += item.confidence || 0;
    counts.set(item.label, entry);
  });
  const winner = [...counts.values()].sort((a, b) => b.count - a.count || b.confidenceSum - a.confidenceSum)[0];
  return {
    label: winner.label,
    confidence: winner.confidenceSum / winner.count,
    top3: winner.top3 || [],
    source: "video",
    created_at: results[results.length - 1].created_at,
  };
}

async function analyzeVideo() {
  if (!state.selectedVideo || state.predictionInFlight) return;
  const token = ++state.videoToken;
  const video = el("video-source");
  state.predictionInFlight = true;
  updateActionButtons();
  try {
    await waitForMetadata(video, state.videoUrl);
    const duration = Number.isFinite(video.duration) ? video.duration : 0;
    if (duration <= 0) throw new ApiError("No se pudo determinar la duración del video.", "video_error");

    const frameCount = Math.min(VIDEO_FRAME_LIMIT, Math.max(1, Math.floor(Math.min(duration, 12))));
    const step = duration / frameCount;
    const results = [];
    for (let index = 0; index < frameCount; index += 1) {
      if (token !== state.videoToken) return;
      setStatus("video-status", `Analizando fotograma ${index + 1} de ${frameCount}…`);
      await seekVideo(video, step * index + step / 2);
      const frame = await captureVideoFrame(video);
      const prediction = await apiPostImage(frame, "video", `fotograma-${index + 1}.jpg`);
      results.push(prediction);
      renderPrediction(prediction, `Fotograma ${index + 1} de ${frameCount}.`);
    }
    if (token !== state.videoToken || results.length === 0) return;
    renderPrediction(aggregateResults(results), `Resumen de ${results.length} fotogramas del video.`);
    await Promise.allSettled([loadHistory(), loadStats()]);
    setStatus("video-status", `Análisis terminado: ${results.length} fotogramas enviados.`);
  } catch (error) {
    showError(error.message);
    setStatus("video-status", "No se pudo analizar el video.");
  } finally {
    if (token === state.videoToken) {
      state.predictionInFlight = false;
      updateActionButtons();
    }
  }
}

/* === HISTORY === */
async function loadHistory() {
  const params = { page: state.historyPage, per_page: HISTORY_PER_PAGE };
  const label = el("history-label").value.trim();
  const source = el("history-source").value;
  if (label) params.label = label;
  if (source) params.source = source;
  try {
    renderHistory(await apiGet(ENDPOINTS.predictions, params));
  } catch (error) {
    showError(error.message);
  }
}

function createHistoryRow(item) {
  const row = document.createElement("tr");
  const values = [
    formatDate(item.created_at),
    item.label,
    formatConfidence(item.confidence),
    item.source || "—",
    Number.isFinite(item.inference_ms) ? item.inference_ms.toFixed(1) : "—",
  ];
  values.forEach((value) => {
    const cell = document.createElement("td");
    cell.textContent = value;
    row.append(cell);
  });
  return row;
}

function renderHistory(data) {
  state.historyPage = data.page || 1;
  state.historyPages = data.pages || 0;
  const items = data.items || [];
  el("history-empty").hidden = items.length > 0;
  el("history-table").hidden = items.length === 0;

  const body = el("history-body");
  body.replaceChildren();
  items.forEach((item) => body.append(createHistoryRow(item)));

  el("history-page").textContent = `Página ${state.historyPage} de ${Math.max(state.historyPages, 1)}`;
  el("history-prev").disabled = state.historyPage <= 1;
  el("history-next").disabled = state.historyPage >= state.historyPages;
}

/* === STATISTICS AND CHARTS === */
function fillTable(tableId, rows, labelKey, emptyText) {
  const body = el(tableId).tBodies[0];
  body.replaceChildren();
  if (rows.length === 0) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 2;
    cell.textContent = emptyText;
    row.append(cell);
    body.append(row);
    return;
  }
  rows.forEach((item) => {
    const row = document.createElement("tr");
    const labelCell = document.createElement("td");
    labelCell.textContent = item[labelKey];
    const countCell = document.createElement("td");
    countCell.textContent = String(item.count);
    row.append(labelCell, countCell);
    body.append(row);
  });
}

function renderChart(key, title, rows, labelKey) {
  if (state.charts[key]) {
    state.charts[key].destroy();
    state.charts[key] = null;
  }
  if (rows.length === 0 || typeof window.Chart === "undefined") return;

  const colors = rows.map((_, index) => CHART_COLORS[index % CHART_COLORS.length]);
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  state.charts[key] = new window.Chart(el(`chart-${key}`), {
    type: "bar",
    data: {
      labels: rows.map((row) => row[labelKey]),
      datasets: [{
        label: title,
        data: rows.map((row) => row.count),
        backgroundColor: colors,
        borderColor: colors,
        borderWidth: 1,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: reducedMotion ? false : { duration: 300 },
      plugins: {
        legend: { display: true, position: "top" },
        tooltip: { callbacks: { label: (context) => `${context.label}: ${context.parsed.y}` } },
      },
      scales: {
        x: { grid: { display: false } },
        y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: "rgba(148, 163, 184, 0.25)" } },
      },
    },
  });
}

function renderStats(data) {
  el("stats-total").textContent = String(data.total ?? 0);
  el("stats-confidence").textContent = Number.isFinite(data.mean_confidence)
    ? formatConfidence(data.mean_confidence)
    : "—";

  const byLabel = data.by_label || [];
  const bySource = data.by_source || [];
  const empty = byLabel.length === 0 && bySource.length === 0;
  el("stats-empty").hidden = !empty;
  el("charts").hidden = empty;

  fillTable("table-labels", byLabel, "label", "Sin etiquetas registradas.");
  fillTable("table-sources", bySource, "source", "Sin fuentes registradas.");
  renderChart("labels", "Predicciones por etiqueta", byLabel, "label");
  renderChart("sources", "Predicciones por fuente", bySource, "source");
}

async function loadStats() {
  try {
    renderStats(await apiGet(ENDPOINTS.stats));
  } catch (error) {
    showError(error.message);
  }
}

/* === MODEL INFO === */
function renderModel(data) {
  el("model-empty").hidden = true;
  el("model-content").hidden = false;
  el("model-architecture").textContent = data.architecture || "—";
  el("model-classes").textContent = String(data.num_classes ?? (data.labels || []).length);

  const official = data.metrics && data.metrics.official_test;
  el("model-accuracy").textContent = official && Number.isFinite(official.accuracy)
    ? formatConfidence(official.accuracy)
    : "—";

  const real = data.metrics && data.metrics.real_test;
  if (!real) el("model-real-test").textContent = "—";
  else if (real.status === "ok") el("model-real-test").textContent = Number.isFinite(real.accuracy) ? formatConfidence(real.accuracy) : "Completada";
  else el("model-real-test").textContent = "Pendiente";

  const chips = el("model-labels");
  chips.replaceChildren();
  (data.labels || []).forEach((name) => {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = name;
    chips.append(chip);
  });

  el("model-details").textContent = JSON.stringify({
    preprocessing: data.preprocessing,
    training: data.training,
    metrics: data.metrics,
  }, null, 2);
}

async function loadModel() {
  try {
    renderModel(await apiGet(ENDPOINTS.model));
  } catch (error) {
    if (error.code === "model_unavailable" || error.code === "bad_response") {
      setStatus("model-empty", "El modelo no está cargado en este momento.");
    } else {
      showError(error.message);
    }
  }
}

/* === LOGS AND HEALTH === */
function renderLogs(data) {
  const entries = data.entries || [];
  el("logs-empty").hidden = entries.length > 0;
  el("logs-list").hidden = entries.length === 0;
  const list = el("logs-list");
  list.replaceChildren();
  entries.forEach((entry) => {
    const item = document.createElement("li");
    item.textContent = `${entry.timestamp || "—"} ${entry.level || ""} ${entry.logger || ""}: ${entry.message || ""}`;
    list.append(item);
  });
}

async function loadLogs() {
  try {
    renderLogs(await apiGet(ENDPOINTS.logs, { limit: 50 }));
  } catch (error) {
    showError(error.message);
  }
}

async function checkHealth() {
  const badge = el("health-badge");
  try {
    const data = await apiGet(ENDPOINTS.health);
    const healthy = data.status === "ok" && data.database === "ok" && data.model === "loaded";
    badge.textContent = healthy
      ? "Servicio listo"
      : `Servicio degradado (base: ${data.database}, modelo: ${data.model})`;
    badge.className = `badge ${healthy ? "badge-ok" : "badge-error"}`;
  } catch (error) {
    badge.textContent = "Servicio no disponible";
    badge.className = "badge badge-error";
  }
}

/* === WIRING === */
function bindEvents() {
  el("camera-start").addEventListener("click", () => { void startCamera(); });
  el("camera-stop").addEventListener("click", stopCamera);
  el("camera-capture").addEventListener("click", async () => {
    clearErrors();
    try {
      const frame = await captureCameraFrame();
      await submitFrame(frame, "camera", "captura-camara.jpg");
    } catch (error) {
      showError(error.message);
    }
  });
  el("continuous-start").addEventListener("click", startContinuous);
  el("continuous-stop").addEventListener("click", stopContinuous);

  el("image-upload").addEventListener("change", handleImageSelection);
  el("upload-form").addEventListener("submit", (event) => { void handleUploadSubmit(event); });
  el("video-upload").addEventListener("change", handleVideoSelection);
  el("video-analyze").addEventListener("click", () => { void analyzeVideo(); });

  el("history-refresh").addEventListener("click", () => { void loadHistory(); });
  el("stats-refresh").addEventListener("click", () => { void loadStats(); });
  el("logs-refresh").addEventListener("click", () => { void loadLogs(); });
  el("history-prev").addEventListener("click", () => {
    if (state.historyPage > 1) { state.historyPage -= 1; void loadHistory(); }
  });
  el("history-next").addEventListener("click", () => {
    if (state.historyPage < state.historyPages) { state.historyPage += 1; void loadHistory(); }
  });
  el("history-label").addEventListener("change", () => { state.historyPage = 1; void loadHistory(); });
  el("history-source").addEventListener("change", () => { state.historyPage = 1; void loadHistory(); });

  document.addEventListener("visibilitychange", () => {
    if (document.hidden && state.continuousTimer) stopContinuous();
  });
  window.addEventListener("pagehide", () => {
    stopContinuous();
    stopCamera();
    if (state.imagePreviewUrl) URL.revokeObjectURL(state.imagePreviewUrl);
    if (state.videoUrl) URL.revokeObjectURL(state.videoUrl);
  });
}

function init() {
  bindEvents();
  updateActionButtons();
  void Promise.allSettled([checkHealth(), loadHistory(), loadStats(), loadModel(), loadLogs()]);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
