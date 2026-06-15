const state = {
  defaults: {},
  inputs: {},
  options: {},
  runId: 0,
  isRunning: false,
};

const inputSections = [
  {
    id: "geometry",
    title: "Wing Geometry",
    groups: [
      {
        title: "Planform",
        fields: [
          ["b", "Span (in)", "number", "0.1"],
          ["r", "Root attach BL (in)", "number", "0.1"],
          ["root_chord", "Root chord (in)", "number", "0.1"],
          ["tip_chord", "Tip chord (in)", "number", "0.1"],
          ["taper_start_bl", "Taper start BL (in)", "number", "0.1"],
          ["rib_spacing", "Rib spacing (in)", "number", "0.1"],
          ["num_points", "Analysis stations", "number", "1"],
          ["lift_distribution_type", "Lift distribution", "select", ["schrenk", "elliptical", "chord_based", "uniform"]],
        ],
      },
      {
        title: "Spar Positions",
        fields: [
          ["front_spar_percent", "Front spar x/c", "number", "0.01"],
          ["rear_spar_percent", "Rear spar x/c", "number", "0.01"],
          ["front_spar_load_share", "Front spar load share", "number", "0.01"],
          ["num_spars", "Number of spars", "number", "1"],
        ],
      },
    ],
  },
  {
    id: "airfoil",
    title: "Flight & Airfoil",
    groups: [
      {
        title: "Airfoil",
        fields: [
          ["airfoil", "Airfoil name", "text"],
          ["airfoil_t_c", "Thickness t/c", "number", "0.001"],
          ["Cm_ac", "Cm aerodynamic moment", "number", "0.001"],
          ["Cm_flap", "Flap delta Cm", "number", "0.001"],
          ["Cl_alpha", "Cl_alpha (/rad)", "number", "0.01"],
          ["x_ac_c", "Aerodynamic center x/c", "number", "0.001"],
        ],
      },
      {
        title: "Flight Conditions",
        fields: [
          ["Vd_mph", "Dive speed Vd (mph)", "number", "1"],
          ["Vc_mph", "Cruise speed Vc (mph)", "number", "1"],
          ["Va_mph", "Maneuver speed Va (mph)", "number", "1"],
          ["altitude_ft", "Altitude (ft)", "number", "100"],
          ["curvature_sign", "Curvature sign", "number", "1"],
        ],
      },
    ],
  },
  {
    id: "loads",
    title: "Loads & Config",
    groups: [
      {
        title: "Loads",
        fields: [
          ["Weight", "Gross weight (lb)", "number", "1"],
          ["Wing_Weight", "Wing weight (lb)", "number", "1"],
          ["Tail_Down_1g", "Tail download at 1g (lb)", "number", "1"],
          ["n", "Positive load factor (+g)", "number", "0.1"],
          ["n_neg", "Negative load factor (-g)", "number", "0.1"],
          ["ng_lift", "Design semi-span lift (lb)", "number", "1"],
          ["distribute_wing_weight", "Distribute wing weight relief", "checkbox"],
        ],
      },
      {
        title: "Configuration, Strut, Jury",
        fields: [
          ["config", "Configuration", "select", ["strut_braced", "cantilever", "single_strut"]],
          ["strut_fuse_bl", "Strut BL at fuselage (in)", "number", "0.1"],
          ["strut_bl", "Strut BL at spar (in)", "number", "0.1"],
          ["strut_vert", "Strut rise (in)", "number", "0.1"],
          ["strut_mat", "Strut material", "select", "strutMaterials"],
          ["strut_tube_od", "Strut OD (in)", "number", "0.001"],
          ["strut_tube_wall", "Strut wall (in)", "number", "0.001"],
          ["secondary_bending", "P-delta amplification", "checkbox"],
          ["jury_strut", "Enable jury strut", "checkbox"],
          ["jury_spar_bl", "Jury spar BL (in)", "number", "0.1"],
        ],
      },
    ],
  },
  {
    id: "front",
    title: "Front Spar",
    groups: [
      { title: "Type & Tube", fields: sparFields("front_spar") },
      { title: "D-cell", fields: [["dcell_enabled", "Enable D-cell", "checkbox"], ["dcell_skin_mat", "D-cell material", "select", "materials"], ["dcell_skin_thick", "D-cell skin thickness (in)", "number", "0.001"]] },
    ],
  },
  {
    id: "rear",
    title: "Rear Spar",
    groups: [{ title: "Type & Geometry", fields: sparFields("rear_spar") }],
  },
  {
    id: "structure",
    title: "Wing Structure",
    groups: [
      {
        title: "Structure & Skin",
        fields: [
          ["wing_structure_type", "Wing structure type", "select", [
            { value: "fabric_tube", label: "Fabric / Tube ladder" },
            { value: "fabric_buildup", label: "Fabric / Built-up + D-cell + optional geodetic" },
            { value: "aluminum_skin", label: "Aluminum stressed skin" },
          ]],
          ["skin_top_mat", "Top skin material", "select", "materials"],
          ["skin_top_thick", "Top skin thickness (in)", "number", "0.001"],
          ["skin_bot_mat", "Bottom skin material", "select", "materials"],
          ["skin_bot_thick", "Bottom skin thickness (in)", "number", "0.001"],
          ["wood_knockdown", "Wood knockdown factor", "number", "0.01"],
        ],
      },
      {
        title: "Geodetic Box",
        fields: [
          ["geodetic_enabled", "Enable geodetic", "checkbox"],
          ["geodetic_mat", "Geodetic strip material", "select", "materials"],
          ["geodetic_w", "Strip width (in)", "number", "0.001"],
          ["geodetic_t", "Strip thickness (in)", "number", "0.001"],
          ["geodetic_strips_per_bay", "Strips per rib bay", "number", "1"],
          ["geodetic_angle", "Strip angle (deg)", "number", "1"],
        ],
      },
      {
        title: "Rib Structure",
        fields: [
          ["rib_mat", "Rib material", "select", "materials"],
          ["rib_h_web", "Rib web height (in)", "number", "0.001"],
          ["rib_t_web", "Rib web thickness (in)", "number", "0.001"],
          ["rib_b_cap", "Rib cap width (in)", "number", "0.001"],
          ["rib_t_cap", "Rib cap thickness (in)", "number", "0.001"],
        ],
      },
    ],
  },
  {
    id: "buckling",
    title: "Buckling",
    groups: [
      {
        title: "Stiffeners & Nose Ribs",
        fields: [
          ["stiffener_spacing", "Web stiffener spacing (in, 0=rib)", "number", "0.1"],
          ["nose_rib_spacing", "Nose rib spacing (in, 0=rib)", "number", "0.1"],
        ],
      },
      {
        title: "Web Doublers",
        fields: [
          ["front_spar_doubler_t", "Front doubler thickness (in)", "number", "0.001"],
          ["front_spar_doubler_extent", "Front doubler extent (rib bays)", "number", "1"],
          ["rear_spar_doubler_t", "Rear doubler thickness (in)", "number", "0.001"],
          ["rear_spar_doubler_extent", "Rear doubler extent (rib bays)", "number", "1"],
        ],
      },
    ],
  },
];

