const state = {
  runMode: "analyze",
  plan: null,
  parts: [],
  relations: [],
  validation: [],
  featurescript: "",
  logs: [],
  summary: null,
  artifacts: null,
  selectedPartId: null,
  centerTab: "json",
  rightTab: "fs",
};

const examples = {
  cold_die:
    "设计一个冷拉延模具（Cold Drawing Die），只建五个主件。上模座尺寸 200×200×40 mm，" +
    "下模座尺寸 200×200×40 mm。压边圈外径 = 凹模外径 = 160 mm。凹模型腔直径 = 64 mm。" +
    "凸模外径 = 60 mm，高度 80 mm。",
  fixture:
    "设计一个简单夹具，包含底座、圆柱定位柱、导向套和法兰支撑件，要求结构适合演示。",
  flange:
    "设计一个法兰组件，包含矩形底座、中心法兰、空心导向环和锥形定位柱，全部以毫米为单位。",
};

const shapeLabels = {
  box: "Box",
  cylinder: "Cylinder",
  hollow_cylinder: "Hollow Cyl",
  tapered_cylinder: "Tapered Cyl",
  flange: "Flange",
};

const requirementInput = document.querySelector("#requirementInput");
const requirementFile = document.querySelector("#requirementFile");
const planFile = document.querySelector("#planFile");
const planEditor = document.querySelector("#planEditor");
const fsOutput = document.querySelector("#fsOutput");
const persistToggle = document.querySelector("#persistToggle");
const partsStrip = document.querySelector("#partsStrip");
const partDetails = document.querySelector("#partDetails");
const validationList = document.querySelector("#validationList");
const summaryCard = document.querySelector("#summaryCard");
const logList = document.querySelector("#logList");

document.querySelector("#primaryAction").addEventListener("click", () => runCurrentMode());
document.querySelector("#analyzeAction").addEventListener("click", () => runAnalyze());
document.querySelector("#generateAction").addEventListener("click", () => runGenerate());
document.querySelector("#buildAction").addEventListener("click", () => runBuild());
document.querySelector("#copyFsButton").addEventListener("click", copyFeatureScript);
document.querySelector("#downloadFsButton").addEventListener("click", downloadFeatureScript);

document.querySelectorAll("[name=runMode]").forEach((element) => {
  element.addEventListener("change", (event) => {
    state.runMode = event.target.value;
    updateModeCards();
    updatePrimaryButton();
  });
});

document.querySelectorAll("[data-center-tab]").forEach((button) => {
  button.addEventListener("click", () => {
    state.centerTab = button.dataset.centerTab;
    updateTabs("center");
  });
});

document.querySelectorAll("[data-right-tab]").forEach((button) => {
  button.addEventListener("click", () => {
    state.rightTab = button.dataset.rightTab;
    updateTabs("right");
  });
});

document.querySelectorAll("[data-example]").forEach((button) => {
  button.addEventListener("click", () => {
    requirementInput.value = examples[button.dataset.example] ?? "";
  });
});

requirementFile.addEventListener("change", async (event) => {
  const file = event.target.files?.[0];
  if (!file) {
    return;
  }
  requirementInput.value = await file.text();
  pushLog("已从文件载入需求文本。");
});

planFile.addEventListener("change", async (event) => {
  const file = event.target.files?.[0];
  if (!file) {
    return;
  }
  planEditor.value = await file.text();
  state.centerTab = "json";
  updateTabs("center");
  pushLog("已从文件载入 plan JSON。");
});

bootstrap();

async function bootstrap() {
  try {
    const payload = await request("/api/state", { method: "GET" });
    document.querySelector("#apiKeyState").textContent = payload.has_api_key ? "已配置 API Key" : "未配置 API Key";
    document.querySelector("#apiKeyState").classList.toggle("muted", !payload.has_api_key);
    document.querySelector("#modelState").textContent = `Analyze: ${payload.analyze_model}`;
    document.querySelector("#outputDir").textContent = payload.output_dir;
    document.querySelector("#shapeList").innerHTML = payload.supported_shapes
      .map((shape) => `<span>${shape}</span>`)
      .join("");
    pushLog("Web UI 已连接到本地服务。");
  } catch (error) {
    pushLog(`初始化失败：${error.message}`, true);
    alert(error.message);
  }
  updateModeCards();
  updatePrimaryButton();
  updateTabs("center");
  updateTabs("right");
}

async function runCurrentMode() {
  if (state.runMode === "analyze") {
    await runAnalyze();
    return;
  }
  if (state.runMode === "generate") {
    await runGenerate();
    return;
  }
  await runBuild();
}

async function runAnalyze() {
  const requirement = requirementInput.value.trim();
  if (!requirement) {
    alert("请先输入需求文本。");
    return;
  }
  await withBusy("正在分析需求...", async () => {
    const payload = await request("/api/analyze", {
      method: "POST",
      body: {
        requirement,
        persist: persistToggle.checked,
      },
    });
    applyPayload(payload);
    state.centerTab = "json";
    state.rightTab = "summary";
    updateTabs("center");
    updateTabs("right");
  });
}

