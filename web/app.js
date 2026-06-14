const state = {
  defaults: {},
  inputs: {},
};

const quickKeys = [
  "b",
  "root_chord",
  "tip_chord",
  "taper_start_bl",
  "front_spar_percent",
  "rear_spar_percent",
  "front_spar_load_share",
  "rib_spacing",
  "config",
  "wing_structure_type",
  "front_spar_type",
  "rear_spar_type",
  "front_spar_mat",
  "rear_spar_mat",
  "n",
  "n_neg",
  "ng_lift",
  "Vd_mph",
  "altitude_ft",
  "Cm_ac",
  "dcell_enabled",
  "geodetic_enabled",
  "distribute_wing_weight",
];

function setStatus(message, kind = "") {
  const el = document.getElementById("status");
  el.textContent = message;
  el.className = `status ${kind}`;
}

function fillSelect(selector, values, current) {
  const el = document.querySelector(selector);
  el.innerHTML = "";
  for (const value of values) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    el.appendChild(option);
  }
  if (current !== undefined) el.value = current;
}

function syncFormFromInputs() {
  for (const key of quickKeys) {
    const el = document.querySelector(`[data-key="${key}"]`);
    if (!el) continue;
    if (el.type === "checkbox") {
      el.checked = Boolean(state.inputs[key]);
    } else {
      el.value = state.inputs[key] ?? "";
    }
  }
  document.getElementById("jsonEditor").value = JSON.stringify(state.inputs, null, 2);
}

function syncInputsFromForm() {
  for (const key of quickKeys) {
    const el = document.querySelector(`[data-key="${key}"]`);
    if (!el) continue;
    if (el.type === "checkbox") {
      state.inputs[key] = el.checked;
    } else if (el.tagName === "SELECT") {
      state.inputs[key] = el.value;
    } else {
      const value = Number(el.value);
      state.inputs[key] = Number.isFinite(value) ? value : el.value;
    }
  }
  document.getElementById("jsonEditor").value = JSON.stringify(state.inputs, null, 2);
}

function loadJsonEditor() {
  const text = document.getElementById("jsonEditor").value;
  state.inputs = JSON.parse(text);
  syncFormFromInputs();
}

function fmt(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return Number(value).toLocaleString(undefined, {
    maximumFractionDigits: digits,
  });
}

function updateCards(metrics) {
  document.getElementById("frontStress").textContent = `${fmt(metrics.sigma_max_front, 0)} psi`;
  document.getElementById("rearStress").textContent = `${fmt(metrics.sigma_max_rear, 0)} psi`;
  document.getElementById("sparWeight").textContent = `${fmt(metrics.spar_weight_total, 2)} lb`;
  document.getElementById("twistRoot").textContent = `${fmt(metrics.torsion?.phi_root_deg, 3)}°`;
}

function minMax(seriesList) {
  let min = Infinity;
  let max = -Infinity;
  for (const series of seriesList) {
    for (const value of series) {
      const n = Number(value);
      if (!Number.isFinite(n)) continue;
      min = Math.min(min, n);
      max = Math.max(max, n);
    }
  }
  if (!Number.isFinite(min) || !Number.isFinite(max)) return [-1, 1];
  if (min === max) return [min - 1, max + 1];
  const pad = (max - min) * 0.08;
  return [min - pad, max + pad];
}

function drawPlot(canvasId, title, x, series) {
  const canvas = document.getElementById(canvasId);
  const rect = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.max(640, rect.width * ratio);
  canvas.height = Math.max(360, rect.height * ratio);

  const ctx = canvas.getContext("2d");
  ctx.scale(ratio, ratio);
  const w = canvas.width / ratio;
  const h = canvas.height / ratio;
  const m = { left: 54, right: 18, top: 42, bottom: 42 };
  const pw = w - m.left - m.right;
  const ph = h - m.top - m.bottom;

  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#4c535f";
  ctx.fillRect(0, 0, w, h);

  ctx.strokeStyle = "#6e7f87";
  ctx.lineWidth = 1;
  ctx.strokeRect(m.left, m.top, pw, ph);

  const [xmin, xmax] = minMax([x]);
  const [ymin, ymax] = minMax(series.map((item) => item.values));
  const xToPx = (value) => m.left + ((value - xmin) / (xmax - xmin)) * pw;
  const yToPx = (value) => m.top + ph - ((value - ymin) / (ymax - ymin)) * ph;

  ctx.strokeStyle = "rgba(242,237,225,0.16)";
  ctx.fillStyle = "#b9bcc2";
  ctx.font = "12px Segoe UI, sans-serif";
  for (let i = 0; i <= 4; i++) {
    const yy = m.top + (ph * i) / 4;
    ctx.beginPath();
    ctx.moveTo(m.left, yy);
    ctx.lineTo(m.left + pw, yy);
    ctx.stroke();
    const val = ymax - ((ymax - ymin) * i) / 4;
    ctx.fillText(fmt(val, 1), 6, yy + 4);
  }

  ctx.fillStyle = "#d2b75f";
  ctx.font = "bold 15px Segoe UI, sans-serif";
  ctx.fillText(title, m.left, 24);

  series.forEach((item, idx) => {
    ctx.strokeStyle = item.color;
    ctx.lineWidth = item.width || 2;
    ctx.setLineDash(item.dash || []);
    ctx.beginPath();
    item.values.forEach((value, i) => {
      const px = xToPx(x[i]);
      const py = yToPx(value);
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    });
    ctx.stroke();
    ctx.setLineDash([]);

    ctx.fillStyle = item.color;
    ctx.font = "12px Segoe UI, sans-serif";
    ctx.fillText(item.label, m.left + 8 + idx * 110, h - 14);
  });
}