function sparFields(prefix) {
  return [
    [`${prefix}_type`, "Spar type", "select", "sparTypes"],
    [`${prefix}_mat`, "Tube/material", "select", "materials"],
    [`${prefix}_od`, "Tube OD (in)", "number", "0.001"],
    [`${prefix}_wall`, "Tube wall (in)", "number", "0.001"],
    [`${prefix}_width`, "Rect width (in)", "number", "0.001"],
    [`${prefix}_height`, "Rect height (in)", "number", "0.001"],
    [`${prefix}_cap_mat`, "Cap material", "select", "materials"],
    [`${prefix}_web_mat`, "Web material", "select", "materials"],
    [`${prefix}_b_top`, "Top cap width (in)", "number", "0.001"],
    [`${prefix}_t_top`, "Top cap height/thickness (in)", "number", "0.001"],
    [`${prefix}_b_bot`, "Bottom cap width (in)", "number", "0.001"],
    [`${prefix}_t_bot`, "Bottom cap height/thickness (in)", "number", "0.001"],
    [`${prefix}_h_web`, "Shear web clear height (in)", "number", "0.001"],
    [`${prefix}_t_web`, "Shear web thickness (in)", "number", "0.001"],
    [`${prefix}_web_spacing`, "Double web spacing (in)", "number", "0.001"],
    [`${prefix}_b_outer`, "Box outer width (in)", "number", "0.001"],
    [`${prefix}_h_outer`, "Box outer height (in)", "number", "0.001"],
    [`${prefix}_t_cap`, "Box cap thickness (in)", "number", "0.001"],
    [`${prefix}_cap_side`, "C-spar cap side", "select", ["top", "bottom"]],
  ];
}

function allInputKeys() {
  return inputSections.flatMap((section) =>
    section.groups.flatMap((group) => group.fields.map((field) => field[0]))
  );
}