async function runGenerate() {
  const plan = getPlanFromEditor();
  await withBusy("正在生成 FeatureScript...", async () => {
    const payload = await request("/api/generate", {
      method: "POST",
      body: {
        plan,
        persist: persistToggle.checked,
      },
    });
    applyPayload(payload);
    state.rightTab = "fs";
    updateTabs("right");
  });
}

async function runBuild() {
  const requirement = requirementInput.value.trim();
  if (!requirement) {
    alert("请先输入需求文本。");
    return;
  }
  await withBusy("正在执行全流程构建...", async () => {
    const payload = await request("/api/build", {
      method: "POST",
      body: {
        requirement,
        persist: persistToggle.checked,
      },
    });
    applyPayload(payload);
    state.rightTab = "fs";
    updateTabs("right");
  });
}

function applyPayload(payload) {
  state.plan = payload.plan;
  state.parts = payload.parts;
  state.relations = payload.relations;
  state.validation = payload.validation;
  state.featurescript = payload.featurescript;
  state.logs = payload.logs ?? [];
  state.summary = payload.summary;
  state.artifacts = payload.artifacts;
  state.selectedPartId = payload.parts[0]?.id ?? null;

  planEditor.value = JSON.stringify(payload.plan, null, 2);
  fsOutput.value = payload.featurescript || "";
  renderStatus();
  renderParts();
  renderSelectedPart();
  renderValidation();
  renderSummary();
  renderLogs();
}

function renderStatus() {
  document.querySelector("#summaryState").textContent =
    state.summary?.description || "等待输入需求";
  document.querySelector("#partCount").textContent = String(state.summary?.part_count ?? 0);
  document.querySelector("#relationCount").textContent = String(state.summary?.relation_count ?? 0);
}

function renderParts() {
  if (!state.parts.length) {
    partsStrip.innerHTML = '<div class="detail-empty">Analyze 后会在这里显示零件导航。</div>';
    return;
  }
  partsStrip.innerHTML = state.parts
    .map((part) => {
      const active = part.id === state.selectedPartId ? "active" : "";
      const errorClass = part.status === "error" ? "error" : "";
      return `
        <button class="part-card ${active} ${errorClass}" data-part-id="${part.id}">
          <header>
            <div>
              <h3>${escapeHtml(part.name)}</h3>
              <small>${escapeHtml(shapeLabels[part.shape] || part.shape)}</small>
            </div>
            <small>${escapeHtml(part.id)}</small>
          </header>
          <div class="part-meta">
            <span class="part-tag">${escapeHtml(part.material_hint)}</span>
            <strong>${part.status === "error" ? "有错误" : "稳定"}</strong>
          </div>
        </button>
      `;
    })
    .join("");
  partsStrip.querySelectorAll("[data-part-id]").forEach((element) => {
    element.addEventListener("click", () => {
      state.selectedPartId = element.dataset.partId;
      renderParts();
      renderSelectedPart();
    });
  });
}

function renderSelectedPart() {
  const part = state.parts.find((item) => item.id === state.selectedPartId);
  if (!part) {
    partDetails.innerHTML = '<div class="detail-empty">尚未选择零件。</div>';
    return;
  }

  const params = Object.entries(part.params)
    .map(
      ([key, value]) => `
        <div class="detail-block">
          <strong>${escapeHtml(key)}</strong>
          <code>${Number(value).toFixed(2)} mm</code>
        </div>
      `,
    )
    .join("");
  const relations = state.relations
    .filter((item) => item.child_id === part.id || item.parent_id === part.id)
    .map(
      (item) => `
        <div class="relation-row">
          <strong>${escapeHtml(item.child_id)}</strong>
          <span> ${escapeHtml(item.relation)} </span>
          <strong>${escapeHtml(item.parent_id)}</strong>
        </div>
      `,
    )
    .join("");

  partDetails.innerHTML = `
    <div class="detail-card">
      <h3>${escapeHtml(part.name)}</h3>
      <p>${escapeHtml(part.description)}</p>
      <div class="detail-grid">
        <div class="detail-block">
          <strong>Shape</strong>
          <span>${escapeHtml(shapeLabels[part.shape] || part.shape)}</span>
        </div>
        <div class="detail-block">
          <strong>Material</strong>
          <span>${escapeHtml(part.material_hint)}</span>
        </div>
        <div class="detail-block">
          <strong>Status</strong>
          <span>${part.status === "error" ? "生成失败" : "正常"}</span>
        </div>
      </div>
      <div class="detail-grid">
        ${params}
      </div>
      <div class="detail-grid">
        <div class="detail-block">
          <strong>X</strong>
          <code>${Number(part.position.x_mm).toFixed(2)} mm</code>
        </div>
        <div class="detail-block">
          <strong>Y</strong>
          <code>${Number(part.position.y_mm).toFixed(2)} mm</code>
        </div>
        <div class="detail-block">
          <strong>Z Bottom</strong>
          <code>${Number(part.position.z_bottom_mm).toFixed(2)} mm</code>
        </div>
      </div>
      <div class="detail-list">
        ${relations || '<div class="detail-empty">该零件暂无装配关系。</div>'}
      </div>
    </div>
  `;
}