function renderPlots(payload) {
  window.lastPayload = payload;
  const s = payload.series;
  const x = s.x;
  drawPlot("plotLift", "Lift Distribution", x, [
    { label: "+g", values: s.positive.w, color: "#085097" },
    { label: "-g", values: s.negative.w, color: "#d2b75f", dash: [6, 4] },
  ]);
  drawPlot("plotShear", "Shear", x, [
    { label: "+g", values: s.positive.V, color: "#085097" },
    { label: "-g", values: s.negative.V, color: "#d2b75f", dash: [6, 4] },
  ]);
  drawPlot("plotMoment", "Bending Moment", x, [
    { label: "+g", values: s.positive.M, color: "#085097" },
    { label: "-g", values: s.negative.M, color: "#d2b75f", dash: [6, 4] },
  ]);
  drawPlot("plotDeflection", "Deflection", x, [
    { label: "front +g", values: s.positive.z_front, color: "#085097" },
    { label: "rear +g", values: s.positive.z_rear, color: "#024084" },
    { label: "front -g", values: s.negative.z_front, color: "#d2b75f", dash: [6, 4] },
    { label: "rear -g", values: s.negative.z_rear, color: "#e5c87a", dash: [4, 4] },
  ]);
}

async function runAnalysis() {
  try {
    syncInputsFromForm();
    // Let advanced JSON override quick fields when the editor is open/edited.
    loadJsonEditor();
    setStatus("Running analysis...");
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ inputs: state.inputs }),
    });
    const payload = await response.json();
    if (!payload.ok) throw new Error(`${payload.error}\n${payload.traceback || ""}`);

    document.getElementById("summary").textContent = payload.summary;
    updateCards(payload.metrics);
    renderPlots(payload);
    setStatus("Analysis complete", "ok");
  } catch (error) {
    document.getElementById("summary").textContent = error.stack || String(error);
    setStatus("Analysis failed", "error");
  }
}

async function init() {
  const response = await fetch("/api/defaults");
  const payload = await response.json();
  state.defaults = payload.defaults;
  state.inputs = JSON.parse(JSON.stringify(payload.defaults));

  fillSelect('[data-key="config"]', ["strut_braced", "cantilever", "single_strut"], state.inputs.config);
  fillSelect(
    '[data-key="wing_structure_type"]',
    ["fabric_tube", "fabric_buildup", "aluminum_skin"],
    state.inputs.wing_structure_type
  );
  fillSelect('[data-key="front_spar_type"]', payload.sparTypes, state.inputs.front_spar_type);
  fillSelect('[data-key="rear_spar_type"]', payload.sparTypes, state.inputs.rear_spar_type);
  fillSelect('[data-key="front_spar_mat"]', payload.materials, state.inputs.front_spar_mat);
  fillSelect('[data-key="rear_spar_mat"]', payload.materials, state.inputs.rear_spar_mat);

  syncFormFromInputs();
  for (const key of quickKeys) {
    const el = document.querySelector(`[data-key="${key}"]`);
    if (el) el.addEventListener("change", syncInputsFromForm);
  }
  document.getElementById("runBtn").addEventListener("click", runAnalysis);
  document.getElementById("resetBtn").addEventListener("click", () => {
    state.inputs = JSON.parse(JSON.stringify(state.defaults));
    syncFormFromInputs();
    setStatus("Defaults restored", "ok");
  });
  document.getElementById("downloadBtn").addEventListener("click", () => {
    syncInputsFromForm();
    const blob = new Blob([JSON.stringify(state.inputs, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "aerobeam-inputs.aerobeam";
    link.click();
    URL.revokeObjectURL(url);
  });

  setStatus("Ready", "ok");
  runAnalysis();
}

window.addEventListener("resize", () => {
  if (window.lastPayload) renderPlots(window.lastPayload);
});

init().catch((error) => {
  document.getElementById("summary").textContent = error.stack || String(error);
  setStatus("Startup failed", "error");
});