function sparPrefixForKey(key) {
  if (key.startsWith("front_spar_")) return "front_spar";
  if (key.startsWith("rear_spar_")) return "rear_spar";
  return "";
}

function relevantSparKeys(prefix, sparType) {
  const common = new Set([`${prefix}_type`]);
  const keys = {
    "Round Tube": [`${prefix}_mat`, `${prefix}_od`, `${prefix}_wall`],
    "Plain Rectangular": [`${prefix}_cap_mat`, `${prefix}_width`, `${prefix}_height`],
    "I-Beam": [
      `${prefix}_cap_mat`, `${prefix}_web_mat`, `${prefix}_b_top`, `${prefix}_t_top`,
      `${prefix}_b_bot`, `${prefix}_t_bot`, `${prefix}_h_web`, `${prefix}_t_web`,
    ],
    "C-Channel": [
      `${prefix}_cap_mat`, `${prefix}_web_mat`, `${prefix}_b_top`, `${prefix}_t_top`,
      `${prefix}_b_bot`, `${prefix}_t_bot`, `${prefix}_h_web`, `${prefix}_t_web`,
    ],
    "Routed (Monolithic)": [
      `${prefix}_cap_mat`, `${prefix}_b_top`, `${prefix}_t_top`, `${prefix}_b_bot`,
      `${prefix}_t_bot`, `${prefix}_h_web`, `${prefix}_t_web`,
    ],
    "Double I-Beam": [
      `${prefix}_cap_mat`, `${prefix}_web_mat`, `${prefix}_b_top`, `${prefix}_t_top`,
      `${prefix}_b_bot`, `${prefix}_t_bot`, `${prefix}_h_web`, `${prefix}_t_web`,
      `${prefix}_web_spacing`,
    ],
    "Box Spar": [
      `${prefix}_cap_mat`, `${prefix}_web_mat`, `${prefix}_b_outer`, `${prefix}_h_outer`,
      `${prefix}_t_web`, `${prefix}_t_cap`,
    ],
    "Aluminum I-Beam": [
      `${prefix}_cap_mat`, `${prefix}_web_mat`, `${prefix}_b_top`, `${prefix}_t_top`,
      `${prefix}_b_bot`, `${prefix}_t_bot`, `${prefix}_h_web`, `${prefix}_t_web`,
    ],
    "Aluminum C-Spar": [
      `${prefix}_cap_mat`, `${prefix}_b_top`, `${prefix}_t_top`, `${prefix}_h_web`,
      `${prefix}_t_web`, `${prefix}_cap_side`,
    ],
  };
  for (const key of keys[sparType] || []) common.add(key);
  return common;
}

function isRelevantSparKey(key) {
  const prefix = sparPrefixForKey(key);
  if (!prefix) return true;
  const sparType = state.inputs[`${prefix}_type`] || state.defaults[`${prefix}_type`] || "Round Tube";
  return relevantSparKeys(prefix, sparType).has(key);
}

function isRelevantStructureKey(key) {
  const structure = state.inputs.wing_structure_type || state.defaults.wing_structure_type || "fabric_tube";
  const geodeticEnabled = parseBool(state.inputs.geodetic_enabled);
  const geodeticDetails = new Set([
    "geodetic_mat",
    "geodetic_w",
    "geodetic_t",
    "geodetic_strips_per_bay",
    "geodetic_angle",
  ]);
  const skinDetails = new Set([
    "skin_top_mat",
    "skin_top_thick",
    "skin_bot_mat",
    "skin_bot_thick",
  ]);

  if (geodeticDetails.has(key)) {
    return structure === "fabric_buildup" && geodeticEnabled;
  }
  if (skinDetails.has(key)) {
    return structure === "aluminum_skin";
  }
  return true;
}

function setStatus(message, kind = "") {
  const el = document.getElementById("status");
  el.textContent = message;
  el.className = `status ${kind}`;
}

function renderMethodStatus(statusMap) {
  const target = document.getElementById("methodStatusList");
  if (!target) return;
  target.innerHTML = "";
  for (const item of Object.values(statusMap || {})) {
    const row = document.createElement("div");
    const pill = document.createElement("span");
    pill.className = `status-pill ${item.status}`;
    pill.textContent = item.status;
    row.appendChild(pill);
    row.append(`${item.label}: ${item.note}`);
    target.appendChild(row);
  }
}

function markInputsChanged() {
  if (!state.isRunning) {
    setStatus("Inputs changed — click Run Analysis");
  }
}

