const DEPARTMENT_SCOPES = ["销售部", "研发部", "算法部", "项目部", "人事部"];
const INTERVIEW_STAGES = ["初筛", "一面", "二面", "HR面"];
const JOB_STORAGE_KEY = "rs_jobs_v012";
const FILTER_STORAGE_KEY = "rs_jobs_filters_v012";
const MAX_TEMPLATE_FILE_BYTES = 8 * 1024 * 1024;
const JOBS_API_URL = "/api/jobs";

const state = {
  me: null,
  users: [],
  jobs: [],
  activeJobId: "",
  draftJob: null,
  filters: loadFilters(),
};

let jobsSyncInFlight = false;
let jobsSyncPending = false;

const els = {
  currentUser: document.getElementById("jobs-current-user"),
  operationsLink: document.getElementById("jobs-operations-link"),
  logoutBtn: document.getElementById("jobs-logout-btn"),
  filterKeyword: document.getElementById("job-filter-keyword"),
  filterStatus: document.getElementById("job-filter-status"),
  filterDepartment: document.getElementById("job-filter-department"),
  filterResetBtn: document.getElementById("job-filter-reset-btn"),
  newBtn: document.getElementById("job-new-btn"),
  jobList: document.getElementById("job-list"),
  formTitle: document.getElementById("job-form-title"),
  statusBadge: document.getElementById("job-status-badge"),
  form: document.getElementById("job-form"),
  title: document.getElementById("job-title"),
  department: document.getElementById("job-department"),
  headcount: document.getElementById("job-headcount"),
  location: document.getElementById("job-location"),
  recruiter: document.getElementById("job-recruiter"),
  hiringManager: document.getElementById("job-hiring-manager"),
  jd: document.getElementById("job-jd"),
  requirements: document.getElementById("job-requirements"),
  processScreening: document.getElementById("process-screening"),
  processFirst: document.getElementById("process-first"),
  processSecond: document.getElementById("process-second"),
  processHr: document.getElementById("process-hr"),
  criteriaEducation: document.getElementById("criteria-education"),
  criteriaMajor: document.getElementById("criteria-major"),
  criteriaSkills: document.getElementById("criteria-skills"),
  criteriaProject: document.getElementById("criteria-project"),
  templateFile: document.getElementById("template-file"),
  templateUploadBtn: document.getElementById("template-upload-btn"),
  templateMessage: document.getElementById("template-message"),
  templatePreview: document.getElementById("template-preview"),
  activeTemplateText: document.getElementById("active-template-text"),
  templateVersionList: document.getElementById("template-version-list"),
  autoScoreEnabled: document.getElementById("auto-score-enabled"),
  saveBtn: document.getElementById("job-save-btn"),
  closeBtn: document.getElementById("job-close-btn"),
  copyBtn: document.getElementById("job-copy-btn"),
  triggerScoreBtn: document.getElementById("trigger-score-btn"),
  message: document.getElementById("job-message"),
  logList: document.getElementById("job-log-list"),
};

function loadFilters() {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(FILTER_STORAGE_KEY) || "{}");
    return {
      keyword: String(parsed.keyword || ""),
      status: String(parsed.status || ""),
      department: String(parsed.department || ""),
    };
  } catch {
    return { keyword: "", status: "", department: "" };
  }
}

function persistFilters() {
  window.localStorage.setItem(FILTER_STORAGE_KEY, JSON.stringify(state.filters));
}

function deepCopy(value) {
  return JSON.parse(JSON.stringify(value));
}

function nowIso() {
  return new Date().toISOString();
}

function formatTime(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleString("zh-CN", { hour12: false });
}

function formatFileSize(bytes) {
  const value = Number(bytes || 0);
  if (!Number.isFinite(value) || value <= 0) {
    return "-";
  }
  if (value < 1024) {
    return `${value} B`;
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }
  return `${(value / (1024 * 1024)).toFixed(2)} MB`;
}

