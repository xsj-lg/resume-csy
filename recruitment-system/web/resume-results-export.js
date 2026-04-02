const FILTER_STORAGE_KEY = "rs_resume_results_export_filters_v001";

const STAGE_ORDER = [
  { key: "初筛", elementId: "resume-export-stage-screening" },
  { key: "一面", elementId: "resume-export-stage-first" },
  { key: "二面", elementId: "resume-export-stage-second" },
  { key: "HR面", elementId: "resume-export-stage-hr" },
];

const state = {
  me: null,
  filters: loadFilters(),
};

const els = {
  currentUser: document.getElementById("resume-export-current-user"),
  dateFrom: document.getElementById("resume-export-date-from"),
  dateTo: document.getElementById("resume-export-date-to"),
  searchBtn: document.getElementById("resume-export-search-btn"),
  resetBtn: document.getElementById("resume-export-reset-btn"),
  downloadBtn: document.getElementById("resume-export-download-btn"),
  logoutBtn: document.getElementById("resume-export-logout-btn"),
  message: document.getElementById("resume-export-message"),
  totalCount: document.getElementById("resume-export-total-count"),
  finishedCount: document.getElementById("resume-export-finished-count"),
  passedCount: document.getElementById("resume-export-passed-count"),
  failedCount: document.getElementById("resume-export-failed-count"),
  stageProgressList: document.getElementById("resume-export-stage-progress-list"),
};

for (const stage of STAGE_ORDER) {
  els[stage.elementId] = document.getElementById(stage.elementId);
}

function loadFilters() {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(FILTER_STORAGE_KEY) || "{}");
    return {
      uploaded_from: String(parsed.uploaded_from || ""),
      uploaded_to: String(parsed.uploaded_to || ""),
    };
  } catch {
    return {
      uploaded_from: "",
      uploaded_to: "",
    };
  }
}

function persistFilters() {
  window.localStorage.setItem(FILTER_STORAGE_KEY, JSON.stringify(state.filters));
}

function roleCodeFromUser(user) {
  const role = String((user && user.role_code) || "").trim().toLowerCase();
  if (role) {
    return role;
  }
  return Number((user && user.is_admin) || 0) === 1 ? "administrator" : "hr_specialist";
}

function canExportResumeResults(user) {
  const roleCode = roleCodeFromUser(user);
  return roleCode === "administrator" || roleCode === "personnel_manager";
}

function redirectToLogin(forceChangePassword = false) {
  const suffix = forceChangePassword ? "?force=1" : "";
  window.location.href = `/login${suffix}`;
}

function setMessage(text, kind = "") {
  els.message.textContent = text;
  els.message.className = "form-message";
  if (kind) {
    els.message.classList.add(kind);
  }
}

async function fetchJSON(url, options = {}) {
  const resp = await fetch(url, options);
  let data = {};
  try {
    data = await resp.json();
  } catch {
    data = {};
  }
  if (!resp.ok) {
    const error = new Error(data.error || "请求失败");
    error.status = resp.status;
    error.code = data.error || "";
    throw error;
  }
  return data;
}

function renderCurrentUser() {
  if (!state.me) {
    els.currentUser.textContent = "未登录";
    return;
  }
  els.currentUser.textContent = `当前用户：${state.me.display_name} (@${state.me.username})`;
}

function syncFiltersToInputs() {
  els.dateFrom.value = state.filters.uploaded_from || "";
  els.dateTo.value = state.filters.uploaded_to || "";
}

function readFiltersFromInputs() {
  state.filters.uploaded_from = String(els.dateFrom.value || "").trim();
  state.filters.uploaded_to = String(els.dateTo.value || "").trim();
  persistFilters();
}

function buildQueryString() {
  const params = new URLSearchParams();
  if (state.filters.uploaded_from) {
    params.set("uploaded_from", state.filters.uploaded_from);
  }
  if (state.filters.uploaded_to) {
    params.set("uploaded_to", state.filters.uploaded_to);
  }
  const text = params.toString();
  return text ? `?${text}` : "";
}