function authHeaders(extra = {}) {
  const password = (document.getElementById("betaPassword")?.value || "").trim();
  return password
    ? { ...extra, "X-AeroBeam-Password": password }
    : extra;
}

function betaPassword() {
  return (document.getElementById("betaPassword")?.value || "").trim();
}

function parseBool(value) {
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return value !== 0;
  if (value === null || value === undefined) return false;
  const text = String(value).trim().toLowerCase();
  if (["1", "true", "yes", "y", "on"].includes(text)) return true;
  if (["0", "false", "no", "n", "off", ""].includes(text)) return false;
  return Boolean(value);
}

function rememberBetaPassword() {
  const password = betaPassword();
  if (password) sessionStorage.setItem("aerobeamBetaPassword", password);
}

function syncFormFromInputs() {
  for (const key of allInputKeys()) {
    const el = document.querySelector(`[data-key="${key}"]`);
    if (!el) continue;
    if (el.type === "checkbox") {
      el.checked = parseBool(state.inputs[key]);
      state.inputs[key] = el.checked;
    } else {
      el.value = state.inputs[key] ?? "";
    }
  }
  updateAllSparFieldVisibility({ prune: true });
  document.getElementById("jsonEditor").value = JSON.stringify(state.inputs, null, 2);
}

function syncInputsFromForm() {
  for (const key of allInputKeys()) {
    const el = document.querySelector(`[data-key="${key}"]`);
    if (!el) continue;
    if (el.disabled) {
      delete state.inputs[key];
      continue;
    }
    if (el.type === "checkbox") {
      state.inputs[key] = el.checked;
    } else if (el.tagName === "SELECT") {
      state.inputs[key] = el.value;
    } else {
      const value = Number(el.value);
      state.inputs[key] = Number.isFinite(value) ? value : el.value;
    }
  }
  updateAllSparFieldVisibility({ prune: true });
  document.getElementById("jsonEditor").value = JSON.stringify(state.inputs, null, 2);
}

function setRunButtonRunning(running) {
  state.isRunning = running;
  const button = document.getElementById("runBtn");
  if (!button) return;
  button.disabled = running;
  button.textContent = running ? "Running..." : "Run Analysis";
}

function fieldDefault(key, type) {
  if (state.defaults[key] !== undefined) return state.defaults[key];
  if (type === "checkbox") return false;
  if (key.endsWith("_cap_mat")) return "Sitka Spruce";
  if (key.endsWith("_web_mat")) return "Birch Plywood";
  if (key.endsWith("_mat")) return "6061-T6";
  const defaults = {
    front_spar_width: 2.0,
    rear_spar_width: 2.0,
    front_spar_height: 4.0,
    rear_spar_height: 4.0,
    front_spar_b_top: 1.5,
    rear_spar_b_top: 1.5,
    front_spar_t_top: 0.75,
    rear_spar_t_top: 0.75,
    front_spar_b_bot: 1.5,
    rear_spar_b_bot: 1.5,
    front_spar_t_bot: 0.75,
    rear_spar_t_bot: 0.75,
    front_spar_h_web: 4.5,
    rear_spar_h_web: 4.5,
    front_spar_t_web: 0.125,
    rear_spar_t_web: 0.125,
    front_spar_web_spacing: 1.0,
    rear_spar_web_spacing: 1.0,
    front_spar_b_outer: 2.0,
    rear_spar_b_outer: 2.0,
    front_spar_h_outer: 5.0,
    rear_spar_h_outer: 5.0,
    front_spar_t_cap: 0.75,
    rear_spar_t_cap: 0.75,
    front_spar_cap_side: "top",
    rear_spar_cap_side: "top",
  };
  return defaults[key] ?? "";
}

function ensureSchemaDefaults() {
  for (const section of inputSections) {
    for (const group of section.groups) {
      for (const field of group.fields) {
        const [key, , type] = field;
        if (isRelevantSparKey(key) && isRelevantStructureKey(key) && state.inputs[key] === undefined) {
          state.inputs[key] = fieldDefault(key, type);
        }
      }
    }
  }
}

function optionsFor(choice) {
  if (Array.isArray(choice)) return choice;
  if (choice === "materials") return state.options.materials || [];
  if (choice === "strutMaterials") return state.options.strutMaterials || [];
  if (choice === "sparTypes") return state.options.sparTypes || [];
  return [];
}

function optionValue(option) {
  return typeof option === "object" ? option.value : option;
}

function optionLabel(option) {
  return typeof option === "object" ? option.label : option;
}