function uid(prefix = "id") {
  if (window.crypto && window.crypto.randomUUID) {
    return `${prefix}_${window.crypto.randomUUID().replace(/-/g, "")}`;
  }
  return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2, 10)}`;
}

function generateJobCode() {
  const now = new Date();
  const dateTag = [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, "0"),
    String(now.getDate()).padStart(2, "0"),
  ].join("");
  return `JOB-${dateTag}-${Math.floor(Math.random() * 900 + 100)}`;
}

function roleCodeFromUser(user) {
  const role = String((user && user.role_code) || "").trim().toLowerCase();
  if (role) {
    return role;
  }
  return Number((user && user.is_admin) || 0) === 1 ? "administrator" : "hr_specialist";
}

function canAccessJobPage(user) {
  const roleCode = roleCodeFromUser(user);
  return roleCode === "administrator" || roleCode === "hr_specialist" || roleCode === "hiring_manager";
}

function normalizeDepartment(value) {
  const text = String(value || "").trim();
  return DEPARTMENT_SCOPES.includes(text) ? text : "";
}

function jobStatusText(status) {
  return status === "closed" ? "已关闭" : "招聘中";
}

function setMessage(text, kind = "") {
  els.message.textContent = text;
  els.message.className = "form-message";
  if (kind) {
    els.message.classList.add(kind);
  }
}

function setTemplateMessage(text, kind = "") {
  els.templateMessage.textContent = text;
  els.templateMessage.className = "form-message";
  if (kind) {
    els.templateMessage.classList.add(kind);
  }
}

function redirectToLogin(forceChangePassword = false) {
  const suffix = forceChangePassword ? "?force=1" : "";
  window.location.href = `/login${suffix}`;
}

async function fetchJSON(url, options = {}) {
  const req = { ...options };
  if (req.body && !(req.body instanceof FormData)) {
    req.headers = { "Content-Type": "application/json", ...(req.headers || {}) };
  }
  const resp = await fetch(url, req);
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

function defaultProcess() {
  return {
    初筛: "",
    一面: "",
    二面: "",
    HR面: "",
  };
}

function defaultCriteria() {
  return {
    education: "",
    major: "",
    skills: "",
    project_experience: "",
  };
}

function blankJobDraft() {
  return {
    job_id: "",
    job_code: "",
    title: "",
    department: "",
    headcount: 1,
    location: "",
    recruiter_user_id: "",
    hiring_manager_user_id: "",
    jd: "",
    requirements: "",
    process: defaultProcess(),
    criteria: defaultCriteria(),
    templates: [],
    active_template_version: 0,
    auto_score_enabled: false,
    status: "open",
    created_at: "",
    updated_at: "",
    closed_at: "",
    logs: [],
  };
}

function normalizeJobItem(item) {
  return {
    ...blankJobDraft(),
    ...(item || {}),
    process: { ...defaultProcess(), ...((item && item.process) || {}) },
    criteria: { ...defaultCriteria(), ...((item && item.criteria) || {}) },
    templates: Array.isArray(item && item.templates) ? item.templates : [],
    logs: Array.isArray(item && item.logs) ? item.logs : [],
  };
}

function loadJobs() {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(JOB_STORAGE_KEY) || "[]");
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.map((item) => normalizeJobItem(item));
  } catch {
    return [];
  }
}

function persistJobs() {
  window.localStorage.setItem(JOB_STORAGE_KEY, JSON.stringify(state.jobs));
  scheduleJobsSync();
}

function replaceJobsLocally(items) {
  state.jobs = Array.isArray(items) ? items.map((item) => normalizeJobItem(item)) : [];
  window.localStorage.setItem(JOB_STORAGE_KEY, JSON.stringify(state.jobs));
}

function applySavedJobFromServer(saved) {
  state.draftJob = deepCopy(saved);
  state.activeJobId = saved.job_id;
  const index = state.jobs.findIndex((item) => item.job_id === saved.job_id);
  if (index >= 0) {
    state.jobs[index] = deepCopy(saved);
  } else {
    state.jobs.push(deepCopy(saved));
  }
  window.localStorage.setItem(JOB_STORAGE_KEY, JSON.stringify(state.jobs));
  renderTemplateSection();
  renderLogs();
  renderJobList();
}

async function fetchJobsFromServer() {
  const data = await fetchJSON(JOBS_API_URL);
  const items = Array.isArray(data.items) ? data.items : [];
  return items.map((item) => normalizeJobItem(item));
}

async function pushJobsToServer() {
  if (jobsSyncInFlight) {
    jobsSyncPending = true;
    return;
  }
  jobsSyncInFlight = true;
  try {
    const data = await fetchJSON(`${JOBS_API_URL}/bulk`, {
      method: "PUT",
      body: JSON.stringify({ items: state.jobs }),
    });
    if (Array.isArray(data.items)) {
      replaceJobsLocally(data.items);
      if (state.activeJobId) {
        const refreshed = state.jobs.find((item) => item.job_id === state.activeJobId);
        if (refreshed) {
          state.draftJob = deepCopy(refreshed);
        }
      }
    }
  } catch (err) {
    setMessage(`岗位同步失败：${err.message || "请求失败"}`, "error");
  } finally {
    jobsSyncInFlight = false;
    if (jobsSyncPending) {
      jobsSyncPending = false;
      void pushJobsToServer();
    }
  }
}

function scheduleJobsSync() {
  void pushJobsToServer();
}

function compareJobsByUpdateDesc(a, b) {
  const aTime = Date.parse(a.updated_at || a.created_at || "");
  const bTime = Date.parse(b.updated_at || b.created_at || "");
  if (Number.isNaN(aTime) && Number.isNaN(bTime)) {
    return String(a.title || "").localeCompare(String(b.title || ""), "zh-CN");
  }
  if (Number.isNaN(aTime)) {
    return 1;
  }
  if (Number.isNaN(bTime)) {
    return -1;
  }
  return bTime - aTime;
}

function filteredJobs() {
  const keyword = String(state.filters.keyword || "").trim().toLowerCase();
  const status = String(state.filters.status || "").trim();
  const department = normalizeDepartment(state.filters.department);
  return [...state.jobs]
    .filter((job) => {
      if (status && job.status !== status) {
        return false;
      }
      if (department && job.department !== department) {
        return false;
      }
      if (!keyword) {
        return true;
      }
      const text = [job.title, job.job_code, job.location, job.department, job.jd, job.requirements]
        .join(" ")
        .toLowerCase();
      return text.includes(keyword);
    })
    .sort(compareJobsByUpdateDesc);
}

function appendJobLog(job, action, detail) {
  job.logs = Array.isArray(job.logs) ? job.logs : [];
  job.logs.push({
    log_id: uid("log"),
    at: nowIso(),
    action,
    operator: (state.me && (state.me.display_name || state.me.username)) || "未知用户",
    detail: detail || "",
  });
  job.logs = job.logs.slice(-200);
}

function roleLabelForOption(item) {
  const role = roleCodeFromUser(item);
  if (role === "administrator") {
    return "管理员";
  }
  if (role === "hr_specialist") {
    return "HR / 招聘专员";
  }
  if (role === "hiring_manager") {
    return "部门负责人 / 用人经理";
  }
  if (role === "interviewer") {
    return "面试官";
  }
  return "用户";
}

function renderUserSelectOptions() {
  const recruiterCandidates = state.users.filter((item) => {
    const role = roleCodeFromUser(item);
    return role === "administrator" || role === "hr_specialist";
  });
  const managerCandidatesByRole = state.users.filter((item) => {
    const role = roleCodeFromUser(item);
    return role === "administrator" || role === "hiring_manager";
  });
  // 无部门负责人账号时回退到全部激活用户，避免下拉不可选。
  const managerCandidates = managerCandidatesByRole.length > 0 ? managerCandidatesByRole : state.users;

  const recruiterValue = els.recruiter.value;
  const managerValue = els.hiringManager.value;

  els.recruiter.innerHTML = ['<option value="">请选择</option>']
    .concat(
      recruiterCandidates.map(
        (item) =>
          `<option value="${item.id}">${item.display_name || item.username}（${roleLabelForOption(item)}）</option>`,
      ),
    )
    .join("");
  els.hiringManager.innerHTML = ['<option value="">不设置</option>']
    .concat(
      managerCandidates.map(
        (item) =>
          `<option value="${item.id}">${item.display_name || item.username}（${roleLabelForOption(item)}）</option>`,
      ),
    )
    .join("");

  els.recruiter.value = recruiterValue || "";
  els.hiringManager.value = managerValue || "";
}

function renderCurrentUser() {
  if (!state.me) {
    els.currentUser.textContent = "未登录";
    if (els.operationsLink) {
      els.operationsLink.classList.add("hidden");
    }
    return;
  }
  const role = roleLabelForOption(state.me);
  els.currentUser.textContent = `当前用户：${state.me.display_name} (@${state.me.username}) · ${role}`;
  if (els.operationsLink) {
    els.operationsLink.classList.toggle("hidden", roleCodeFromUser(state.me) !== "administrator");
  }
}

function updateStatusBadge() {
  const job = state.draftJob;
  if (!job || !job.job_id) {
    els.statusBadge.textContent = "未保存";
    els.statusBadge.className = "job-status-badge";
    return;
  }
  els.statusBadge.textContent = jobStatusText(job.status);
  els.statusBadge.className = `job-status-badge ${job.status === "closed" ? "closed" : "open"}`;
}

function renderJobList() {
  const items = filteredJobs();
  els.jobList.innerHTML = "";
  if (items.length === 0) {
    const li = document.createElement("li");
    li.className = "job-empty";
    li.textContent = "暂无岗位，点击“新建岗位”开始配置。";
    els.jobList.appendChild(li);
    return;
  }

  items.forEach((job) => {
    const li = document.createElement("li");
    li.className = `job-item ${job.job_id === state.activeJobId ? "active" : ""}`;
    const templateCount = Array.isArray(job.templates) ? job.templates.length : 0;
    li.innerHTML = `
      <div class="job-item-title">${job.title || "未命名岗位"}</div>
      <div class="job-item-meta">${job.job_code || "-"} · ${job.department || "未设置部门"}</div>
      <div class="job-item-meta">地点：${job.location || "-"} · 编制：${job.headcount || "-"}</div>
      <div class="job-item-tags">
        <span class="tag">${jobStatusText(job.status)}</span>
        <span class="tag">流程:4阶段</span>
        <span class="tag">评分表:${templateCount}</span>
      </div>
    `;
    li.addEventListener("click", () => {
      selectJob(job.job_id);
    });
    els.jobList.appendChild(li);
  });
}

function activeTemplate(job) {
  const templates = Array.isArray(job.templates) ? job.templates : [];
  return templates.find((item) => Number(item.version_no) === Number(job.active_template_version)) || null;
}

function renderTemplatePreview(template) {
  if (!template) {
    els.templatePreview.innerHTML = "";
    return;
  }
  const headers = Array.isArray(template.preview && template.preview.headers) ? template.preview.headers : [];
  const rows = Array.isArray(template.preview && template.preview.rows) ? template.preview.rows : [];
  const note = String((template.preview && template.preview.note) || "").trim();
  const dimensions = Array.isArray(template.dimensions) ? template.dimensions : [];

  const previewParts = [];
  if (dimensions.length > 0) {
    const dimRows = dimensions
      .map(
        (item) =>
          `<li>维度：${item.dimension || "未命名维度"} · 评估点：${item.point || "-"} · 指标：${
            item.indicator || item.criterion || "-"
          } · 标准：${item.criterion || "-"} · 分值：${item.score || "-"}</li>`,
      )
      .join("");
    previewParts.push(`<ul class="template-dimension-list">${dimRows}</ul>`);
  }
  if (previewParts.length === 0) {
    previewParts.push('<div class="template-note">当前版本暂无可展示的预览内容，请重新上传评分表后再试。</div>');
  }
  els.templatePreview.innerHTML = previewParts.join("");
}

function renderTemplateSection() {
  const job = state.draftJob;
  if (!job) {
    return;
  }
  const templates = Array.isArray(job.templates) ? [...job.templates] : [];
  templates.sort((a, b) => Number(b.version_no || 0) - Number(a.version_no || 0));
  const active = activeTemplate(job);
  els.activeTemplateText.textContent = active
    ? `当前生效版本：V${active.version_no}（${active.filename}）`
    : "当前生效版本：无";

  els.templateVersionList.innerHTML = "";
  if (templates.length === 0) {
    const li = document.createElement("li");
    li.className = "template-empty";
    li.textContent = "暂无评分表版本";
    els.templateVersionList.appendChild(li);
    renderTemplatePreview(null);
    return;
  }

  templates.forEach((template) => {
    const li = document.createElement("li");
    li.className = "template-version-item";
    li.innerHTML = `
      <div>
        <strong>V${template.version_no}</strong> · ${template.filename}
        <div class="template-version-meta">上传时间：${formatTime(template.uploaded_at)} · 上传人：${template.uploaded_by || "-"}</div>
        <div class="template-version-meta">文件大小：${formatFileSize(template.size)} · 存储路径：${template.storage_rel_path || "-"}</div>
      </div>
      <div class="template-version-actions"></div>
    `;

    const actions = li.querySelector(".template-version-actions");
    const previewBtn = document.createElement("button");
    previewBtn.type = "button";
    previewBtn.className = "inline-btn";
    previewBtn.textContent = "预览";
    previewBtn.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      renderTemplatePreview(template);
      setTemplateMessage(`已预览 V${template.version_no}（${template.filename}）`, "success");
    });
    actions.appendChild(previewBtn);

    if (Number(template.version_no) !== Number(job.active_template_version)) {
      const activateBtn = document.createElement("button");
      activateBtn.type = "button";
      activateBtn.className = "inline-btn";
      activateBtn.textContent = "设为生效";
      activateBtn.addEventListener("click", () => activateTemplateVersion(template.version_no));
      actions.appendChild(activateBtn);
    } else {
      const tag = document.createElement("span");
      tag.className = "template-active-tag";
      tag.textContent = "生效中";
      actions.appendChild(tag);
    }

    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "inline-btn";
    deleteBtn.textContent = "删除";
    deleteBtn.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      void deleteTemplateVersion(template.version_no);
    });
    actions.appendChild(deleteBtn);

    els.templateVersionList.appendChild(li);
  });

  renderTemplatePreview(active || templates[0]);
}

function renderLogs() {
  const logs = Array.isArray(state.draftJob && state.draftJob.logs) ? [...state.draftJob.logs] : [];
  logs.sort((a, b) => Date.parse(b.at || "") - Date.parse(a.at || ""));
  els.logList.innerHTML = "";
  if (logs.length === 0) {
    const li = document.createElement("li");
    li.className = "job-empty";
    li.textContent = "暂无关键操作日志";
    els.logList.appendChild(li);
    return;
  }
  logs.forEach((item) => {
    const li = document.createElement("li");
    li.className = "job-log-item";
    li.innerHTML = `
      <div class="job-log-main">${item.action}</div>
      <div class="job-log-sub">${formatTime(item.at)} · ${item.operator || "未知"}</div>
      <div class="job-log-sub">${item.detail || "-"}</div>
    `;
    els.logList.appendChild(li);
  });
}

function fillForm(job) {
  els.title.value = job.title || "";
  els.department.value = job.department || "";
  els.headcount.value = String(job.headcount || 1);
  els.location.value = job.location || "";
  els.recruiter.value = job.recruiter_user_id || "";
  els.hiringManager.value = job.hiring_manager_user_id || "";
  els.jd.value = job.jd || "";
  els.requirements.value = job.requirements || "";
  els.processScreening.value = (job.process && job.process.初筛) || "";
  els.processFirst.value = (job.process && job.process.一面) || "";
  els.processSecond.value = (job.process && job.process.二面) || "";
  els.processHr.value = (job.process && job.process.HR面) || "";
  els.criteriaEducation.value = (job.criteria && job.criteria.education) || "";
  els.criteriaMajor.value = (job.criteria && job.criteria.major) || "";
  els.criteriaSkills.value = (job.criteria && job.criteria.skills) || "";
  els.criteriaProject.value = (job.criteria && job.criteria.project_experience) || "";
  els.autoScoreEnabled.checked = Boolean(job.auto_score_enabled);
  updateStatusBadge();
  renderTemplateSection();
  renderLogs();
}

function resetDraftToNew() {
  state.activeJobId = "";
  state.draftJob = blankJobDraft();
  els.formTitle.textContent = "新建岗位";
  setMessage("");
  setTemplateMessage("");
  fillForm(state.draftJob);
  renderJobList();
}

function selectJob(jobId) {
  const job = state.jobs.find((item) => item.job_id === jobId);
  if (!job) {
    return;
  }
  state.activeJobId = jobId;
  state.draftJob = deepCopy(job);
  els.formTitle.textContent = `${job.title || "岗位"}（${job.job_code || "-"}）`;
  setMessage("");
  setTemplateMessage("");
  fillForm(state.draftJob);
  renderJobList();
}

function syncDraftToState() {
  if (!state.draftJob) {
    return;
  }
  const index = state.jobs.findIndex((item) => item.job_id === state.draftJob.job_id);
  if (index === -1) {
    state.jobs.push(deepCopy(state.draftJob));
  } else {
    state.jobs[index] = deepCopy(state.draftJob);
  }
  persistJobs();
}

function collectDraftFromForm() {
  const title = String(els.title.value || "").trim();
  const department = normalizeDepartment(els.department.value);
  const headcount = Number.parseInt(els.headcount.value, 10);
  const location = String(els.location.value || "").trim();
  const recruiterUserId = String(els.recruiter.value || "").trim();
  const hiringManagerUserId = String(els.hiringManager.value || "").trim();
  const jd = String(els.jd.value || "").trim();
  const requirements = String(els.requirements.value || "").trim();

  if (!title) {
    return { error: "岗位名称不能为空" };
  }
  if (!department) {
    return { error: `所属部门仅支持：${DEPARTMENT_SCOPES.join(" / ")}` };
  }
  if (!Number.isFinite(headcount) || headcount < 1) {
    return { error: "招聘人数需为大于 0 的整数" };
  }
  if (!location) {
    return { error: "工作地点不能为空" };
  }
  if (!recruiterUserId) {
    return { error: "请选择招聘负责人" };
  }

  const process = {
    初筛: String(els.processScreening.value || "").trim(),
    一面: String(els.processFirst.value || "").trim(),
    二面: String(els.processSecond.value || "").trim(),
    HR面: String(els.processHr.value || "").trim(),
  };
  const criteria = {
    education: String(els.criteriaEducation.value || "").trim(),
    major: String(els.criteriaMajor.value || "").trim(),
    skills: String(els.criteriaSkills.value || "").trim(),
    project_experience: String(els.criteriaProject.value || "").trim(),
  };

  return {
    value: {
      title,
      department,
      headcount,
      location,
      recruiter_user_id: recruiterUserId,
      hiring_manager_user_id: hiringManagerUserId,
      jd,
      requirements,
      process,
      criteria,
      auto_score_enabled: Boolean(els.autoScoreEnabled.checked),
    },
  };
}

function ensureDraftExists() {
  if (!state.draftJob) {
    resetDraftToNew();
  }
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
    if (!canAccessJobPage(state.me)) {
      window.location.href = "/";
      return false;
    }
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

async function loadUserOptions() {
  const data = await fetchJSON("/api/users/options");
  state.users = Array.isArray(data.items) ? data.items : [];
  renderUserSelectOptions();
}

function readFiltersFromInputs() {
  state.filters.keyword = String(els.filterKeyword.value || "").trim();
  state.filters.status = String(els.filterStatus.value || "").trim();
  state.filters.department = normalizeDepartment(els.filterDepartment.value);
  persistFilters();
}

function syncFiltersToInputs() {
  els.filterKeyword.value = state.filters.keyword || "";
  els.filterStatus.value = state.filters.status || "";
  els.filterDepartment.value = state.filters.department || "";
}

function refreshListOnly() {
  readFiltersFromInputs();
  renderJobList();
}

function extractDimensions(headers, rows) {
  if (!Array.isArray(headers) || headers.length === 0 || !Array.isArray(rows)) {
    return [];
  }
  const indexByRule = (rules) => headers.findIndex((item) => rules.some((rule) => String(item).includes(rule)));
  const dimIndex = indexByRule(["评分维度", "维度", "dimension"]);
  const criterionIndex = indexByRule(["评分标准", "标准", "criterion"]);
  const scoreIndex = indexByRule(["分值", "分数", "score"]);
  if (dimIndex < 0) {
    return [];
  }
  const dimensions = [];
  rows.forEach((row) => {
    const dimension = String(row[dimIndex] || "").trim();
    if (!dimension) {
      return;
    }
    dimensions.push({
      dimension,
      criterion: criterionIndex >= 0 ? String(row[criterionIndex] || "").trim() : "",
      score: scoreIndex >= 0 ? String(row[scoreIndex] || "").trim() : "",
    });
  });
  return dimensions.slice(0, 50);
}

function parseDelimitedPreview(text) {
  const lines = String(text || "")
    .replace(/\r\n/g, "\n")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  if (lines.length === 0) {
    return { headers: [], rows: [], dimensions: [], note: "文件为空，未解析到可预览内容。" };
  }
  const firstLine = lines[0];
  const delimiterCandidates = [",", "\t", ";", "|"];
  let delimiter = ",";
  let maxCount = -1;
  delimiterCandidates.forEach((symbol) => {
    const count = firstLine.split(symbol).length;
    if (count > maxCount) {
      maxCount = count;
      delimiter = symbol;
    }
  });
  const splitLine = (line) => line.split(delimiter).map((item) => item.trim());
  const headers = splitLine(lines[0]).slice(0, 12);
  const rows = lines.slice(1, 7).map((line) => splitLine(line).slice(0, 12));
  const dimensions = extractDimensions(headers, rows);
  return {
    headers,
    rows,
    dimensions,
    note:
      dimensions.length > 0
        ? "已解析评分维度预览（最多展示 6 行）。"
        : "已解析表格预览；未识别到标准维度列，可继续上传保存版本。",
  };
}

async function parseTemplatePreview(file) {
  const name = String((file && file.name) || "");
  const ext = name.includes(".") ? name.split(".").pop().toLowerCase() : "";
  if (!["xlsx", "xls", "csv"].includes(ext)) {
    return { error: "评分表仅支持 .xlsx / .xls / .csv" };
  }
  if (Number(file.size || 0) <= 0) {
    return { error: "评分表文件不能为空" };
  }
  if (Number(file.size || 0) > MAX_TEMPLATE_FILE_BYTES) {
    return { error: "评分表文件过大（最大 8MB）" };
  }
  if (ext === "csv") {
    const text = await file.text();
    return { value: parseDelimitedPreview(text) };
  }
  return {
    value: {
      headers: [],
      rows: [],
      dimensions: [],
      note: "已通过格式校验。当前前端版本对 xls/xlsx 仅展示文件元信息，结构化解析将在后端评分服务接入后补齐。",
    },
  };
}

async function uploadTemplateVersion() {
  ensureDraftExists();
  if (!state.draftJob || !state.draftJob.job_id) {
    setTemplateMessage("请先保存岗位，再上传评分表版本", "error");
    return;
  }
  const file = els.templateFile.files && els.templateFile.files[0];
  if (!file) {
    setTemplateMessage("请选择评分表文件", "error");
    return;
  }
  els.templateUploadBtn.disabled = true;
  try {
    const form = new FormData();
    form.append("file", file);
    const data = await fetchJSON(`/api/jobs/${encodeURIComponent(state.draftJob.job_id)}/score-table`, {
      method: "POST",
      body: form,
    });
    const saved = normalizeJobItem(data.item || {});
    if (!saved.job_id) {
      throw new Error("评分表上传成功，但岗位数据返回异常");
    }
    applySavedJobFromServer(saved);

    const versions = Array.isArray(saved.templates) ? saved.templates : [];
    const latestVersion = versions.reduce((max, item) => Math.max(max, Number(item.version_no || 0)), 0);
    els.templateFile.value = "";
    setTemplateMessage(`已上传评分表版本 V${latestVersion}`, "success");
    setMessage("评分表版本已更新（已同步后端）", "success");
  } catch (err) {
    setTemplateMessage(err.message || "评分表上传失败", "error");
  } finally {
    els.templateUploadBtn.disabled = false;
  }
}

function activateTemplateVersion(versionNo) {
  ensureDraftExists();
  if (!state.draftJob || !state.draftJob.job_id) {
    setTemplateMessage("请先保存岗位", "error");
    return;
  }
  const template = (state.draftJob.templates || []).find((item) => Number(item.version_no) === Number(versionNo));
  if (!template) {
    setTemplateMessage("版本不存在", "error");
    return;
  }
  state.draftJob.active_template_version = Number(versionNo);
  state.draftJob.updated_at = nowIso();
  appendJobLog(state.draftJob, "评分表生效切换", `切换到 V${versionNo}`);
  syncDraftToState();
  renderTemplateSection();
  renderLogs();
  setTemplateMessage(`已切换到 V${versionNo}`, "success");
}

async function deleteTemplateVersion(versionNo) {
  ensureDraftExists();
  if (!state.draftJob || !state.draftJob.job_id) {
    setTemplateMessage("请先保存岗位", "error");
    return;
  }
  const template = (state.draftJob.templates || []).find((item) => Number(item.version_no) === Number(versionNo));
  if (!template) {
    setTemplateMessage("版本不存在", "error");
    return;
  }

  const isActive = Number(versionNo) === Number(state.draftJob.active_template_version);
  const confirmText = isActive
    ? `确认删除评分表版本 V${versionNo}（${template.filename || "-"})？当前版本为生效版本，删除后将自动切换。`
    : `确认删除评分表版本 V${versionNo}（${template.filename || "-"})？删除后不可恢复。`;
  if (!window.confirm(confirmText)) {
    return;
  }

  try {
    const data = await fetchJSON(
      `/api/jobs/${encodeURIComponent(state.draftJob.job_id)}/score-table/${encodeURIComponent(String(versionNo))}`,
      { method: "DELETE" },
    );
    const saved = normalizeJobItem(data.item || {});
    if (!saved.job_id) {
      throw new Error("评分表删除成功，但岗位数据返回异常");
    }
    applySavedJobFromServer(saved);
    if (Number(saved.active_template_version || 0) > 0) {
      setTemplateMessage(`已删除 V${versionNo}，当前生效版本 V${saved.active_template_version}`, "success");
    } else {
      setTemplateMessage(`已删除 V${versionNo}，当前无生效评分表版本`, "success");
    }
    setMessage("评分表版本删除成功（已同步后端）", "success");
  } catch (err) {
    setTemplateMessage(err.message || "评分表版本删除失败", "error");
  }
}

function applyDraftValue(nextValue) {
  ensureDraftExists();
  const beforeAutoScore = Boolean(state.draftJob.auto_score_enabled);
  Object.assign(state.draftJob, nextValue);
  state.draftJob.updated_at = nowIso();
  if (beforeAutoScore !== Boolean(state.draftJob.auto_score_enabled)) {
    appendJobLog(
      state.draftJob,
      state.draftJob.auto_score_enabled ? "启用自动评分" : "停用自动评分",
      state.draftJob.auto_score_enabled ? "开启 AI 自动评分" : "关闭 AI 自动评分",
    );
  }
}

function saveDraftJob(event) {
  event.preventDefault();
  ensureDraftExists();
  const parsed = collectDraftFromForm();
  if (parsed.error) {
    setMessage(parsed.error, "error");
    return;
  }

  const now = nowIso();
  const isNew = !state.draftJob.job_id;
  if (isNew) {
    state.draftJob.job_id = uid("job");
    state.draftJob.job_code = generateJobCode();
    state.draftJob.created_at = now;
    state.draftJob.status = "open";
    state.activeJobId = state.draftJob.job_id;
  }
  applyDraftValue(parsed.value);

  appendJobLog(
    state.draftJob,
    isNew ? "岗位创建" : "岗位更新",
    `${state.draftJob.title}（${state.draftJob.job_code || "-"}）`,
  );
  syncDraftToState();
  renderJobList();
  els.formTitle.textContent = `${state.draftJob.title}（${state.draftJob.job_code}）`;
  updateStatusBadge();
  renderLogs();
  setMessage(isNew ? "岗位创建成功" : "岗位保存成功", "success");
}

function closeActiveJob() {
  ensureDraftExists();
  if (!state.draftJob || !state.draftJob.job_id) {
    setMessage("请先保存岗位", "error");
    return;
  }
  if (state.draftJob.status === "closed") {
    setMessage("岗位已是关闭状态", "error");
    return;
  }
  state.draftJob.status = "closed";
  state.draftJob.closed_at = nowIso();
  state.draftJob.updated_at = nowIso();
  appendJobLog(state.draftJob, "岗位关闭", `${state.draftJob.title}`);
  syncDraftToState();
  renderJobList();
  updateStatusBadge();
  renderLogs();
  setMessage("岗位已关闭", "success");
}

function copyActiveJob() {
  ensureDraftExists();
  if (!state.draftJob || !state.draftJob.job_id) {
    setMessage("请先保存岗位再复制", "error");
    return;
  }
  const source = state.draftJob;
  const copy = deepCopy(source);
  copy.job_id = uid("job");
  copy.job_code = generateJobCode();
  copy.title = `${source.title}（复制）`;
  copy.status = "open";
  copy.closed_at = "";
  copy.auto_score_enabled = false;
  copy.created_at = nowIso();
  copy.updated_at = nowIso();
  copy.logs = [];
  appendJobLog(copy, "岗位复制创建", `源岗位：${source.job_code}`);
  state.jobs.push(copy);
  persistJobs();
  selectJob(copy.job_id);
  setMessage("岗位复制成功", "success");
}

function triggerAutoScore() {
  ensureDraftExists();
  if (!state.draftJob || !state.draftJob.job_id) {
    setMessage("请先保存岗位", "error");
    return;
  }
  const autoScoreEnabledNow = Boolean(els.autoScoreEnabled && els.autoScoreEnabled.checked);
  if (!autoScoreEnabledNow) {
    setMessage("请先勾选“启用 AI 自动评分”", "error");
    return;
  }
  if (!state.draftJob.active_template_version) {
    setMessage("请先上传并生效评分表版本", "error");
    return;
  }
  state.draftJob.auto_score_enabled = true;
  appendJobLog(
    state.draftJob,
    "触发评分",
    `触发岗位自动评分（模板 V${state.draftJob.active_template_version}）`,
  );
  state.draftJob.updated_at = nowIso();
  syncDraftToState();
  renderLogs();
  setMessage("已记录触发评分操作（当前为前端演示链路）", "success");
}

function resetFilters() {
  state.filters = { keyword: "", status: "", department: "" };
  persistFilters();
  syncFiltersToInputs();
  renderJobList();
}

async function logout() {
  try {
    await fetchJSON("/api/auth/logout", { method: "POST" });
  } catch {
    // ignore
  }
  redirectToLogin(false);
}

els.form.addEventListener("submit", saveDraftJob);
els.logoutBtn.addEventListener("click", logout);
els.newBtn.addEventListener("click", resetDraftToNew);
els.closeBtn.addEventListener("click", closeActiveJob);
els.copyBtn.addEventListener("click", copyActiveJob);
els.triggerScoreBtn.addEventListener("click", triggerAutoScore);
els.templateUploadBtn.addEventListener("click", uploadTemplateVersion);
els.filterResetBtn.addEventListener("click", resetFilters);
els.filterKeyword.addEventListener("input", refreshListOnly);
els.filterStatus.addEventListener("change", refreshListOnly);
els.filterDepartment.addEventListener("change", refreshListOnly);

(async () => {
  const ok = await ensureAuthenticated();
  if (!ok) {
    return;
  }
  renderCurrentUser();
  try {
    await loadUserOptions();
  } catch (err) {
    if (err.status === 401) {
      redirectToLogin(false);
      return;
    }
    if (err.status === 403 && err.code === "must_change_password") {
      redirectToLogin(true);
      return;
    }
    setMessage(err.message || "加载用户选项失败", "error");
  }

  state.jobs = loadJobs();
  try {
    const remoteJobs = await fetchJobsFromServer();
    replaceJobsLocally(remoteJobs);
  } catch (err) {
    setMessage(`加载岗位失败，已使用本地缓存：${err.message || "请求失败"}`, "error");
  }
  syncFiltersToInputs();
  renderJobList();
  if (state.jobs.length > 0) {
    const first = filteredJobs()[0] || state.jobs.sort(compareJobsByUpdateDesc)[0];
    if (first) {
      selectJob(first.job_id);
      return;
    }
  }
  resetDraftToNew();
})();
