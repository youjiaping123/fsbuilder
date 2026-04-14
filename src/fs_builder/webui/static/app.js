const state = {
  runMode: "analyze",
  isBusy: false,
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
  rightTab: "summary",
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
  box: "长方体",
  cylinder: "圆柱体",
  hollow_cylinder: "空心圆柱",
  tapered_cylinder: "锥形圆柱",
  flange: "法兰",
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
const primaryAction = document.querySelector("#primaryAction");
const actionTip = document.querySelector("#actionTip");
const copyFsButton = document.querySelector("#copyFsButton");
const downloadFsButton = document.querySelector("#downloadFsButton");

primaryAction.addEventListener("click", () => runCurrentMode());
copyFsButton.addEventListener("click", copyFeatureScript);
downloadFsButton.addEventListener("click", downloadFeatureScript);

document.querySelectorAll("[name=runMode]").forEach((element) => {
  element.addEventListener("change", (event) => {
    state.runMode = event.target.value;
    updateModeCards();
    updatePrimaryButton();
    syncControls();
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
    syncControls();
  });
});

requirementInput.addEventListener("input", syncControls);
planEditor.addEventListener("input", syncControls);

requirementFile.addEventListener("change", async (event) => {
  const file = event.target.files?.[0];
  if (!file) {
    return;
  }
  requirementInput.value = await file.text();
  pushLog("已从文件载入需求文本。");
  syncControls();
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
  syncControls();
});

bootstrap();

async function bootstrap() {
  try {
    const payload = await request("/api/state", { method: "GET" });
    document.querySelector("#apiKeyState").textContent = payload.has_api_key
      ? "已配置 API Key"
      : "未配置 API Key";
    document.querySelector("#apiKeyState").classList.toggle("muted", !payload.has_api_key);
    document.querySelector("#modelState").textContent = `分析模型：${payload.analyze_model}`;
    document.querySelector("#outputDir").textContent = payload.output_dir;
    document.querySelector("#shapeList").innerHTML = payload.supported_shapes
      .map((shape) => `<span>${escapeHtml(shapeLabels[shape] || shape)}</span>`)
      .join("");
    pushLog("Web UI 已连接到本地服务。");
  } catch (error) {
    pushLog(`初始化失败：${error.message}`);
    alert(error.message);
  }
  updateModeCards();
  updatePrimaryButton();
  updateTabs("center");
  updateTabs("right");
  syncControls();
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
  const normalizedPlan = payload.plan ?? null;
  const normalizedRelations = normalizedPlan?.assembly_relations ?? payload.relations ?? [];
  const normalizedSummary = {
    ...(payload.summary ?? {}),
    assembly_name: normalizedPlan?.assembly_name ?? payload.summary?.assembly_name ?? "未命名装配",
    description: normalizedPlan?.description ?? payload.summary?.description ?? "暂无摘要",
    part_count: normalizedPlan?.parts?.length ?? payload.summary?.part_count ?? 0,
    relation_count:
      normalizedPlan?.assembly_relations?.length ?? payload.summary?.relation_count ?? 0,
  };

  state.plan = normalizedPlan;
  state.parts = payload.parts ?? [];
  state.relations = normalizedRelations;
  state.validation = payload.validation ?? [];
  state.featurescript = payload.featurescript ?? "";
  state.logs = payload.logs ?? [];
  state.summary = normalizedSummary;
  state.artifacts = payload.artifacts ?? {};
  if (!state.parts.some((part) => part.id === state.selectedPartId)) {
    state.selectedPartId = state.parts[0]?.id ?? null;
  }

  planEditor.value = normalizedPlan ? JSON.stringify(normalizedPlan, null, 2) : "";
  fsOutput.value = state.featurescript;
  renderStatus();
  renderParts();
  renderSelectedPart();
  renderValidation();
  renderSummary();
  renderLogs();
  syncControls();
}

function renderStatus() {
  document.querySelector("#summaryState").textContent =
    state.summary?.description || "等待输入需求";
  document.querySelector("#partCount").textContent = String(state.summary?.part_count ?? 0);
  document.querySelector("#relationCount").textContent = String(state.summary?.relation_count ?? 0);
}

function renderParts() {
  if (!state.parts.length) {
    partsStrip.innerHTML = '<div class="detail-empty">分析完成后会在这里显示零件导航。</div>';
    return;
  }
  partsStrip.innerHTML = state.parts
    .map((part) => {
      const active = part.id === state.selectedPartId ? "active" : "";
      const errorClass = part.status === "error" ? "error" : "";
      const disabled = state.isBusy ? "disabled" : "";
      return `
        <button class="part-card ${active} ${errorClass}" data-part-id="${part.id}" ${disabled}>
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
          <span class="relation-label">子件：${escapeHtml(item.child_id)}</span>
          <span class="relation-label">关系：${escapeHtml(item.relation)}</span>
          <span class="relation-label">父件：${escapeHtml(item.parent_id)}</span>
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
          <strong>形状</strong>
          <span>${escapeHtml(shapeLabels[part.shape] || part.shape)}</span>
        </div>
        <div class="detail-block">
          <strong>材料</strong>
          <span>${escapeHtml(part.material_hint)}</span>
        </div>
        <div class="detail-block">
          <strong>状态</strong>
          <span>${part.status === "error" ? "生成失败" : "正常"}</span>
        </div>
      </div>
      <div class="detail-grid">
        ${params}
      </div>
      <div class="detail-grid">
        <div class="detail-block">
          <strong>X 坐标</strong>
          <code>${Number(part.position.x_mm).toFixed(2)} mm</code>
        </div>
        <div class="detail-block">
          <strong>Y 坐标</strong>
          <code>${Number(part.position.y_mm).toFixed(2)} mm</code>
        </div>
        <div class="detail-block">
          <strong>Z 底面</strong>
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
        <strong>零件数量</strong>
        <span>${state.summary.part_count}</span>
      </div>
      <div class="summary-stat">
        <strong>装配关系</strong>
        <span>${state.summary.relation_count}</span>
      </div>
      <div class="summary-stat">
        <strong>失败零件</strong>
        <span>${state.summary.failed_parts ?? 0}</span>
      </div>
      <div class="summary-stat">
        <strong>生成方式</strong>
        <span>${escapeHtml(localizeGeneratorName(state.summary.generator))}</span>
      </div>
    </div>
    <div class="detail-list">
      <div class="relation-row summary-path"><strong>Plan 文件</strong><div>${escapeHtml(state.artifacts?.plan_path || "未落盘")}</div></div>
      <div class="relation-row summary-path"><strong>脚本文件</strong><div>${escapeHtml(state.artifacts?.featurescript_path || "未落盘")}</div></div>
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
  const tips = {
    analyze: "读取左侧需求文本，生成并校验结构化 plan。",
    generate: "基于中间区域的 plan JSON，生成右侧脚本输出。",
    build: "从需求到脚本一次跑完整条链路，适合现场演示。",
  };
  primaryAction.textContent = state.isBusy ? "处理中..." : labels[state.runMode];
  actionTip.textContent = tips[state.runMode];
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
  state.isBusy = true;
  pushLog(message);
  document.querySelector("#summaryState").textContent = message;
  syncControls();
  try {
    await task();
  } catch (error) {
    pushLog(error.message);
    alert(error.message);
  } finally {
    state.isBusy = false;
    syncControls();
    renderStatus();
    renderParts();
  }
}

function pushLog(message) {
  state.logs = [{ time: new Date().toISOString(), message }, ...state.logs].slice(0, 12);
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

function syncControls() {
  const hasRequirement = Boolean(requirementInput.value.trim());
  const hasPlan = Boolean(planEditor.value.trim());
  const hasFeatureScript = Boolean(fsOutput.value.trim());

  let primaryDisabled = state.isBusy;
  if (state.runMode === "analyze" || state.runMode === "build") {
    primaryDisabled = primaryDisabled || !hasRequirement;
  }
  if (state.runMode === "generate") {
    primaryDisabled = primaryDisabled || !hasPlan;
  }

  primaryAction.disabled = primaryDisabled;
  copyFsButton.disabled = state.isBusy || !hasFeatureScript;
  downloadFsButton.disabled = state.isBusy || !hasFeatureScript;

  requirementInput.disabled = state.isBusy;
  planEditor.disabled = state.isBusy;
  persistToggle.disabled = state.isBusy;
  requirementFile.disabled = state.isBusy;
  planFile.disabled = state.isBusy;

  document.querySelectorAll("[name=runMode]").forEach((element) => {
    element.disabled = state.isBusy;
  });
  document.querySelectorAll("[data-example]").forEach((button) => {
    button.disabled = state.isBusy;
  });
  document.querySelectorAll("[data-center-tab], [data-right-tab]").forEach((button) => {
    button.disabled = state.isBusy;
  });
  document.querySelectorAll(".file-button").forEach((element) => {
    element.classList.toggle("disabled", state.isBusy);
  });

  updatePrimaryButton();
}

function localizeGeneratorName(value) {
  if (!value) {
    return "仅分析";
  }
  if (value === "template") {
    return "模板生成";
  }
  return value;
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