function createField(field) {
  const [key, label, type, meta] = field;
  const wrapper = document.createElement("label");
  wrapper.textContent = label;
  wrapper.dataset.key = key;
  const prefix = sparPrefixForKey(key);
  if (prefix) wrapper.dataset.sparPrefix = prefix;

  let input;
  if (type === "select") {
    input = document.createElement("select");
    for (const optionDef of optionsFor(meta)) {
      const option = document.createElement("option");
      option.value = optionValue(optionDef);
      option.textContent = optionLabel(optionDef);
      input.appendChild(option);
    }
  } else {
    input = document.createElement("input");
    input.type = type || "text";
    if (meta && type === "number") input.step = meta;
  }

  input.dataset.key = key;
  if (prefix) input.dataset.sparPrefix = prefix;
  if (type === "checkbox") {
    wrapper.classList.add("check");
    input.checked = parseBool(state.inputs[key]);
    wrapper.textContent = "";
    wrapper.appendChild(input);
    wrapper.append(` ${label}`);
  } else {
    input.value = state.inputs[key] ?? "";
    wrapper.appendChild(input);
  }
  input.addEventListener("input", () => {
    syncInputsFromForm();
    markInputsChanged();
  });
  input.addEventListener("change", () => {
    syncInputsFromForm();
    markInputsChanged();
  });
  return wrapper;
}

function updateSparFieldVisibility(prefix, { prune = false } = {}) {
  const typeKey = `${prefix}_type`;
  const sparType = state.inputs[typeKey] || state.defaults[typeKey] || "Round Tube";
  const relevant = relevantSparKeys(prefix, sparType);

  document.querySelectorAll(`[data-spar-prefix="${prefix}"]`).forEach((el) => {
    const key = el.dataset.key;
    if (!key) return;
    const visible = relevant.has(key);
    const wrapper = el.matches("label") ? el : document.querySelector(`label[data-key="${key}"]`);
    const input = el.matches("input, select, textarea") ? el : wrapper?.querySelector("input, select, textarea");
    if (wrapper) wrapper.classList.toggle("hidden-field", !visible);
    if (input) input.disabled = !visible;

    if (visible && state.inputs[key] === undefined) {
      const field = inputSections.flatMap((section) => section.groups).flatMap((group) => group.fields).find((item) => item[0] === key);
      state.inputs[key] = fieldDefault(key, field?.[2] || "text");
      if (input) {
        if (input.type === "checkbox") input.checked = parseBool(state.inputs[key]);
        else input.value = state.inputs[key] ?? "";
      }
    } else if (!visible && prune) {
      delete state.inputs[key];
    }
  });
}

function updateAllSparFieldVisibility(options = {}) {
  updateSparFieldVisibility("front_spar", options);
  updateSparFieldVisibility("rear_spar", options);
  updateStructureFieldVisibility(options);
}

function updateStructureFieldVisibility({ prune = false } = {}) {
  const managed = [
    "geodetic_mat",
    "geodetic_w",
    "geodetic_t",
    "geodetic_strips_per_bay",
    "geodetic_angle",
    "skin_top_mat",
    "skin_top_thick",
    "skin_bot_mat",
    "skin_bot_thick",
  ];

  for (const key of managed) {
    const wrapper = document.querySelector(`label[data-key="${key}"]`);
    const input = document.querySelector(`[data-key="${key}"]`);
    const visible = isRelevantStructureKey(key);
    if (wrapper) wrapper.classList.toggle("hidden-field", !visible);
    if (input) input.disabled = !visible;
    if (!visible && prune) delete state.inputs[key];
    if (visible && state.inputs[key] === undefined) {
      const field = inputSections.flatMap((section) => section.groups).flatMap((group) => group.fields).find((item) => item[0] === key);
      state.inputs[key] = fieldDefault(key, field?.[2] || "text");
      if (input) input.value = state.inputs[key] ?? "";
    }
  }
}

function renderInputTabs() {
  const tabs = document.getElementById("inputTabs");
  const panels = document.getElementById("inputTabPanels");
  tabs.innerHTML = "";
  panels.innerHTML = "";

  inputSections.forEach((section, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `tab-button ${index === 0 ? "active" : ""}`;
    button.textContent = section.title;
    button.addEventListener("click", () => {
      document.querySelectorAll(".tab-button").forEach((el) => el.classList.remove("active"));
      document.querySelectorAll(".input-tab-panel").forEach((el) => el.classList.remove("active"));
      button.classList.add("active");
      document.getElementById(`tab-${section.id}`).classList.add("active");
    });
    tabs.appendChild(button);

    const panel = document.createElement("div");
    panel.id = `tab-${section.id}`;
    panel.className = `input-tab-panel ${index === 0 ? "active" : ""}`;
    for (const group of section.groups) {
      const title = document.createElement("div");
      title.className = "input-section-title";
      title.textContent = group.title;
      panel.appendChild(title);
      const grid = document.createElement("section");
      grid.className = "grid";
      for (const field of group.fields) grid.appendChild(createField(field));
      panel.appendChild(grid);
    }
    panels.appendChild(panel);
  });
}