function renderValidation() {
  validationList.innerHTML = state.validation
    .map(
      (item) => `
        <div class="validation-card ${item.level === "error" ? "error" : "success"}">
          <strong>${escapeHtml(item.title)}</strong>
          <p>${escapeHtml(item.message)}</p>
        </div>
      `,
    )
    .join("");
}

function renderSummary() {
  if (!state.summary) {
    summaryCard.innerHTML = "<h3>等待结果</h3><p>执行后会展示装配摘要、输出路径和生成统计。</p>";
    return;
  }
  summaryCard.innerHTML = `
    <h3>${escapeHtml(state.summary.assembly_name)}</h3>
    <p>${escapeHtml(state.summary.description)}</p>
    <div class="summary-grid">
      <div class="summary-stat">
        <strong>Part Count</strong>
        <span>${state.summary.part_count}</span>
      </div>
      <div class="summary-stat">
        <strong>Relations</strong>
        <span>${state.summary.relation_count}</span>
      </div>
      <div class="summary-stat">
        <strong>Failed Parts</strong>
        <span>${state.summary.failed_parts ?? 0}</span>
      </div>
      <div class="summary-stat">
        <strong>Generator</strong>
        <span>${escapeHtml(state.summary.generator ?? "analyze-only")}</span>
      </div>
    </div>
    <div class="detail-list">
      <div class="relation-row"><strong>Plan Path</strong><div>${escapeHtml(state.artifacts?.plan_path || "未落盘")}</div></div>
      <div class="relation-row"><strong>FS Path</strong><div>${escapeHtml(state.artifacts?.featurescript_path || "未落盘")}</div></div>
    </div>
  `;
}

function renderLogs() {
  const items = [...state.logs];
  if (!items.length) {
    items.push({ time: "--:--:--", message: "服务已启动，等待操作。" });
  }
  logList.innerHTML = items
    .map(
      (item) => `
        <div class="log-item">
          <time>${escapeHtml(formatTime(item.time))}</time>
          <span>${escapeHtml(item.message)}</span>
        </div>
      `,
    )
    .join("");
}

function updateModeCards() {
  document.querySelectorAll(".mode-card").forEach((card) => {
    card.classList.toggle("active", card.dataset.mode === state.runMode);
  });
}

function updatePrimaryButton() {
  const labels = {
    analyze: "执行需求分析",
    generate: "生成 FeatureScript",
    build: "执行全流程构建",
  };
  document.querySelector("#primaryAction").textContent = labels[state.runMode];
}

function updateTabs(side) {
  const activeKey = side === "center" ? state.centerTab : state.rightTab;
  document.querySelectorAll(`[data-${side}-tab]`).forEach((button) => {
    button.classList.toggle("active", button.dataset[`${side}Tab`] === activeKey);
  });
  document.querySelectorAll(`[data-${side}-view]`).forEach((view) => {
    view.classList.toggle("active", view.dataset[`${side}View`] === activeKey);
  });
}

function getPlanFromEditor() {
  const raw = planEditor.value.trim();
  if (!raw) {
    throw new Error("请先提供 plan JSON。");
  }
  try {
    return JSON.parse(raw);
  } catch (error) {
    throw new Error(`plan JSON 解析失败：${error.message}`);
  }
}

async function request(url, options) {
  const response = await fetch(url, {
    method: options.method,
    headers: {
      "Content-Type": "application/json",
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "请求失败");
  }
  return payload;
}

async function withBusy(message, task) {
  pushLog(message);
  document.querySelector("#summaryState").textContent = message;
  try {
    await task();
  } catch (error) {
    pushLog(error.message, true);
    alert(error.message);
  }
}

function pushLog(message) {
  state.logs = [
    { time: new Date().toISOString(), message },
    ...state.logs,
  ].slice(0, 12);
  renderLogs();
}

async function copyFeatureScript() {
  if (!fsOutput.value) {
    alert("当前没有可复制的 FeatureScript。");
    return;
  }
  await navigator.clipboard.writeText(fsOutput.value);
  pushLog("已复制 FeatureScript 到剪贴板。");
}

function downloadFeatureScript() {
  if (!fsOutput.value) {
    alert("当前没有可下载的 FeatureScript。");
    return;
  }
  const filename = `${state.summary?.assembly_name || "generated"}.fs`;
  downloadText(filename, fsOutput.value);
  pushLog(`已下载 ${filename}。`);
}

function downloadText(filename, content) {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function formatTime(value) {
  if (!value || value === "--:--:--") {
    return value;
  }
  return new Date(value).toLocaleTimeString("zh-CN", {
    hour12: false,
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