function buildStageMetricMarkup(value, label) {
  return `
    <div>
      <div class="operations-stat-meta">${label}</div>
      <div class="operations-stat-value">${value}</div>
    </div>
  `;
}

function buildStageProgressMarkup(stageName, stageStats) {
  const interviewCount = Number(stageStats.interview_count || 0);
  const currentCount = Number(stageStats.current_count || 0);
  const passedCount = Number(stageStats.passed_count || 0);
  const failedCount = Number(stageStats.failed_count || 0);
  return `
    <article class="resume-export-stage-item">
      <div class="operations-stat-label">${stageName}</div>
      <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:10px;">
        ${buildStageMetricMarkup(interviewCount, `面试${stageName}简历个数`)}
        ${buildStageMetricMarkup(currentCount, `当前处于${stageName}简历个数`)}
        ${buildStageMetricMarkup(passedCount, `通过${stageName}简历个数`)}
        ${buildStageMetricMarkup(failedCount, `未通过${stageName}简历个数`)}
      </div>
    </article>
  `;
}

function renderStageProgress(data) {
  const stageProgressCounts = data.stage_progress_counts || {};
  els.stageProgressList.innerHTML = STAGE_ORDER.map((stage) =>
    buildStageProgressMarkup(stage.key, stageProgressCounts[stage.key] || {}),
  ).join("");
}

function renderSummary(data) {
  const stageCounts = data.stage_counts || {};
  els.totalCount.textContent = String(data.total_count || 0);
  els.finishedCount.textContent = String(data.finished_count || 0);
  els.passedCount.textContent = String(data.passed_count || 0);
  els.failedCount.textContent = String(data.failed_count || 0);
  for (const stage of STAGE_ORDER) {
    els[stage.elementId].textContent = String(stageCounts[stage.key] || 0);
  }
  renderStageProgress(data);
}

async function ensureAuthenticated() {
  try {
    const data = await fetchJSON("/api/auth/me");
    state.me = data.item || null;
    if (!state.me) {
      redirectToLogin(false);
      return false;
    }
    if (Number(state.me.must_change_password || 0) === 1) {
      redirectToLogin(true);
      return false;
    }
    if (!canExportResumeResults(state.me)) {
      window.location.href = "/";
      return false;
    }
    renderCurrentUser();
    return true;
  } catch (err) {
    if (err.status === 401) {
      redirectToLogin(false);
      return false;
    }
    setMessage(err.message || "登录状态校验失败", "error");
    return false;
  }
}

async function loadSummary() {
  readFiltersFromInputs();
  setMessage("正在加载统计...");
  try {
    const data = await fetchJSON(`/api/resume-results/summary${buildQueryString()}`);
    renderSummary(data);
    setMessage("统计已更新", "success");
  } catch (err) {
    setMessage(err.message || "统计加载失败", "error");
  }
}

function downloadExport() {
  readFiltersFromInputs();
  window.location.href = `/api/resume-results/export${buildQueryString()}`;
}

function resetFilters() {
  state.filters.uploaded_from = "";
  state.filters.uploaded_to = "";
  persistFilters();
  syncFiltersToInputs();
  void loadSummary();
}

async function logout() {
  try {
    await fetchJSON("/api/auth/logout", { method: "POST" });
  } finally {
    redirectToLogin(false);
  }
}

async function bootstrap() {
  syncFiltersToInputs();
  const authed = await ensureAuthenticated();
  if (!authed) {
    return;
  }
  await loadSummary();
}

els.searchBtn.addEventListener("click", () => {
  void loadSummary();
});
els.resetBtn.addEventListener("click", resetFilters);
els.downloadBtn.addEventListener("click", downloadExport);
els.logoutBtn.addEventListener("click", logout);

bootstrap();