function normalizeLoadedInputs(payload) {
  if (payload && typeof payload === "object" && payload.inputs && typeof payload.inputs === "object") {
    return payload.inputs;
  }
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new Error("Input file must contain a JSON object.");
  }
  return payload;
}

function loadJsonEditor() {
  const text = document.getElementById("jsonEditor").value;
  state.inputs = JSON.parse(text);
  ensureSchemaDefaults();
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
  document.getElementById("relativeFlex").textContent = `${fmt(metrics.z_delta_max, 3)} in`;
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
  drawGeometry(s.geometry);
  drawPlot("plotLift", "Lift Distribution", x, [
    { label: "+g", values: s.positive.w, color: "#085097" },
    { label: "-g", values: s.negative.w, color: "#d2b75f", dash: [6, 4] },
  ]);
  drawPlot("plotShear", "Shear", x, [
    { label: "+g", values: s.positive.V, color: "#085097" },
    { label: "-g", values: s.negative.V, color: "#d2b75f", dash: [6, 4] },
  ]);
  drawPlot("plotMoment", "Spar Bending Moment", x, [
    { label: "front +g", values: s.positive.M_front, color: "#085097" },
    { label: "rear +g", values: s.positive.M_rear, color: "#024084", width: 1.8 },
    { label: "front -g", values: s.negative.M_front, color: "#d2b75f", dash: [6, 4] },
    { label: "rear -g", values: s.negative.M_rear, color: "#e5c87a", dash: [3, 4], width: 1.6 },
  ]);
  drawPlot("plotDeflection", "Deflection", x, [
    { label: "front +g", values: s.positive.z_front, color: "#085097" },
    { label: "rear +g", values: s.positive.z_rear, color: "#024084" },
    { label: "rear-front Δ +g", values: s.positive.z_delta, color: "#6e9b5a", dash: [2, 3], width: 1.4 },
    { label: "front -g", values: s.negative.z_front, color: "#d2b75f", dash: [6, 4] },
    { label: "rear -g", values: s.negative.z_rear, color: "#e5c87a", dash: [4, 4] },
  ]);
}

function drawGeometry(geometry) {
  const canvas = document.getElementById("plotGeometry");
  const rect = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.max(900, rect.width * ratio);
  canvas.height = Math.max(430, rect.height * ratio);
  const ctx = canvas.getContext("2d");
  ctx.scale(ratio, ratio);
  const w = canvas.width / ratio;
  const h = canvas.height / ratio;

  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#4c535f";
  ctx.fillRect(0, 0, w, h);
  ctx.fillStyle = "#d2b75f";
  ctx.font = "bold 15px Segoe UI, sans-serif";
  ctx.fillText("Plan View", 18, 24);
  ctx.fillText("Front Elevation", 18, h / 2 + 24);

  const x = geometry.x || [];
  const chord = geometry.chord || [];
  const front = geometry.front_spar || [];
  const rear = geometry.rear_spar || [];
  if (!x.length) return;

  const margin = { left: 56, right: 24, top: 42, bottom: 26 };
  const plan = {
    x: margin.left,
    y: margin.top,
    w: w - margin.left - margin.right,
    h: h / 2 - margin.top - 22,
  };
  const elev = {
    x: margin.left,
    y: h / 2 + margin.top,
    w: w - margin.left - margin.right,
    h: h / 2 - margin.top - margin.bottom,
  };

  const xMax = geometry.b_half || Math.max(...x);
  const cMax = Math.max(...chord, 1);
  const xToPlan = (value) => plan.x + (value / xMax) * plan.w;
  const yToPlan = (value) => plan.y + (value / cMax) * plan.h;

  ctx.strokeStyle = "#6e7f87";
  ctx.strokeRect(plan.x, plan.y, plan.w, plan.h);
  ctx.strokeRect(elev.x, elev.y, elev.w, elev.h);

  // Planform polygon: leading edge is y=0, trailing edge is chord(x).
  ctx.beginPath();
  ctx.moveTo(xToPlan(x[0]), yToPlan(0));
  for (let i = 1; i < x.length; i++) ctx.lineTo(xToPlan(x[i]), yToPlan(0));
  for (let i = x.length - 1; i >= 0; i--) ctx.lineTo(xToPlan(x[i]), yToPlan(chord[i]));
  ctx.closePath();
  ctx.fillStyle = "rgba(242, 237, 225, 0.10)";
  ctx.fill();
  ctx.strokeStyle = "#f2ede1";
  ctx.stroke();

  if (geometry.dcell_enabled) {
    ctx.beginPath();
    ctx.moveTo(xToPlan(x[0]), yToPlan(0));
    for (let i = 1; i < x.length; i++) ctx.lineTo(xToPlan(x[i]), yToPlan(0));
    for (let i = x.length - 1; i >= 0; i--) ctx.lineTo(xToPlan(x[i]), yToPlan(front[i]));
    ctx.closePath();
    ctx.fillStyle = "rgba(8, 80, 151, 0.25)";
    ctx.fill();
  }

  function drawPlanLine(values, color, label, yLabel) {
    ctx.beginPath();
    values.forEach((value, i) => {
      const px = xToPlan(x[i]);
      const py = yToPlan(value);
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    });
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.fillStyle = color;
    ctx.fillText(label, plan.x + 8, yToPlan(yLabel) - 5);
  }
  drawPlanLine(front, "#085097", `Front ${Math.round(geometry.front_spar_percent * 100)}%`, front[0]);
  drawPlanLine(rear, "#d2b75f", `Rear ${Math.round(geometry.rear_spar_percent * 100)}%`, rear[0]);

  function drawVerticalBL(bl, color, label) {
    if (!Number.isFinite(bl) || bl < 0 || bl > xMax) return;
    const px = xToPlan(bl);
    ctx.beginPath();
    ctx.setLineDash([6, 4]);
    ctx.moveTo(px, plan.y);
    ctx.lineTo(px, plan.y + plan.h);
    ctx.strokeStyle = color;
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = color;
    ctx.fillText(label, px + 4, plan.y + 14);
  }
  drawVerticalBL(geometry.strut_bl, "#d2b75f", `Strut BL ${fmt(geometry.strut_bl, 0)}`);
  if (geometry.jury_enabled) drawVerticalBL(geometry.jury_bl, "#e5c87a", `Jury BL ${fmt(geometry.jury_bl, 0)}`);
  if (geometry.taper_start_bl > 0) drawVerticalBL(geometry.taper_start_bl, "#6e9b5a", `Taper BL ${fmt(geometry.taper_start_bl, 0)}`);

  // Front elevation.
  const rootBl = geometry.root_bl || 0;
  const elevX = (value) => elev.x + (value / xMax) * elev.w;
  const yRange = Math.max(Math.abs(geometry.strut_vert || 0), 20);
  const elevY = (value) => elev.y + elev.h / 2 - (value / (yRange * 1.2)) * elev.h;

  ctx.strokeStyle = "#333333";
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.moveTo(elevX(rootBl), elev.y);
  ctx.lineTo(elevX(rootBl), elev.y + elev.h);
  ctx.stroke();
  ctx.fillStyle = "#b9bcc2";
  ctx.fillText(`FUSE / BL ${fmt(rootBl, 0)}`, elevX(rootBl) + 6, elev.y + 16);

  ctx.strokeStyle = "#085097";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(elevX(rootBl), elevY(0));
  ctx.lineTo(elevX(xMax), elevY(0));
  ctx.stroke();
  ctx.fillStyle = "#085097";
  ctx.fillText("Front spar", elevX(rootBl) + 8, elevY(0) - 8);

  ctx.strokeStyle = "#d2b75f";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(elevX(rootBl), elevY(-2));
  ctx.lineTo(elevX(xMax), elevY(-2));
  ctx.stroke();
  ctx.fillStyle = "#d2b75f";
  ctx.fillText(geometry.config === "single_strut" ? "Rear spar (cantilever)" : "Rear spar", elevX(rootBl) + 8, elevY(-2) + 18);

  if (geometry.config !== "cantilever") {
    const sx = geometry.strut_bl;
    const sxFuse = geometry.strut_fuse_bl;
    const syFuse = -Math.abs(geometry.strut_vert || 0);
    ctx.strokeStyle = "#e5c87a";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(elevX(sxFuse), elevY(syFuse));
    ctx.lineTo(elevX(sx), elevY(0));
    ctx.stroke();
    ctx.fillStyle = "#e5c87a";
    ctx.fillText("Strut", elevX((sx + sxFuse) / 2) + 6, elevY(syFuse / 2));

    if (geometry.jury_enabled && geometry.jury_bl > sxFuse && geometry.jury_bl < sx) {
      const frac = (geometry.jury_bl - sxFuse) / (sx - sxFuse);
      const jy = syFuse + frac * (0 - syFuse);
      ctx.strokeStyle = "#f2ede1";
      ctx.setLineDash([5, 4]);
      ctx.beginPath();
      ctx.moveTo(elevX(geometry.jury_bl), elevY(0));
      ctx.lineTo(elevX(geometry.jury_bl), elevY(jy));
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillText("Jury", elevX(geometry.jury_bl) + 5, elevY(jy) - 4);
    }
  }
}

async function runAnalysis() {
  if (state.isRunning) return;
  const runId = ++state.runId;
  try {
    setRunButtonRunning(true);
    syncInputsFromForm();
    // Let advanced JSON override quick fields when the editor is open/edited.
    loadJsonEditor();
    rememberBetaPassword();
    const started = new Date();
    setStatus(`Running analysis #${runId}...`);
    document.getElementById("summary").textContent = `Running analysis #${runId}...\nStarted ${started.toLocaleTimeString()}`;
    updateCards({
      sigma_max_front: null,
      sigma_max_rear: null,
      spar_weight_total: null,
      z_delta_max: null,
      torsion: {},
    });
    await new Promise((resolve) => requestAnimationFrame(resolve));
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ inputs: state.inputs, betaPassword: betaPassword() }),
    });
    const payload = await response.json();
    if (!payload.ok) throw new Error(`${payload.error}\n${payload.traceback || ""}`);
    if (runId !== state.runId) return;

    const finished = new Date();
    document.getElementById("summary").textContent =
      `Analysis #${runId} complete — ${finished.toLocaleTimeString()}\n\n${payload.summary}`;
    updateCards(payload.metrics);
    renderPlots(payload);
    setStatus(`Analysis #${runId} complete`, "ok");
  } catch (error) {
    document.getElementById("summary").textContent = error.stack || String(error);
    setStatus("Analysis failed", "error");
  } finally {
    if (runId === state.runId) setRunButtonRunning(false);
  }
}

async function downloadReport() {
  try {
    syncInputsFromForm();
    loadJsonEditor();
    rememberBetaPassword();
    setStatus("Generating PDF report...");
    const response = await fetch("/api/report", {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ inputs: state.inputs, betaPassword: betaPassword() }),
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.error || `Report failed with HTTP ${response.status}`);
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "aerobeam-report.pdf";
    link.click();
    URL.revokeObjectURL(url);
    setStatus("PDF report ready", "ok");
  } catch (error) {
    document.getElementById("summary").textContent = error.stack || String(error);
    setStatus("PDF report failed", "error");
  }
}

async function uploadInputs(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  try {
    const text = await file.text();
    const loaded = normalizeLoadedInputs(JSON.parse(text));
    state.inputs = { ...state.defaults, ...loaded };
    ensureSchemaDefaults();
    syncFormFromInputs();
    setStatus(`Loaded ${file.name}`, "ok");
    await runAnalysis();
  } catch (error) {
    document.getElementById("summary").textContent = error.stack || String(error);
    setStatus("Input upload failed", "error");
  } finally {
    event.target.value = "";
  }
}

async function init() {
  const response = await fetch("/api/defaults");
  const payload = await response.json();
  state.defaults = payload.defaults;
  state.inputs = JSON.parse(JSON.stringify(payload.defaults));
  state.options = {
    sparTypes: payload.sparTypes || [],
    materials: payload.materials || [],
    strutMaterials: payload.strutMaterials || [],
  };
  renderMethodStatus(payload.methodStatus || {});
  ensureSchemaDefaults();
  const savedPassword = sessionStorage.getItem("aerobeamBetaPassword") || "";
  if (savedPassword) document.getElementById("betaPassword").value = savedPassword;

  renderInputTabs();
  syncFormFromInputs();
  for (const key of allInputKeys()) {
    const el = document.querySelector(`[data-key="${key}"]`);
    if (el) {
      el.addEventListener("input", markInputsChanged);
      el.addEventListener("change", markInputsChanged);
    }
  }
  document.getElementById("runBtn").addEventListener("click", runAnalysis);
  document.getElementById("reportBtn").addEventListener("click", downloadReport);
  document.getElementById("uploadInput").addEventListener("change", uploadInputs);
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
