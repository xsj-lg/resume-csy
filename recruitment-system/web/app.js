const INTERVIEW_STAGES = ["初筛", "一面", "二面", "HR面"];
const STATUS_PENDING = "pending";
const STATUS_PASSED = "passed";
const STATUS_ENDED = "ended";

const CANDIDATE_STATUS_BY_STAGE = {
  初筛: "待初筛",
  一面: "待一面",
  二面: "待二面",
  HR面: "待HR面",
};
const FAILED_STATUS_BY_STAGE = {
  初筛: "未通过初筛",
  一面: "未通过一面",
  二面: "未通过二面",
  HR面: "未通过HR面",
};
const FAILED_CANDIDATE_STATUSES = new Set(Object.values(FAILED_STATUS_BY_STAGE));

const DEFAULT_SORT_MODE = "star_time";
const SORT_MODES = new Set(["star_time", "time", "name"]);
const POSITION_MATCH_MODES = new Set(["fuzzy", "exact"]);
const FILTER_DEBOUNCE_MS = 260;
const ROLE_ORDER = ["administrator", "hr_specialist", "interviewer", "hiring_manager"];
const DEPARTMENT_SCOPES = ["销售部", "研发部", "算法部", "项目部", "人事部"];
const STAGE_STATUS_OPTIONS = [
  "",
  "待初筛",
  "待一面",
  "待二面",
  "待HR面",
  "通过",
  "未通过初筛",
  "未通过一面",
  "未通过二面",
  "未通过HR面",
];
const JOB_STORAGE_KEY = "rs_jobs_v012";
const JOBS_API_URL = "/api/jobs";
const WORKSPACE_SELECTION_STORAGE_KEY = "rs_workspace_last_candidate_v1";
const ROLE_LABELS = {
  administrator: "管理员",
  hr_specialist: "HR / 招聘专员",
  interviewer: "面试官",
  hiring_manager: "部门负责人 / 用人经理",
};

const state = {
  candidates: [],
  candidateTotalCount: 0,
  candidateFilteredCount: 0,
  candidateFilters: {
    name: "",
    position: "",
    positionMatch: "fuzzy",
    department: "",
    uploadFrom: "",
    uploadTo: "",
    stageStatus: "",
    uploadDate: "",
  },
  activeId: null,
  evaluation: null,
  viewStage: INTERVIEW_STAGES[0],
  sortMode: loadSortMode(),
  showAllCandidates: loadShowAll(),
  calendarItems: [],
  interviewerOptions: [],
  currentUser: null,
  uploadJobs: [],
  jobSnapshotsById: {},
  candidateReloadTimer: null,
  candidateFetchSeq: 0,
  uploadDateOptions: [],
};

const els = {
  list: document.getElementById("candidate-list"),
  count: document.getElementById("candidate-count"),
  activeCandidate: document.getElementById("active-candidate"),
  activeMeta: document.getElementById("active-meta"),
  frame: document.getElementById("resume-frame"),
  hint: document.getElementById("save-hint"),
  form: document.getElementById("evaluation-form"),
  message: document.getElementById("form-message"),

  currentUserText: document.getElementById("current-user-text"),
  jobsManageLink: document.getElementById("jobs-manage-link"),
  operationsManageLink: document.getElementById("operations-manage-link"),
  usersManageLink: document.getElementById("users-manage-link"),
  logoutBtn: document.getElementById("logout-btn"),
  uploadResumeBtn: document.getElementById("upload-resume-btn"),
  syncResumesBtn: document.getElementById("sync-resumes-btn"),
  uploadModal: document.getElementById("upload-modal"),
  uploadForm: document.getElementById("upload-form"),
  uploadFile: document.getElementById("upload-file"),
  uploadJob: document.getElementById("upload-job"),
  uploadCandidateName: document.getElementById("upload-candidate-name"),
  uploadDepartment: document.getElementById("upload-department"),
  uploadSubmitBtn: document.getElementById("upload-submit-btn"),
  uploadCancelBtn: document.getElementById("upload-cancel-btn"),
  uploadMessage: document.getElementById("upload-message"),
  filterName: document.getElementById("candidate-filter-name"),
  filterPosition: document.getElementById("candidate-filter-position"),
  filterPositionMatch: document.getElementById("candidate-filter-position-match"),
  filterDepartmentWrap: document.getElementById("candidate-filter-department-wrap"),
  filterDepartment: document.getElementById("candidate-filter-department"),
  filterStageStatus: document.getElementById("candidate-filter-stage"),
  filterUploadFrom: document.getElementById("candidate-filter-upload-from"),
  filterUploadTo: document.getElementById("candidate-filter-upload-to"),
  filterUploadDate: document.getElementById("candidate-filter-upload-date"),
  filterResetBtn: document.getElementById("candidate-filter-reset-btn"),

  sortMode: document.getElementById("candidate-sort-mode"),
  showAll: document.getElementById("show-all-candidates"),
  calendarList: document.getElementById("interview-calendar"),
  calendarCount: document.getElementById("calendar-count"),

  stageAxis: document.getElementById("stage-axis"),
  currentStageText: document.getElementById("current-stage-text"),
  stageEndedFrom: document.getElementById("stage-ended-from"),
  stageNextBtn: document.getElementById("stage-next-btn"),
  stageEndBtn: document.getElementById("stage-end-btn"),
  stageResetBtn: document.getElementById("stage-reset-btn"),
  triggerAutoScoreBtn: document.getElementById("trigger-auto-score-btn"),
  jobConfigMeta: document.getElementById("job-config-meta"),
  jobConfigList: document.getElementById("job-config-list"),
  triggerResumeExtractBtn: document.getElementById("trigger-resume-extract-btn"),
  resumeExtractMeta: document.getElementById("resume-extract-meta"),
  extractPhone: document.getElementById("extract-phone"),
  extractEmail: document.getElementById("extract-email"),
  extractLocation: document.getElementById("extract-location"),
  extractMajor: document.getElementById("extract-major"),
  extractSkills: document.getElementById("extract-skills"),
  extractCertificates: document.getElementById("extract-certificates"),
  extractSummary: document.getElementById("extract-summary"),
  extractEducation: document.getElementById("extract-education"),
  extractWork: document.getElementById("extract-work"),
  extractProject: document.getElementById("extract-project"),
  aiScoreMeta: document.getElementById("ai-score-meta"),
  aiScoreSummary: document.getElementById("ai-score-summary"),
  aiScoreRiskList: document.getElementById("ai-score-risk-list"),
  aiScoreDimensionList: document.getElementById("ai-score-dimension-list"),
  roundSectionTitle: document.getElementById("round-section-title"),
  saveRoundBtn: document.getElementById("save-round-btn"),
  saveProfileBtn: document.getElementById("save-profile-btn"),
  deleteCandidateBtn: document.getElementById("delete-candidate-btn"),

  candidateName: document.getElementById("candidate-name"),
  baseLocation: document.getElementById("base-location"),
  candidateDepartment: document.getElementById("candidate-department"),
  appliedPosition: document.getElementById("applied-position"),
  candidateJob: document.getElementById("candidate-job"),
  salaryMode: document.getElementById("salary-mode"),
  salaryRange: document.getElementById("salary-range"),
  experienceType: document.getElementById("experience-type"),
  graduationWrap: document.getElementById("graduation-wrap"),
  graduationYear: document.getElementById("graduation-year"),
  workWrap: document.getElementById("work-wrap"),
  workYears: document.getElementById("work-years"),
  highestEducation: document.getElementById("highest-education"),
  schoolName: document.getElementById("school-name"),
  hireType: document.getElementById("hire-type"),
  presetPosition: document.getElementById("preset-position"),

  interviewTime: document.getElementById("interview-time"),
  stageInterviewer: document.getElementById("stage-interviewer"),
  plannedQuestions: document.getElementById("planned-questions"),
  interviewReview: document.getElementById("interview-review"),
};

function loadSortMode() {
  const value = window.localStorage.getItem("candidateSortMode") || DEFAULT_SORT_MODE;
  return SORT_MODES.has(value) ? value : DEFAULT_SORT_MODE;
}

function loadShowAll() {
  return window.localStorage.getItem("showAllCandidates") === "1";
}

function currentUserStorageId() {
  return String(state.currentUser?.id || "").trim();
}

function loadWorkspaceSelection() {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(WORKSPACE_SELECTION_STORAGE_KEY) || "{}");
    if (!parsed || typeof parsed !== "object") {
      return {};
    }
    return parsed;
  } catch {
    return {};
  }
}

function loadLastActiveCandidateId() {
  const stored = loadWorkspaceSelection();
  const candidateId = String(stored.candidateId || "").trim();
  if (!candidateId) {
    return "";
  }
  const storedUserId = String(stored.userId || "").trim();
  const currentUserId = currentUserStorageId();
  if (storedUserId && currentUserId && storedUserId !== currentUserId) {
    return "";
  }
  return candidateId;
}

function persistActiveCandidateSelection(candidateId = state.activeId) {
  const normalized = String(candidateId || "").trim();
  if (!normalized) {
    window.localStorage.removeItem(WORKSPACE_SELECTION_STORAGE_KEY);
    return;
  }
  window.localStorage.setItem(
    WORKSPACE_SELECTION_STORAGE_KEY,
    JSON.stringify({
      candidateId: normalized,
      userId: currentUserStorageId(),
      updatedAt: new Date().toISOString(),
    }),
  );
}

function clearActiveCandidateSelection() {
  window.localStorage.removeItem(WORKSPACE_SELECTION_STORAGE_KEY);
}

function scrollActiveCandidateIntoView() {
  if (!state.activeId || !els.list) {
    return;
  }
  const activeItem = Array.from(els.list.querySelectorAll(".candidate-item")).find(
    (item) => item.dataset.candidateId === state.activeId,
  );
  if (!activeItem) {
    return;
  }
  window.requestAnimationFrame(() => {
    activeItem.scrollIntoView({ block: "nearest" });
  });
}

function normalizeFilterKeyword(value) {
  return String(value || "").trim();
}

function normalizeDepartmentScope(value) {
  const text = String(value || "").trim();
  return DEPARTMENT_SCOPES.includes(text) ? text : "";
}

function populateFilterSelect(select, options, blankLabel = "全部") {
  if (!select) {
    return;
  }
  select.innerHTML = options
    .map((value, index) => {
      const label = value || blankLabel;
      return `<option value="${value}">${label}</option>`;
    })
    .join("");
}

function updateUploadDateSelect(options) {
  const list = Array.isArray(options) ? options : [];
  state.uploadDateOptions = list;
  if (!els.filterUploadDate) {
    return;
  }
  populateFilterSelect(els.filterUploadDate, ["", ...list], "选择上传日期");
  if (state.candidateFilters.uploadDate) {
    els.filterUploadDate.value = state.candidateFilters.uploadDate;
  } else {
    els.filterUploadDate.value = "";
  }
}

function initCandidateFilterSelects() {
  populateFilterSelect(els.filterStageStatus, STAGE_STATUS_OPTIONS, "全部阶段");
  updateUploadDateSelect(state.uploadDateOptions);
}

function readCandidateFiltersFromInputs() {
  const name = normalizeFilterKeyword(els.filterName.value);
  const position = normalizeFilterKeyword(els.filterPosition.value);
  const selectedMode = String(els.filterPositionMatch.value || "").trim().toLowerCase();
  const positionMatch = POSITION_MATCH_MODES.has(selectedMode) ? selectedMode : "fuzzy";
  const department = normalizeDepartmentScope(els.filterDepartment?.value || "");
  const stageStatus = normalizeFilterKeyword(els.filterStageStatus?.value || "");
  const uploadFrom = String(els.filterUploadFrom?.value || "").trim();
  const uploadTo = String(els.filterUploadTo?.value || "").trim();
  const uploadDate = String(els.filterUploadDate?.value || "").trim();
  return {
    name,
    position,
    positionMatch,
    department,
    stageStatus,
    uploadFrom,
    uploadTo,
    uploadDate,
  };
}

function syncCandidateFilterInputs() {
  els.filterName.value = state.candidateFilters.name;
  els.filterPosition.value = state.candidateFilters.position;
  els.filterPositionMatch.value = state.candidateFilters.positionMatch;
  if (els.filterDepartment) {
    els.filterDepartment.value = state.candidateFilters.department || "";
  }
  if (els.filterStageStatus) {
    els.filterStageStatus.value = state.candidateFilters.stageStatus || "";
  }
  if (els.filterUploadFrom) {
    els.filterUploadFrom.value = state.candidateFilters.uploadFrom || "";
  }
  if (els.filterUploadTo) {
    els.filterUploadTo.value = state.candidateFilters.uploadTo || "";
  }
  if (els.filterUploadDate) {
    els.filterUploadDate.value = state.candidateFilters.uploadDate || "";
  }
}

function hasActiveCandidateFilters() {
  const filters = state.candidateFilters;
  return Boolean(
    filters.name
      || filters.position
      || filters.department
      || filters.stageStatus
      || filters.uploadFrom
      || filters.uploadTo
      || filters.uploadDate
  );
}

function buildCandidatesApiURL() {
  const params = new URLSearchParams();
  if (state.candidateFilters.name) {
    params.set("candidate_name", state.candidateFilters.name);
  }
  if (state.candidateFilters.position) {
    params.set("applied_position", state.candidateFilters.position);
    params.set("position_match", state.candidateFilters.positionMatch);
  }
  if (state.candidateFilters.department) {
    params.set("department_scope", state.candidateFilters.department);
  }
  if (state.candidateFilters.stageStatus) {
    params.set("stage_status", state.candidateFilters.stageStatus);
  }
  if (state.candidateFilters.uploadDate) {
    params.set("upload_date", state.candidateFilters.uploadDate);
  } else {
    if (state.candidateFilters.uploadFrom) {
      params.set("uploaded_from", state.candidateFilters.uploadFrom);
    }
    if (state.candidateFilters.uploadTo) {
      params.set("uploaded_to", state.candidateFilters.uploadTo);
    }
  }
  const query = params.toString();
  return query ? `/api/candidates?${query}` : "/api/candidates";
}

function setMessage(text, kind = "") {
  els.message.textContent = text;
  els.message.className = "form-message";
  if (kind) {
    els.message.classList.add(kind);
  }
}

function setUploadMessage(text, kind = "") {
  els.uploadMessage.textContent = text;
  els.uploadMessage.className = "form-message";
  if (kind) {
    els.uploadMessage.classList.add(kind);
  }
}

function suggestedNameFromFilename(filename) {
  const text = (filename || "").trim();
  if (!text) {
    return "";
  }
  const dot = text.lastIndexOf(".");
  return dot > 0 ? text.slice(0, dot) : text;
}

function normalizeJobId(value) {
  return String(value || "").trim();
}

function normalizeUploadJob(item) {
  const jobId = normalizeJobId(item?.job_id);
  const title = String(item?.title || item?.job_title || "").trim();
  const activeTemplateVersion = item?.active_template_version ?? item?.score_table_version ?? 0;
  return {
    job_id: jobId,
    job_code: String(item?.job_code || "").trim(),
    title,
    department: normalizeDepartmentScope(item?.department || item?.department_scope),
    status: String(item?.status || "open").trim(),
    updated_at: String(item?.updated_at || item?.created_at || "").trim(),
    jd: String(item?.jd || "").trim(),
    requirements: String(item?.requirements || "").trim(),
    criteria: item?.criteria && typeof item.criteria === "object" ? item.criteria : {},
    process: item?.process && typeof item.process === "object" ? item.process : {},
    auto_score_enabled: Boolean(item?.auto_score_enabled),
    active_template_version: activeTemplateVersion,
    templates: Array.isArray(item?.templates) ? item.templates : [],
  };
}

function templatesFromSnapshot(snapshot) {
  if (!snapshot || typeof snapshot !== "object") {
    return [];
  }
  if (Array.isArray(snapshot.templates) && snapshot.templates.length > 0) {
    return snapshot.templates;
  }
  const scoreItems = Array.isArray(snapshot.score_items) ? snapshot.score_items : [];
  const dimensions = scoreItems
    .map((item) => ({
      dimension: String(item?.dimension || "").trim(),
      criterion: String(item?.criterion || "").trim(),
      score: String(item?.score || "").trim(),
    }))
    .filter((item) => item.dimension || item.criterion || item.score);
  if (dimensions.length === 0) {
    return [];
  }
  const versionNo = snapshot.score_table_version || 1;
  return [{ version_no: versionNo, filename: "snapshot", dimensions }];
}

function parseUploadJobsFromStorage() {
  try {
    const raw = JSON.parse(window.localStorage.getItem(JOB_STORAGE_KEY) || "[]");
    if (!Array.isArray(raw)) {
      return [];
    }
    return raw
      .map((item) => normalizeUploadJob(item))
      .filter((item) => item.job_id && item.title && item.status !== "closed")
      .sort((a, b) => Date.parse(b.updated_at || "") - Date.parse(a.updated_at || ""));
  } catch {
    return [];
  }
}

async function fetchUploadJobsFromServer() {
  const data = await fetchJSON(JOBS_API_URL);
  const items = Array.isArray(data.items) ? data.items : [];
  return items
    .map((item) => normalizeUploadJob(item))
    .filter((item) => item.job_id && item.title && item.status !== "closed")
    .sort((a, b) => Date.parse(b.updated_at || "") - Date.parse(a.updated_at || ""));
}

function collectUploadJobsFromCandidates() {
  const byId = new Map();
  state.candidates.forEach((candidate) => {
    const jobId = normalizeJobId(candidate?.job_id);
    const jobTitle = String(candidate?.job_title || "").trim();
    if (!jobId || !jobTitle) {
      return;
    }
    const snapshot = state.jobSnapshotsById[jobId] || {};
    const candidateJob = normalizeUploadJob({
      job_id: jobId,
      job_code: String(candidate?.job_code || "").trim(),
      job_title: jobTitle,
      department_scope: normalizeDepartmentScope(candidate?.department_scope || ""),
      jd: String(snapshot?.jd || "").trim(),
      requirements: String(snapshot?.requirements || "").trim(),
      criteria: snapshot?.criteria || {},
      process: snapshot?.process || {},
      auto_score_enabled: Boolean(snapshot?.auto_score_enabled),
      active_template_version: snapshot?.score_table_version || 0,
      templates: templatesFromSnapshot(snapshot),
      status: "open",
    });
    byId.set(jobId, candidateJob);
  });
  return Array.from(byId.values());
}

function mergeUploadJobs(storageJobs, candidateJobs) {
  const merged = new Map();
  storageJobs.forEach((job) => {
    merged.set(job.job_id, { ...job });
  });
  candidateJobs.forEach((job) => {
    const existing = merged.get(job.job_id);
    if (!existing) {
      merged.set(job.job_id, { ...job });
      return;
    }
    merged.set(job.job_id, {
      ...existing,
      job_code: existing.job_code || job.job_code,
      title: existing.title || job.title,
      department: existing.department || job.department,
      jd: existing.jd || job.jd,
      requirements: existing.requirements || job.requirements,
      criteria:
        existing.criteria && Object.keys(existing.criteria).length > 0
          ? existing.criteria
          : job.criteria,
      process:
        existing.process && Object.keys(existing.process).length > 0
          ? existing.process
          : job.process,
      auto_score_enabled: Boolean(existing.auto_score_enabled || job.auto_score_enabled),
      active_template_version: existing.active_template_version || job.active_template_version || 0,
      templates:
        Array.isArray(existing.templates) && existing.templates.length > 0
          ? existing.templates
          : job.templates,
    });
  });
  return Array.from(merged.values()).sort((a, b) => Date.parse(b.updated_at || "") - Date.parse(a.updated_at || ""));
}

function renderUploadJobOptions() {
  if (!els.uploadJob) {
    return;
  }
  const selected = normalizeJobId(els.uploadJob.value);
  const jobs = state.uploadJobs;
  if (jobs.length === 0) {
    els.uploadJob.innerHTML = '<option value="">暂无可关联岗位（请先到岗位管理创建）</option>';
    els.uploadJob.value = "";
    return;
  }
  els.uploadJob.innerHTML = ['<option value="">请选择岗位</option>']
    .concat(
      jobs.map((job) => {
        const codeText = job.job_code ? ` [${job.job_code}]` : "";
        const departmentText = job.department ? ` · ${job.department}` : "";
        return `<option value="${job.job_id}">${job.title}${codeText}${departmentText}</option>`;
      }),
    )
    .join("");
  els.uploadJob.value = jobs.some((job) => job.job_id === selected) ? selected : "";
}

async function refreshUploadJobs() {
  let storageJobs = [];
  try {
    storageJobs = await fetchUploadJobsFromServer();
  } catch {
    storageJobs = parseUploadJobsFromStorage();
  }
  const candidateJobs = collectUploadJobsFromCandidates();
  state.uploadJobs = mergeUploadJobs(storageJobs, candidateJobs);
  renderUploadJobOptions();
  renderCandidateJobOptions(state.evaluation?.profile || null);
}

function selectedUploadJob() {
  const selectedJobId = normalizeJobId(els.uploadJob?.value || "");
  if (!selectedJobId) {
    return null;
  }
  return state.uploadJobs.find((job) => job.job_id === selectedJobId) || null;
}

function renderCandidateJobOptions(profile = null) {
  if (!els.candidateJob) {
    return;
  }
  const profileJobId = normalizeJobId(profile?.job_id || "");
  const selected = normalizeJobId(els.candidateJob.value || profileJobId);
  const jobs = state.uploadJobs;

  const options = ['<option value="">请选择岗位</option>'].concat(
    jobs.map((job) => {
      const codeText = job.job_code ? ` [${job.job_code}]` : "";
      const departmentText = job.department ? ` · ${job.department}` : "";
      return `<option value="${job.job_id}">${job.title}${codeText}${departmentText}</option>`;
    }),
  );

  const hasSelected = selected && jobs.some((job) => job.job_id === selected);
  if (!hasSelected && selected) {
    const currentTitle = String(profile?.job_title || "").trim();
    const currentCode = String(profile?.job_code || "").trim();
    const fallbackText = currentTitle
      ? `${currentTitle}${currentCode ? ` [${currentCode}]` : ""}（当前关联）`
      : `${selected}（当前关联）`;
    options.push(`<option value="${selected}">${fallbackText}</option>`);
  }

  els.candidateJob.innerHTML = options.join("");
  els.candidateJob.value = selected || "";
}

function selectedCandidateJob() {
  const selectedJobId = normalizeJobId(els.candidateJob?.value || "");
  if (!selectedJobId) {
    return null;
  }
  return state.uploadJobs.find((job) => job.job_id === selectedJobId) || null;
}

function buildUploadJobPayload(job) {
  const activeVersion = Number(job?.active_template_version || 0);
  const templates = Array.isArray(job?.templates) ? job.templates : [];
  const activeTemplate =
    templates.find((item) => Number(item?.version_no || 0) === activeVersion) ||
    templates[templates.length - 1] ||
    null;
  const dimensions = Array.isArray(activeTemplate?.dimensions)
    ? activeTemplate.dimensions
        .map((item) => ({
          dimension: String(item?.dimension || "").trim(),
          criterion: String(item?.criterion || "").trim(),
          score: String(item?.score || "").trim(),
        }))
        .filter((item) => item.dimension || item.criterion || item.score)
    : [];
  const rawDimensions = [];

  const normalizedDimensionScores = rawDimensions
    .filter((item) => item && typeof item === "object")
    .map((item) => {
      const name = String(item.dimension_name || item.dimension || item.name || "").trim() || "未命名维度";
      const dimScore = Number(item.dimension_score ?? item.score ?? item.score_value ?? 0);
      const dimMax = Number(item.dimension_max ?? item.max_score ?? item.max ?? 0);
      const items = (Array.isArray(item.items) ? item.items : [])
        .filter((entry) => entry && typeof entry === "object")
        .map((entry) => ({
          name: String(entry.item_name || entry.point || entry.point_name || entry.name || "").trim() || "未命名评分项",
          score: Number(entry.item_score ?? entry.score ?? entry.score_value ?? 0),
          standard: String(entry.selected_standard || entry.criterion || entry.standard || "").trim(),
          reason: String(entry.reason || "").trim(),
          confidence: String(entry.confidence || "").trim(),
          evidence: Array.isArray(entry.evidence)
            ? entry.evidence.map((value) => String(value || "").trim()).filter(Boolean)
            : [],
        }));
      return { name, score: dimScore, max: dimMax, items };
    });

  return {
    job_id: job?.job_id || "",
    job_code: job?.job_code || "",
    job_title: job?.title || "",
    department_scope: job?.department || "",
    jd: job?.jd || "",
    requirements: job?.requirements || "",
    criteria: job?.criteria || {},
    process: job?.process || {},
    auto_score_enabled: Boolean(job?.auto_score_enabled),
    active_template_version: activeTemplate?.version_no || activeVersion || "",
    templates: activeTemplate
      ? [
          {
            version_no: activeTemplate.version_no || activeVersion || "",
            filename: activeTemplate.filename || "",
            dimensions,
          },
        ]
      : [],
  };
}

async function openUploadModal() {
  await refreshUploadJobs();
  els.uploadModal.classList.remove("hidden");
  els.uploadCandidateName.disabled = false;
  if (els.uploadDepartment && !normalizeDepartmentScope(els.uploadDepartment.value)) {
    els.uploadDepartment.value = "";
  }
  setUploadMessage("");
}

function closeUploadModal() {
  els.uploadModal.classList.add("hidden");
  setUploadMessage("");
  els.uploadForm.reset();
  els.uploadCandidateName.disabled = false;
}

function redirectToLogin(forceChangePassword = false) {
  const suffix = forceChangePassword ? "?force=1" : "";
  window.location.href = `/login${suffix}`;
}

function updateExperienceInputs(type) {
  const isFresh = type === "应届生";
  els.graduationWrap.classList.toggle("hidden", !isFresh);
  els.workWrap.classList.toggle("hidden", isFresh);
  if (isFresh) {
    els.workYears.value = "";
  } else {
    els.graduationYear.value = "";
  }
}

function renderCurrentUser() {
  const user = state.currentUser;
  if (!user) {
    els.currentUserText.textContent = "未登录";
    els.usersManageLink.classList.add("hidden");
    return;
  }
  const roleCode = roleCodeFromUser(user);
  const roleText = roleLabelFromCode(roleCode);
  els.currentUserText.textContent = `${user.display_name} (@${user.username}) · ${roleText}`;
  els.usersManageLink.classList.toggle("hidden", roleCode !== "administrator");
}

function normalizeRoleCode(value) {
  const text = String(value || "").trim().toLowerCase();
  return ROLE_ORDER.includes(text) ? text : "";
}

function roleCodeFromUser(user) {
  const normalized = normalizeRoleCode(user?.role_code);
  if (normalized) {
    return normalized;
  }
  return Number(user?.is_admin || 0) === 1 ? "administrator" : "hr_specialist";
}

function roleLabelFromCode(roleCode) {
  return ROLE_LABELS[roleCode] || "用户";
}

function activeCandidate() {
  return state.candidates.find((c) => c.candidate_id === state.activeId) || null;
}

function parseDatetimeMs(input) {
  if (!input) {
    return null;
  }
  const normalized = input.includes("T") ? input : input.replace(" ", "T");
  const time = Date.parse(normalized);
  return Number.isNaN(time) ? null : time;
}

function normalizeStageStatuses(profile) {
  const raw = profile?.stage_statuses || {};
  const normalized = {};
  INTERVIEW_STAGES.forEach((stage) => {
    const value = raw[stage];
    if (value === STATUS_PASSED || value === STATUS_ENDED) {
      normalized[stage] = value;
    } else {
      normalized[stage] = STATUS_PENDING;
    }
  });
  return normalized;
}

function currentWorkflowStage(profile, statuses) {
  if (profile?.current_stage && INTERVIEW_STAGES.includes(profile.current_stage)) {
    return profile.current_stage;
  }
  const firstPending = INTERVIEW_STAGES.find((stage) => statuses[stage] === STATUS_PENDING);
  return firstPending || INTERVIEW_STAGES[INTERVIEW_STAGES.length - 1];
}

function failedStatusByStage(stage) {
  if (FAILED_STATUS_BY_STAGE[stage]) {
    return FAILED_STATUS_BY_STAGE[stage];
  }
  return stage ? `未通过${stage}` : "未通过";
}

function isFailedInterviewStatus(status) {
  const text = String(status || "").trim();
  return FAILED_CANDIDATE_STATUSES.has(text) || /^未通过/.test(text);
}

function deriveInterviewStatusFromProfile(profile) {
  const statuses = normalizeStageStatuses(profile);
  const endedFrom = profile?.stage_closed_from;
  if (endedFrom && INTERVIEW_STAGES.includes(endedFrom)) {
    return failedStatusByStage(endedFrom);
  }
  const endedStage = INTERVIEW_STAGES.find((stage) => statuses[stage] === STATUS_ENDED);
  if (endedStage) {
    return failedStatusByStage(endedStage);
  }
  if (INTERVIEW_STAGES.every((stage) => statuses[stage] === STATUS_PASSED)) {
    return "通过";
  }
  const pendingStage = INTERVIEW_STAGES.find((stage) => statuses[stage] === STATUS_PENDING) || INTERVIEW_STAGES[0];
  return CANDIDATE_STATUS_BY_STAGE[pendingStage] || CANDIDATE_STATUS_BY_STAGE[INTERVIEW_STAGES[0]];
}

function stageStatusClass(status) {
  if (status === "待初筛") {
    return "tag-status-wait-screen";
  }
  if (status === "待一面") {
    return "tag-status-wait-1";
  }
  if (status === "待二面") {
    return "tag-status-wait-2";
  }
  if (status === "待HR面") {
    return "tag-status-wait-hr";
  }
  if (status === "通过") {
    return "tag-status-passed";
  }
  if (isFailedInterviewStatus(status)) {
    return "tag-status-failed";
  }
  return "";
}

function compareNearestInterviewTime(a, b) {
  const aTime = parseDatetimeMs(a.nearest_interview_time);
  const bTime = parseDatetimeMs(b.nearest_interview_time);
  if (aTime === null && bTime === null) {
    return 0;
  }
  if (aTime === null) {
    return 1;
  }
  if (bTime === null) {
    return -1;
  }
  return aTime - bTime;
}

function sortNormalCandidates(items) {
  const list = [...items];
  if (state.sortMode === "name") {
    list.sort((a, b) =>
      a.name.localeCompare(b.name, "zh-CN") || Number(b.is_starred || 0) - Number(a.is_starred || 0),
    );
    return list;
  }

  if (state.sortMode === "time") {
    list.sort((a, b) => {
      const timeCmp = compareNearestInterviewTime(a, b);
      if (timeCmp !== 0) {
        return timeCmp;
      }
      const starCmp = Number(b.is_starred || 0) - Number(a.is_starred || 0);
      if (starCmp !== 0) {
        return starCmp;
      }
      return a.name.localeCompare(b.name, "zh-CN");
    });
    return list;
  }

  list.sort((a, b) => {
    const starCmp = Number(b.is_starred || 0) - Number(a.is_starred || 0);
    if (starCmp !== 0) {
      return starCmp;
    }
    const timeCmp = compareNearestInterviewTime(a, b);
    if (timeCmp !== 0) {
      return timeCmp;
    }
    return a.name.localeCompare(b.name, "zh-CN");
  });
  return list;
}

function getVisibleCandidates() {
  const failed = state.candidates.filter((item) => isFailedInterviewStatus(item.interview_status));
  const normal = state.candidates.filter((item) => !isFailedInterviewStatus(item.interview_status));
  const sortedNormal = sortNormalCandidates(normal);
  const sortedFailed = [...failed].sort((a, b) => {
    const aTime = parseDatetimeMs(a.terminated_at) || 0;
    const bTime = parseDatetimeMs(b.terminated_at) || 0;
    return bTime - aTime;
  });

  // When the user actively filters, show every matched record so exact date
  // or keyword searches do not look empty just because the candidate failed.
  if (hasActiveCandidateFilters()) {
    return [...sortedNormal, ...sortedFailed];
  }

  if (!state.showAllCandidates) {
    return sortedNormal;
  }

  return [...sortedNormal, ...sortedFailed];
}

function renderCalendar() {
  els.calendarList.innerHTML = "";
  const items = state.calendarItems || [];
  els.calendarCount.textContent = String(items.length);

  if (items.length === 0) {
    const li = document.createElement("li");
    li.className = "calendar-item empty";
    li.textContent = "暂无面试安排";
    els.calendarList.appendChild(li);
    return;
  }

  items.forEach((item) => {
    const li = document.createElement("li");
    li.className = "calendar-item";
    const displayTime = item.interview_time_display || formatDatetimeDisplay(item.interview_time || "");
    li.textContent = `${item.candidate_name}-${item.stage}-${displayTime}`;
    li.title = li.textContent;
    li.addEventListener("click", () => {
      if (item.candidate_id) {
        selectCandidate(item.candidate_id).catch((err) => {
          setMessage(err.message || "候选人加载失败", "error");
        });
      }
    });
    els.calendarList.appendChild(li);
  });
}

function renderList() {
  const visibleCandidates = getVisibleCandidates();
  els.list.innerHTML = "";

  if (visibleCandidates.length === 0) {
    const li = document.createElement("li");
    li.className = "candidate-empty";
    li.textContent = "暂无可显示候选人";
    els.list.appendChild(li);
  }

  visibleCandidates.forEach((candidate) => {
    const li = document.createElement("li");
    li.className = `candidate-item ${candidate.candidate_id === state.activeId ? "active" : ""}`;
    li.dataset.candidateId = String(candidate.candidate_id || "");

    const stageStatus = candidate.interview_status || CANDIDATE_STATUS_BY_STAGE[INTERVIEW_STAGES[0]];
    const stageClass = stageStatusClass(stageStatus);
    const inflowDisplay = formatDateTag(candidate.inflow_date);
    li.innerHTML = `
      <div class="candidate-title-row">
        <div class="candidate-name">${candidate.name}</div>
        <button type="button" class="star-btn ${Number(candidate.is_starred || 0) ? "on" : ""}">${
          Number(candidate.is_starred || 0) ? "★" : "☆"
        }</button>
      </div>
      <div class="candidate-tags">
        <span class="tag">${candidate.experience_tag || "未知"}</span>
        <span class="tag">${candidate.duration_tag || "未知"}</span>
        <span class="tag">${candidate.education_tag || "未知"}</span>
        <span class="tag">${candidate.school_tag || "未知"}</span>
        <span class="tag tag-inflow">${inflowDisplay || "未知"}</span>
        <span class="tag tag-stage ${stageClass}">${stageStatus}</span>
      </div>
      <div class="candidate-note">${candidate.applied_position_text || "申请岗位:未知"}</div>
    `;

    const starBtn = li.querySelector(".star-btn");
    starBtn.addEventListener("click", async (event) => {
      event.stopPropagation();
      await toggleCandidateStar(candidate);
    });

    li.addEventListener("click", () => {
      selectCandidate(candidate.candidate_id).catch((err) => {
        setMessage(err.message || "加载失败", "error");
      });
    });
    els.list.appendChild(li);
  });

  const hiddenFailed =
    hasActiveCandidateFilters() || state.showAllCandidates === true
      ? 0
      : state.candidates.filter((item) => isFailedInterviewStatus(item.interview_status)).length;

  const totalCount = Number.isFinite(state.candidateTotalCount) ? state.candidateTotalCount : state.candidates.length;
  const filteredCount = Number.isFinite(state.candidateFilteredCount)
    ? state.candidateFilteredCount
    : state.candidates.length;

  if (hasActiveCandidateFilters()) {
    els.count.textContent =
      hiddenFailed > 0
        ? `筛选结果 ${visibleCandidates.length}/${filteredCount} 位（全量 ${totalCount} 位，隐藏未通过 ${hiddenFailed} 位）`
        : `筛选结果 ${visibleCandidates.length}/${filteredCount} 位（全量 ${totalCount} 位）`;
    return;
  }

  els.count.textContent =
    hiddenFailed > 0
      ? `显示 ${visibleCandidates.length}/${filteredCount} 位（隐藏未通过 ${hiddenFailed} 位）`
      : `共 ${visibleCandidates.length} 位候选人`;
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

function normalizeDatetimeLocal(input) {
  if (!input) {
    return "";
  }
  const normalized = input.includes("T") ? input : input.replace(" ", "T");
  return normalized.slice(0, 16);
}

function formatDatetimeDisplay(input) {
  if (!input) {
    return "未定";
  }
  const normalized = input.includes("T") ? input : input.replace(" ", "T");
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) {
    return input;
  }
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDateTag(tag) {
  const text = String(tag || "").trim();
  if (!/^\d{8}$/.test(text)) {
    return text || "未知";
  }
  return `${text.slice(0, 4)}-${text.slice(4, 6)}-${text.slice(6, 8)}`;
}

function autoResizeTextarea(el) {
  el.style.height = "auto";
  el.style.height = `${el.scrollHeight}px`;
}

function stageVisualClass(stage, statuses, profile) {
  const status = statuses[stage];
  const allPassed = INTERVIEW_STAGES.every((s) => statuses[s] === STATUS_PASSED);
  const closed = Boolean(profile?.stage_closed_from);
  const current = currentWorkflowStage(profile || {}, statuses);

  if (status === STATUS_PASSED) {
    return "status-passed";
  }
  if (status === STATUS_ENDED) {
    return "status-ended";
  }
  if (!closed && !allPassed && stage === current) {
    return "status-active";
  }
  return "status-pending";
}

function renderStageAxis() {
  els.stageAxis.innerHTML = "";
  const profile = state.evaluation?.profile || {};
  const rounds = state.evaluation?.rounds || {};
  const statuses = normalizeStageStatuses(profile);
  const closed = Boolean(profile.stage_closed_from);
  const allPassed = INTERVIEW_STAGES.every((stage) => statuses[stage] === STATUS_PASSED);
  const current = currentWorkflowStage(profile, statuses);
  const closedStage = INTERVIEW_STAGES.includes(profile.stage_closed_from) ? profile.stage_closed_from : "";
  const actionStage = closedStage || current || INTERVIEW_STAGES[0];
  const nextLabel =
    actionStage === INTERVIEW_STAGES[INTERVIEW_STAGES.length - 1] ? "通过面试" : "进入下一阶段";
  const endLabel = failedStatusByStage(actionStage);

  INTERVIEW_STAGES.forEach((stage) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `stage-node ${stageVisualClass(stage, statuses, profile)} ${stage === state.viewStage ? "active" : ""}`;
    const stageTime = formatDatetimeDisplay(rounds[stage]?.interview_time || "");
    btn.innerHTML = `
      <span class="stage-node-label">${stage}</span>
      <span class="stage-node-time">${stageTime}</span>
    `;
    btn.addEventListener("click", () => {
      state.viewStage = stage;
      renderStageAxis();
      applyRoundFields();
      setMessage("");
    });
    els.stageAxis.appendChild(btn);
  });

  if (closed) {
    els.currentStageText.textContent = `当前流程：已结束（${failedStatusByStage(closedStage || actionStage)}）`;
  } else if (allPassed) {
    els.currentStageText.textContent = "当前流程：已通过面试";
  } else {
    els.currentStageText.textContent = `当前流程：${current}（进行中）`;
  }

  if (closedStage) {
    els.stageEndedFrom.classList.remove("hidden");
    els.stageEndedFrom.textContent = `结束结果：${failedStatusByStage(closedStage)}`;
  } else {
    els.stageEndedFrom.classList.add("hidden");
    els.stageEndedFrom.textContent = "";
  }

  const hasProgress =
    closed ||
    current !== INTERVIEW_STAGES[0] ||
    INTERVIEW_STAGES.some((stage) => statuses[stage] !== STATUS_PENDING);

  els.stageNextBtn.textContent = nextLabel;
  els.stageEndBtn.textContent = endLabel;
  els.stageNextBtn.disabled = closed || allPassed;
  els.stageEndBtn.disabled = closed || allPassed;
  els.stageResetBtn.disabled = !hasProgress;
}

function applyProfileFields(profile) {
  const candidate = activeCandidate();
  void refreshUploadJobs();
  els.candidateName.value = profile.candidate_name || candidate?.name || "";
  els.baseLocation.value = profile.base_location || "北京";
  if (els.candidateDepartment) {
    els.candidateDepartment.value = normalizeDepartmentScope(profile.department_scope || candidate?.department_scope || "");
  }
  els.appliedPosition.value = profile.applied_position || "";
  renderCandidateJobOptions(profile);
  els.salaryMode.value = profile.salary_mode || "月薪";
  els.salaryRange.value = profile.salary_range || "";
  els.experienceType.value = profile.experience_type || "应届生";
  els.graduationYear.value = profile.graduation_year || "";
  els.workYears.value = profile.work_years || "";
  els.highestEducation.value = profile.highest_education || "未知";
  els.schoolName.value = profile.school_name || "未知";
  els.hireType.value = profile.hire_type || "实习";
  els.presetPosition.value = profile.preset_position || "";
  updateExperienceInputs(els.experienceType.value);
}

function currentRound() {
  if (!state.evaluation || !state.evaluation.rounds) {
    return null;
  }
  return state.evaluation.rounds[state.viewStage] || null;
}

function renderInterviewerOptions(selectedId = "") {
  els.stageInterviewer.innerHTML = "";

  const empty = document.createElement("option");
  empty.value = "";
  empty.textContent = "未指定";
  els.stageInterviewer.appendChild(empty);

  state.interviewerOptions.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.id;
    option.textContent = item.label || item.display_name || item.username;
    els.stageInterviewer.appendChild(option);
  });

  if (selectedId && !state.interviewerOptions.some((item) => item.id === selectedId)) {
    const fallback = document.createElement("option");
    fallback.value = selectedId;
    fallback.textContent = `${selectedId} (已不可用)`;
    els.stageInterviewer.appendChild(fallback);
  }

  els.stageInterviewer.value = selectedId || "";
}

function applyRoundFields() {
  const round = currentRound() || {
    interview_time: "",
    interviewer_user_id: "",
    planned_questions: "",
    interview_review: "",
    updated_at: "",
  };

  const stageNo = INTERVIEW_STAGES.indexOf(state.viewStage) + 1;
  els.roundSectionTitle.textContent = `第${stageNo}阶段的面评信息`;
  els.interviewTime.value = normalizeDatetimeLocal(round.interview_time || "");
  renderInterviewerOptions(round.interviewer_user_id || "");
  els.plannedQuestions.value = round.planned_questions || "";
  els.interviewReview.value = round.interview_review || "";
  autoResizeTextarea(els.plannedQuestions);
  autoResizeTextarea(els.interviewReview);
}

function parseJobSnapshot(item) {
  if (item && item.job_snapshot && typeof item.job_snapshot === "object") {
    return item.job_snapshot;
  }
  const raw = String(item?.profile?.job_snapshot_json || "").trim();
  if (!raw) {
    return {};
  }
  try {
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function renderJobSnapshot(item) {
  if (!els.jobConfigMeta || !els.jobConfigList) {
    return;
  }
  const snapshot = parseJobSnapshot(item);
  const profile = item?.profile || {};
  const jobTitle = String(snapshot.job_title || profile.job_title || "").trim();
  const jobCode = String(snapshot.job_code || profile.job_code || "").trim();
  const scoreItems = Array.isArray(snapshot.score_items) ? snapshot.score_items : [];
  const process = snapshot.process && typeof snapshot.process === "object" ? snapshot.process : {};
  const criteria = snapshot.criteria && typeof snapshot.criteria === "object" ? snapshot.criteria : {};
  const autoEnabled = Boolean(snapshot.auto_score_enabled);

  els.jobConfigList.innerHTML = "";
  if (!jobTitle && !jobCode && scoreItems.length === 0) {
    els.jobConfigMeta.textContent = "未关联岗位配置";
    return;
  }

  const titleText = jobCode ? `${jobTitle || "-"}（${jobCode}）` : jobTitle || "-";
  const activeVersion = snapshot.score_table_version || "v1";
  els.jobConfigMeta.textContent = `岗位：${titleText} · 评分项：${scoreItems.length} · 评分版本：${activeVersion} · 自动评分：${autoEnabled ? "已启用" : "未启用"}`;

  INTERVIEW_STAGES.forEach((stage) => {
    const stageRequirement = String(process[stage] || "").trim();
    if (!stageRequirement) {
      return;
    }
    const li = document.createElement("li");
    li.textContent = `流程-${stage}：${stageRequirement}`;
    els.jobConfigList.appendChild(li);
  });

  const criteriaItems = [
    ["学历", criteria.education],
    ["专业", criteria.major],
    ["技能", criteria.skills],
    ["项目经验", criteria.project_experience],
  ];
  criteriaItems.forEach(([label, value]) => {
    const text = String(value || "").trim();
    if (!text) {
      return;
    }
    const li = document.createElement("li");
    li.textContent = `筛选-${label}：${text}`;
    els.jobConfigList.appendChild(li);
  });

  if (els.jobConfigList.childElementCount === 0) {
    const li = document.createElement("li");
    li.textContent = "已关联岗位，但未配置流程说明或筛选标准。";
    els.jobConfigList.appendChild(li);
  }
}

function parseResumeStructured(profile) {
  if (profile && profile.resume_structured && typeof profile.resume_structured === "object") {
    return profile.resume_structured;
  }
  const raw = String(profile?.resume_structured_json || "").trim();
  if (!raw) {
    return {};
  }
  try {
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function formatResumePeriod(start, end) {
  const startText = String(start || "").trim();
  const endText = String(end || "").trim();
  if (!startText && !endText) {
    return "";
  }
  return `${startText || "?"}-${endText || "?"}`;
}

function buildResumeLines(items, formatter, limit = 8) {
  if (!Array.isArray(items) || items.length === 0) {
    return "";
  }
  return items
    .slice(0, limit)
    .map((item, idx) => formatter(item, idx))
    .filter(Boolean)
    .join("\n");
}

function setExtractFieldValue(element, value) {
  if (!element) {
    return;
  }
  element.value = String(value || "").trim();
}

function renderResumeStructured(profile) {
  if (!els.resumeExtractMeta) {
    return;
  }
  const structured = parseResumeStructured(profile || {});
  const basic = structured.basic && typeof structured.basic === "object" ? structured.basic : {};
  const status = String(profile?.resume_extract_status || "").trim() || "pending";
  const source = String(profile?.resume_extract_source || "").trim() || "-";
  const model = String(profile?.resume_extract_model || "").trim() || "-";
  const updatedAt = String(profile?.resume_extract_updated_at || "").trim();
  const extractError = String(profile?.resume_extract_error || "").trim();
  const updatedText = updatedAt ? new Date(updatedAt).toLocaleString("zh-CN") : "-";
  const errorText = extractError ? ` · 错误：${extractError}` : "";
  els.resumeExtractMeta.textContent = `状态：${status} · 来源：${source} · 模型：${model} · 更新时间：${updatedText}${errorText}`;

  setExtractFieldValue(els.extractPhone, basic.phone || structured.basic_contact_phone || "");
  setExtractFieldValue(els.extractEmail, basic.email || structured.basic_contact_email || "");
  setExtractFieldValue(els.extractLocation, basic.location || profile?.base_location || "");
  setExtractFieldValue(els.extractMajor, basic.major);
  setExtractFieldValue(els.extractSkills, Array.isArray(structured.skills) ? structured.skills.join("\n") : "");
  setExtractFieldValue(
    els.extractCertificates,
    Array.isArray(structured.certificates) ? structured.certificates.join("\n") : "",
  );
  setExtractFieldValue(els.extractSummary, structured.summary || structured.basic_snippet || "");
  setExtractFieldValue(
    els.extractEducation,
    buildResumeLines(structured.education, (item, idx) => {
      const school = String(item?.school || "").trim();
      const degree = String(item?.degree || "").trim();
      const major = String(item?.major || "").trim();
      const period = formatResumePeriod(item?.start, item?.end);
      const summary = String(item?.summary || "").trim();
      const content = [school, degree, major, period, summary].filter(Boolean).join(" · ");
      return content ? `${idx + 1}. ${content}` : "";
    }),
  );
  setExtractFieldValue(
    els.extractWork,
    buildResumeLines(structured.work_experience, (item, idx) => {
      const company = String(item?.company || "").trim();
      const title = String(item?.title || "").trim();
      const period = formatResumePeriod(item?.start, item?.end);
      const summary = String(item?.summary || "").trim();
      const content = [company, title, period, summary].filter(Boolean).join(" · ");
      return content ? `${idx + 1}. ${content}` : "";
    }, 10),
  );
  setExtractFieldValue(
    els.extractProject,
    buildResumeLines(structured.project_experience, (item, idx) => {
      const name = String(item?.name || "").trim();
      const role = String(item?.role || "").trim();
      const period = formatResumePeriod(item?.start, item?.end);
      const summary = String(item?.summary || "").trim();
      const techStack = Array.isArray(item?.tech_stack) ? item.tech_stack.filter(Boolean).join("/") : "";
      const content = [name, role, period, techStack ? `技术栈:${techStack}` : "", summary]
        .filter(Boolean)
        .join(" · ");
      return content ? `${idx + 1}. ${content}` : "";
    }, 12),
  );
  [els.extractSkills, els.extractCertificates, els.extractSummary, els.extractEducation, els.extractWork, els.extractProject]
    .filter(Boolean)
    .forEach((el) => autoResizeTextarea(el));
}

function normalizeAutoScorePayload(rawScore) {
  let score = rawScore;
  if (typeof score === "string") {
    const text = score.trim();
    if (!text) {
      return null;
    }
    try {
      score = JSON.parse(text);
    } catch {
      return null;
    }
  }
  if (!score || typeof score !== "object") {
    return null;
  }

  const overall = score.overall && typeof score.overall === "object" ? score.overall : {};
  const totalScore = Number(score.total_score ?? overall.total_score ?? 0);
  const maxScore = Number(score.max_score ?? overall.max_score ?? 0);
  const summary = String(score.summary || overall.summary || "").trim();
  const matchLevel = String(score.match_level || overall.match_level || "").trim();
  const scoreSource = String(score.score_source || "").trim();
  const scoreStatus = String(score.score_status || "").trim();
  const modelName = String(score.model_name || "").trim();
  const promptId = String(score.prompt_id || "").trim();
  const createdAt = String(score.created_at || "").trim();
  const errorMessage = String(score.error_message || "").trim();

  const rawRiskFlags = Array.isArray(score.risk_flags)
    ? score.risk_flags
    : Array.isArray(overall.risk_flags)
      ? overall.risk_flags
      : [];
  const riskFlags = rawRiskFlags
    .map((item) => String(item || "").trim())
    .filter(Boolean);

  const rawDimensions = Array.isArray(score.dimension_scores)
    ? score.dimension_scores
    : Array.isArray(score.dimensions)
      ? score.dimensions
      : [];
  const normalizedDimensionScores = rawDimensions
    .filter((item) => item && typeof item === "object")
    .map((item) => {
      const name = String(item.dimension_name || item.dimension || item.name || "").trim() || "未命名维度";
      const dimScore = Number(item.dimension_score ?? item.score ?? item.score_value ?? 0);
      const dimMax = Number(item.dimension_max ?? item.max_score ?? item.max ?? 0);
      const items = (Array.isArray(item.items) ? item.items : [])
        .filter((entry) => entry && typeof entry === "object")
        .map((entry) => ({
          name: String(entry.item_name || entry.point || entry.point_name || entry.name || "").trim() || "未命名评分项",
          score: Number(entry.item_score ?? entry.score ?? entry.score_value ?? 0),
          standard: String(entry.selected_standard || entry.criterion || entry.standard || "").trim(),
          reason: String(entry.reason || "").trim(),
          confidence: String(entry.confidence || "").trim(),
          evidence: Array.isArray(entry.evidence)
            ? entry.evidence.map((value) => String(value || "").trim()).filter(Boolean)
            : [],
        }));
      return { name, score: dimScore, max: dimMax, items };
    });
  const dimensionScores = rawDimensions
    .filter((item) => item && typeof item === "object")
    .map((item) => {
      const name = String(item.dimension_name || item.dimension || item.name || "").trim();
      const dimScore = Number(item.dimension_score ?? item.score ?? item.score_value ?? 0);
      const dimMax = Number(item.dimension_max ?? item.max_score ?? item.max ?? 0);
      return { name: name || "未命名维度", score: dimScore, max: dimMax };
    });

  return {
    scoreSource,
    scoreStatus,
    totalScore,
    maxScore,
    summary,
    matchLevel,
    createdAt,
    modelName,
    promptId,
    riskFlags,
    dimensionScores: normalizedDimensionScores,
    errorMessage,
  };
}

function renderAutoScore(score) {
  if (!els.aiScoreMeta || !els.aiScoreSummary || !els.aiScoreRiskList || !els.aiScoreDimensionList) {
    return;
  }
  els.aiScoreRiskList.innerHTML = "";
  els.aiScoreDimensionList.innerHTML = "";
  const normalizedScore = normalizeAutoScorePayload(score);
  if (!normalizedScore) {
    els.aiScoreMeta.textContent = "暂无自动评分结果";
    els.aiScoreSummary.textContent = "";
    return;
  }

  const scoreSource = normalizedScore.scoreSource === "llm" ? "LLM" : normalizedScore.scoreSource || "规则降级";
  const scoreStatus = normalizedScore.scoreStatus || "success";
  const createdAt = normalizedScore.createdAt ? new Date(normalizedScore.createdAt).toLocaleString("zh-CN") : "-";
  const modelName = normalizedScore.modelName || "-";
  const promptId = normalizedScore.promptId || "-";
  const matchLevel = normalizedScore.matchLevel || "待定";
  els.aiScoreMeta.textContent =
    `来源：${scoreSource} · 状态：${scoreStatus} · 总分：${normalizedScore.totalScore || 0}/${normalizedScore.maxScore || 0} · 结论：${matchLevel} · 时间：${createdAt} · 模型：${modelName} · Prompt：${promptId}`;
  els.aiScoreSummary.textContent = normalizedScore.summary || "";

  normalizedScore.riskFlags.forEach((flag) => {
    const li = document.createElement("li");
    li.textContent = `风险：${flag}`;
    els.aiScoreRiskList.appendChild(li);
  });

  normalizedScore.dimensionScores.slice(0, 8).forEach((dim) => {
    const li = document.createElement("li");
    li.textContent = `${dim.name}：${dim.score}/${dim.max}`;
    els.aiScoreDimensionList.appendChild(li);
  });

  els.aiScoreDimensionList.innerHTML = "";
  normalizedScore.dimensionScores.forEach((dim) => {
    const li = document.createElement("li");
    li.className = "ai-score-dimension-item";

    const details = document.createElement("details");
    details.className = "ai-score-dimension-dropdown";

    const title = document.createElement("summary");
    title.className = "ai-score-dimension-title";
    title.textContent = `${dim.name}：${dim.score}/${dim.max}`;
    details.appendChild(title);

    if (Array.isArray(dim.items) && dim.items.length > 0) {
      const itemList = document.createElement("ul");
      itemList.className = "ai-score-item-list";
      dim.items.forEach((entry) => {
        const item = document.createElement("li");
        item.className = "ai-score-item";

        const header = document.createElement("div");
        header.className = "ai-score-item-header";
        header.textContent = `${entry.name}：${entry.score}`;
        item.appendChild(header);

        if (entry.standard) {
          const standard = document.createElement("div");
          standard.className = "ai-score-item-detail";
          standard.textContent = `判定标准：${entry.standard}`;
          item.appendChild(standard);
        }
        if (entry.reason) {
          const reason = document.createElement("div");
          reason.className = "ai-score-item-detail";
          reason.textContent = `判定理由：${entry.reason}`;
          item.appendChild(reason);
        }
        if (Array.isArray(entry.evidence) && entry.evidence.length > 0) {
          const evidence = document.createElement("div");
          evidence.className = "ai-score-item-detail";
          evidence.textContent = `命中证据：${entry.evidence.join("；")}`;
          item.appendChild(evidence);
        }
        if (entry.confidence) {
          const confidence = document.createElement("div");
          confidence.className = "ai-score-item-detail";
          confidence.textContent = `置信度：${entry.confidence}`;
          item.appendChild(confidence);
        }

        itemList.appendChild(item);
      });
      details.appendChild(itemList);
    } else {
      const emptyText = document.createElement("div");
      emptyText.className = "ai-score-item-detail ai-score-item-empty";
      emptyText.textContent = "暂无评分项明细";
      details.appendChild(emptyText);
    }

    li.appendChild(details);
    els.aiScoreDimensionList.appendChild(li);
  });

  if (normalizedScore.dimensionScores.length === 0 && normalizedScore.riskFlags.length === 0) {
    const li = document.createElement("li");
    li.textContent = "说明：自动评分已返回，但未提供维度明细";
    els.aiScoreRiskList.appendChild(li);
  }

  if (normalizedScore.errorMessage) {
    const li = document.createElement("li");
    li.textContent = `说明：已使用规则评分兜底，LLM错误：${normalizedScore.errorMessage}`;
    els.aiScoreRiskList.appendChild(li);
  }
}

function applyEvaluation(item, preserveViewStage = false) {
  state.evaluation = item;
  const snapshot = parseJobSnapshot(item);
  const snapshotJobId = normalizeJobId(snapshot?.job_id || item?.profile?.job_id || "");
  if (snapshotJobId && snapshot && typeof snapshot === "object" && Object.keys(snapshot).length > 0) {
    state.jobSnapshotsById[snapshotJobId] = snapshot;
  }
  applyProfileFields(item.profile || {});

  const statuses = normalizeStageStatuses(item.profile || {});
  const workflowStage = currentWorkflowStage(item.profile || {}, statuses);
  if (!preserveViewStage || !INTERVIEW_STAGES.includes(state.viewStage)) {
    state.viewStage = workflowStage;
  }

  renderStageAxis();
  applyRoundFields();
  renderJobSnapshot(item);
  renderResumeStructured(item.profile || {});
  renderAutoScore(item.auto_score || item.profile?.auto_score || null);

  const updated = item.profile?.updated_at
    ? `最近保存：${new Date(item.profile.updated_at).toLocaleString("zh-CN")}`
    : "未保存";
  els.hint.textContent = updated;
}

function syncCandidateListFromProfile() {
  const profile = state.evaluation?.profile;
  const candidate = activeCandidate();
  if (!profile || !candidate) {
    return;
  }

  candidate.name = profile.candidate_name || candidate.name || "未命名候选人";
  candidate.experience_tag = profile.experience_type || "未知";
  candidate.duration_tag =
    profile.experience_type === "应届生"
      ? profile.graduation_year
        ? `${profile.graduation_year}毕业`
        : "未知"
      : profile.work_years || "未知";
  candidate.education_tag = profile.highest_education || "未知";
  candidate.school_tag = profile.school_name || "未知";
  candidate.interview_status = deriveInterviewStatusFromProfile(profile);
  candidate.stage_tag = candidate.interview_status;
  candidate.department_scope = normalizeDepartmentScope(profile.department_scope || candidate.department_scope || "");
  candidate.job_id = profile.job_id || candidate.job_id || "";
  candidate.job_code = profile.job_code || candidate.job_code || "";
  candidate.job_title = profile.job_title || candidate.job_title || "";
  const jobText = candidate.job_title
    ? candidate.job_code
      ? `${candidate.job_title}（${candidate.job_code}）`
      : candidate.job_title
    : profile.applied_position || "未知";
  candidate.applied_position_text = `申请岗位:${jobText}`;
  candidate.is_starred = Number(profile.is_starred || 0);
  candidate.terminated_at = profile.terminated_at || "";
  if (candidate.candidate_id === state.activeId) {
    els.activeCandidate.textContent = candidate.name;
    const departmentText = normalizeDepartmentScope(candidate.department_scope) || "未分配部门";
    els.activeMeta.textContent = `文件：${candidate.filename || "-"} · 流入日：${formatDateTag(candidate.inflow_date)} · 部门：${departmentText} · 岗位：${jobText}`;
  }
}

function buildProfilePayload() {
  const payload = {
    candidate_name: els.candidateName.value.trim(),
    base_location: els.baseLocation.value,
    department_scope: normalizeDepartmentScope(els.candidateDepartment?.value || ""),
    applied_position: els.appliedPosition.value.trim(),
    salary_mode: els.salaryMode.value,
    salary_range: els.salaryRange.value.trim(),
    experience_type: els.experienceType.value,
    graduation_year: els.graduationYear.value.trim(),
    work_years: els.workYears.value.trim(),
    highest_education: els.highestEducation.value,
    school_name: els.schoolName.value.trim(),
    hire_type: els.hireType.value,
    preset_position: els.presetPosition.value.trim(),
  };
  const linkedJob = selectedCandidateJob();
  if (linkedJob) {
    payload.job_id = linkedJob.job_id;
    payload.job_code = linkedJob.job_code || "";
    payload.job_title = linkedJob.title || "";
    payload.job_payload = buildUploadJobPayload(linkedJob);
    return payload;
  }

  const selectedJobId = normalizeJobId(els.candidateJob?.value || "");
  const profile = state.evaluation?.profile || {};
  if (selectedJobId && selectedJobId === normalizeJobId(profile.job_id || "")) {
    payload.job_id = selectedJobId;
    payload.job_code = String(profile.job_code || "").trim();
    payload.job_title = String(profile.job_title || "").trim();
    payload.job_payload = parseJobSnapshot(state.evaluation);
  }
  return payload;
}

function buildRoundPayload() {
  return {
    stage: state.viewStage,
    interview_time: els.interviewTime.value.trim(),
    interviewer_user_id: els.stageInterviewer.value,
    planned_questions: els.plannedQuestions.value.trim(),
    interview_review: els.interviewReview.value.trim(),
  };
}

async function selectCandidate(candidateId) {
  if (!candidateId) {
    return;
  }

  const candidate = state.candidates.find((c) => c.candidate_id === candidateId);
  if (!candidate) {
    return;
  }

  state.activeId = candidateId;
  persistActiveCandidateSelection(candidateId);
  renderList();
  scrollActiveCandidateIntoView();

  els.activeCandidate.textContent = candidate.name;
  const departmentText = normalizeDepartmentScope(candidate.department_scope) || "未分配部门";
  const jobText = candidate.job_title
    ? candidate.job_code
      ? `${candidate.job_title}（${candidate.job_code}）`
      : candidate.job_title
    : candidate.applied_position || "未知";
  els.activeMeta.textContent = `文件：${candidate.filename} · 流入日：${formatDateTag(candidate.inflow_date)} · 部门：${departmentText} · 岗位：${jobText}`;
  els.frame.src = candidate.pdf_url;
  setMessage("");

  const data = await fetchJSON(`/api/evaluations/${encodeURIComponent(candidateId)}`);
  applyEvaluation(data.item);
}

async function toggleCandidateStar(candidate) {
  if (!candidate?.candidate_id) {
    return;
  }

  const nextStarred = Number(candidate.is_starred || 0) ? 0 : 1;
  try {
    const data = await fetchJSON(`/api/evaluations/${encodeURIComponent(candidate.candidate_id)}/star`, {
      method: "PUT",
      body: JSON.stringify({ is_starred: nextStarred }),
    });

    if (candidate.candidate_id === state.activeId) {
      applyEvaluation(data.item, true);
      syncCandidateListFromProfile();
    } else {
      candidate.is_starred = nextStarred;
    }
    renderList();
    setMessage(nextStarred ? "已加星标" : "已取消星标", "success");
  } catch (err) {
    if (err.status === 401) {
      redirectToLogin(false);
      return;
    }
    if (err.status === 403 && err.code === "must_change_password") {
      redirectToLogin(true);
      return;
    }
    setMessage(err.message || "星标保存失败", "error");
  }
}

async function reloadCalendar() {
  const data = await fetchJSON("/api/interview-calendar");
  state.calendarItems = data.items || [];
  renderCalendar();
}

async function runStageAction(action) {
  if (!state.activeId) {
    return;
  }

  const profile = state.evaluation?.profile || {};
  const statuses = normalizeStageStatuses(profile);
  const activeStage = currentWorkflowStage(profile, statuses) || INTERVIEW_STAGES[0];

  const successMap = {
    next: activeStage === INTERVIEW_STAGES[INTERVIEW_STAGES.length - 1] ? "已通过面试" : "已进入下一阶段",
    end: `已标记${failedStatusByStage(activeStage)}`,
    reset: "已重置阶段状态",
  };

  try {
    const data = await fetchJSON(`/api/evaluations/${encodeURIComponent(state.activeId)}/stage`, {
      method: "POST",
      body: JSON.stringify({ action }),
    });
    applyEvaluation(data.item);
    syncCandidateListFromProfile();
    const switched = await reconcileActiveCandidateSelection();
    if (!switched) {
      renderList();
    }
    setMessage(successMap[action] || "阶段状态已更新", "success");
  } catch (err) {
    if (err.status === 403 && err.code === "must_change_password") {
      redirectToLogin(true);
      return;
    }
    setMessage(err.message || "阶段流转失败", "error");
  }
}

async function saveRound() {
  if (!state.activeId) {
    return;
  }

  try {
    const data = await fetchJSON(`/api/evaluations/${encodeURIComponent(state.activeId)}/round`, {
      method: "PUT",
      body: JSON.stringify(buildRoundPayload()),
    });
    applyEvaluation(data.item, true);
    syncCandidateListFromProfile();
    renderList();
    await reloadCalendar();
    setMessage("面评信息已保存", "success");
  } catch (err) {
    if (err.status === 403 && err.code === "must_change_password") {
      redirectToLogin(true);
      return;
    }
    setMessage(err.message || "面评信息保存失败", "error");
  }
}

async function saveProfile() {
  if (!state.activeId) {
    return;
  }

  const payload = buildProfilePayload();
  if (!payload.candidate_name) {
    setMessage("候选人名称不能为空", "error");
    return;
  }
  if (payload.salary_range && !payload.salary_range.includes("-")) {
    setMessage("薪资区间需为区间值，例如 30k-40k", "error");
    return;
  }
  if (payload.job_id && !payload.job_title) {
    setMessage("请选择有效的关联岗位", "error");
    return;
  }

  try {
    const data = await fetchJSON(`/api/evaluations/${encodeURIComponent(state.activeId)}/profile`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    applyEvaluation(data.item, true);
    syncCandidateListFromProfile();
    renderList();
    await reloadCalendar();
    setMessage("通用信息已保存", "success");
  } catch (err) {
    if (err.status === 403 && err.code === "must_change_password") {
      redirectToLogin(true);
      return;
    }
    setMessage(err.message || "通用信息保存失败", "error");
  }
}

async function deleteActiveCandidate() {
  if (!state.activeId) {
    return;
  }
  const candidate = activeCandidate();
  const displayName = candidate?.name || "该候选人";
  const confirmed = window.confirm(`确认删除 ${displayName}？该操作会删除候选人信息和本地 PDF，且不可恢复。`);
  if (!confirmed) {
    return;
  }

  const deletingId = state.activeId;
  try {
    await fetchJSON(`/api/candidates/${encodeURIComponent(deletingId)}`, {
      method: "DELETE",
    });
    state.activeId = null;
    await loadCandidates();
    setMessage("候选人已删除", "success");
  } catch (err) {
    if (err.status === 401) {
      redirectToLogin(false);
      return;
    }
    if (err.status === 403 && err.code === "must_change_password") {
      redirectToLogin(true);
      return;
    }
    setMessage(err.message || "候选人删除失败", "error");
  }
}

async function uploadResume(event) {
  event.preventDefault();
  setUploadMessage("");

  const files = Array.from(els.uploadFile.files || []);
  if (files.length === 0) {
    setUploadMessage("请选择至少一个 PDF 文件", "error");
    return;
  }
  const candidateName = els.uploadCandidateName.value.trim();
  const applyCandidateName = files.length === 1 && candidateName;
  const createdIds = [];
  let successCount = 0;
  const failed = [];

  els.uploadSubmitBtn.disabled = true;
  try {
    for (const file of files) {
      if (!String(file.name || "").toLowerCase().endsWith(".pdf")) {
        failed.push({ name: file.name || "未命名文件", reason: "仅支持上传 PDF 文件" });
        continue;
      }

      const formData = new FormData();
      formData.append("file", file);
      if (applyCandidateName) {
        formData.append("candidate_name", candidateName);
      }

      try {
        const data = await fetchJSON("/api/resumes/upload", {
          method: "POST",
          body: formData,
        });
        successCount += 1;
        const createdId = data.item?.candidate_id || "";
        if (createdId) {
          createdIds.push(createdId);
        }
      } catch (err) {
        if (err.status === 401) {
          redirectToLogin(false);
          return;
        }
        if (err.status === 403 && err.code === "must_change_password") {
          redirectToLogin(true);
          return;
        }
        failed.push({ name: file.name || "未命名文件", reason: err.message || "上传失败" });
      }
    }
  } catch (err) {
    if (err.status === 401) {
      redirectToLogin(false);
      return;
    }
    if (err.status === 403 && err.code === "must_change_password") {
      redirectToLogin(true);
      return;
    }
    setUploadMessage(err.message || "上传失败", "error");
  } finally {
    els.uploadSubmitBtn.disabled = false;
  }

  const failedCount = failed.length;
  const summary = `批量上传完成：成功 ${successCount}，失败 ${failedCount}`;
  if (successCount > 0) {
    closeUploadModal();
    await loadCandidates(createdIds[0] || null);
    if (failedCount === 0) {
      setMessage(summary, "success");
      return;
    }
    const failPreview = failed
      .slice(0, 3)
      .map((item) => `${item.name}(${item.reason})`)
      .join("；");
    const overflow = failedCount > 3 ? `；其余 ${failedCount - 3} 份失败` : "";
    setMessage(`${summary}。失败示例：${failPreview}${overflow}`, "error");
    return;
  }

  const allFailedPreview = failed
    .slice(0, 3)
    .map((item) => `${item.name}(${item.reason})`)
    .join("；");
  const overflow = failedCount > 3 ? `；其余 ${failedCount - 3} 份失败` : "";
  setUploadMessage(`${summary}。${allFailedPreview}${overflow}`, "error");
}

async function syncResumes() {
  const preferredCandidateId = state.activeId;
  els.syncResumesBtn.disabled = true;
  try {
    const data = await fetchJSON("/api/resumes/sync", { method: "POST" });
    await loadCandidates(preferredCandidateId);
    const item = data.item || {};
    const addedCount = Number(item.added_count || 0);
    const scannedCount = Number(item.scanned_pdf_count || 0);
    setMessage(`同步完成：新增 ${addedCount} 份，扫描 ${scannedCount} 份 PDF`, "success");
  } catch (err) {
    if (err.status === 401) {
      redirectToLogin(false);
      return;
    }
    if (err.status === 403 && err.code === "must_change_password") {
      redirectToLogin(true);
      return;
    }
    setMessage(err.message || "目录同步失败", "error");
  } finally {
    els.syncResumesBtn.disabled = false;
  }
}

function clearWorkspaceForEmptyList() {
  clearActiveCandidateSelection();
  els.activeCandidate.textContent = "暂无候选人";
  els.activeMeta.textContent = "";
  els.frame.src = "about:blank";
  renderJobSnapshot(null);
  renderResumeStructured(null);
  renderAutoScore(null);
  els.hint.textContent = "未保存";
  setMessage("");
}

async function reconcileActiveCandidateSelection() {
  const visibleCandidates = getVisibleCandidates();
  if (visibleCandidates.length === 0) {
    state.activeId = null;
    clearActiveCandidateSelection();
    renderList();
    clearWorkspaceForEmptyList();
    return true;
  }

  if (state.activeId && visibleCandidates.some((item) => item.candidate_id === state.activeId)) {
    return false;
  }

  state.activeId = visibleCandidates[0].candidate_id;
  renderList();
  await selectCandidate(state.activeId);
  return true;
}

function clearCandidateReloadTimer() {
  if (state.candidateReloadTimer) {
    window.clearTimeout(state.candidateReloadTimer);
    state.candidateReloadTimer = null;
  }
}

function handleCandidateReloadError(err) {
  if (err.status === 401) {
    redirectToLogin(false);
    return;
  }
  if (err.status === 403 && err.code === "must_change_password") {
    redirectToLogin(true);
    return;
  }
  setMessage(err.message || "候选人列表加载失败", "error");
}

function triggerCandidateFilterReload() {
  clearCandidateReloadTimer();
  state.candidateReloadTimer = window.setTimeout(async () => {
    state.candidateReloadTimer = null;
    try {
      await loadCandidates(state.activeId);
    } catch (err) {
      handleCandidateReloadError(err);
    }
  }, FILTER_DEBOUNCE_MS);
}

async function loadCandidates(preferredCandidateId = null) {
  const requestSeq = ++state.candidateFetchSeq;
  const candidateUrl = buildCandidatesApiURL();
  const [candidateData, calendarData] = await Promise.all([
    fetchJSON(candidateUrl),
    fetchJSON("/api/interview-calendar"),
  ]);
  updateUploadDateSelect(candidateData.upload_dates || []);
  if (requestSeq !== state.candidateFetchSeq) {
    return;
  }

  state.candidates = candidateData.items || [];
  state.candidateTotalCount = Number(candidateData.total_count ?? state.candidates.length);
  state.candidateFilteredCount = Number(candidateData.filtered_count ?? state.candidates.length);
  state.calendarItems = calendarData.items || [];
  await refreshUploadJobs();

  renderCalendar();

  const restoredCandidateId = preferredCandidateId ? "" : loadLastActiveCandidateId();

  if (preferredCandidateId && state.candidates.some((item) => item.candidate_id === preferredCandidateId)) {
    state.activeId = preferredCandidateId;
  } else if (restoredCandidateId && state.candidates.some((item) => item.candidate_id === restoredCandidateId)) {
    state.activeId = restoredCandidateId;
  }

  const visibleCandidates = getVisibleCandidates();
  if (!state.activeId && visibleCandidates.length > 0) {
    state.activeId = visibleCandidates[0].candidate_id;
  }
  if (state.activeId && !visibleCandidates.some((item) => item.candidate_id === state.activeId)) {
    state.activeId = visibleCandidates.length > 0 ? visibleCandidates[0].candidate_id : null;
  }

  renderList();

  if (state.activeId) {
    await selectCandidate(state.activeId);
  } else {
    clearActiveCandidateSelection();
    clearWorkspaceForEmptyList();
  }
}

async function ensureAuthenticated() {
  try {
    const data = await fetchJSON("/api/auth/me");
    state.currentUser = data.item || null;
    renderCurrentUser();
    if (state.currentUser && Number(state.currentUser.must_change_password || 0) === 1) {
      redirectToLogin(true);
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

async function loadInterviewerOptions() {
  const data = await fetchJSON("/api/users/options");
  state.interviewerOptions = data.items || [];
}

async function logout() {
  try {
    await fetchJSON("/api/auth/logout", { method: "POST" });
  } catch {
    // ignore
  }
  redirectToLogin(false);
}

function updateCandidateFiltersFromInputs() {
  state.candidateFilters = readCandidateFiltersFromInputs();
}

function resetCandidateFilters() {
  state.candidateFilters = {
    name: "",
    position: "",
    positionMatch: "fuzzy",
    department: "",
    uploadFrom: "",
    uploadTo: "",
    stageStatus: "",
    uploadDate: "",
  };
  syncCandidateFilterInputs();
}

function roleLabelFromCode(roleCode) {
  return ROLE_LABELS[roleCode] || "用户";
}

function syncDepartmentFilterVisibility() {
  if (!els.filterDepartmentWrap || !els.filterDepartment) {
    return;
  }
  const roleCode = roleCodeFromUser(state.currentUser);
  const shouldHide = roleCode === "hiring_manager";
  els.filterDepartmentWrap.classList.toggle("hidden", shouldHide);
  if (shouldHide && state.candidateFilters.department) {
    state.candidateFilters.department = "";
    syncCandidateFilterInputs();
  }
}

function renderCurrentUser() {
  const user = state.currentUser;
  if (!user) {
    els.currentUserText.textContent = "未登录";
    if (els.jobsManageLink) {
      els.jobsManageLink.classList.add("hidden");
    }
    if (els.operationsManageLink) {
      els.operationsManageLink.classList.add("hidden");
    }
    els.usersManageLink.classList.add("hidden");
    if (els.triggerAutoScoreBtn) {
      els.triggerAutoScoreBtn.classList.add("hidden");
      els.triggerAutoScoreBtn.disabled = true;
    }
    if (els.triggerResumeExtractBtn) {
      els.triggerResumeExtractBtn.classList.add("hidden");
      els.triggerResumeExtractBtn.disabled = true;
    }
    return;
  }
  const roleCode = roleCodeFromUser(user);
  const roleText = roleLabelFromCode(roleCode);
  els.currentUserText.textContent = `${user.display_name} (@${user.username}) · ${roleText}`;
  const canManageJobs = roleCode === "administrator" || roleCode === "hr_specialist" || roleCode === "hiring_manager";
  const canViewOperationLogs = roleCode === "administrator";
  const canTriggerAutoScore = roleCode === "administrator" || roleCode === "hr_specialist";
  if (els.jobsManageLink) {
    els.jobsManageLink.classList.toggle("hidden", !canManageJobs);
  }
  if (els.operationsManageLink) {
    els.operationsManageLink.classList.toggle("hidden", !canViewOperationLogs);
  }
  els.usersManageLink.classList.toggle("hidden", roleCode !== "administrator");
  if (els.triggerAutoScoreBtn) {
    els.triggerAutoScoreBtn.classList.toggle("hidden", !canTriggerAutoScore);
    els.triggerAutoScoreBtn.disabled = !canTriggerAutoScore;
  }
  if (els.triggerResumeExtractBtn) {
    els.triggerResumeExtractBtn.classList.toggle("hidden", !canTriggerAutoScore);
    els.triggerResumeExtractBtn.disabled = !canTriggerAutoScore;
  }
  syncDepartmentFilterVisibility();
}

async function triggerAutoScore() {
  if (!state.activeId) {
    setMessage("请先选择候选人", "error");
    return;
  }
  if (!els.triggerAutoScoreBtn) {
    return;
  }
  els.triggerAutoScoreBtn.disabled = true;
  try {
    const data = await fetchJSON(`/api/evaluations/${encodeURIComponent(state.activeId)}/auto-score`, {
      method: "POST",
    });
    applyEvaluation(data.item, true);
    syncCandidateListFromProfile();
    renderList();
    setMessage("已触发自动评分并更新结果", "success");
  } catch (err) {
    if (err.status === 401) {
      redirectToLogin(false);
      return;
    }
    if (err.status === 403 && err.code === "must_change_password") {
      redirectToLogin(true);
      return;
    }
    setMessage(err.message || "触发自动评分失败", "error");
  } finally {
    const roleCode = roleCodeFromUser(state.currentUser);
    els.triggerAutoScoreBtn.disabled = !(roleCode === "administrator" || roleCode === "hr_specialist");
  }
}

async function triggerResumeExtract() {
  if (!state.activeId) {
    setMessage("请先选择候选人", "error");
    return;
  }
  if (!els.triggerResumeExtractBtn) {
    return;
  }
  els.triggerResumeExtractBtn.disabled = true;
  try {
    const data = await fetchJSON(`/api/evaluations/${encodeURIComponent(state.activeId)}/resume-extract`, {
      method: "POST",
    });
    applyEvaluation(data.item, true);
    syncCandidateListFromProfile();
    renderList();
    setMessage("已更新简历结构化抽取结果", "success");
  } catch (err) {
    if (err.status === 401) {
      redirectToLogin(false);
      return;
    }
    if (err.status === 403 && err.code === "must_change_password") {
      redirectToLogin(true);
      return;
    }
    setMessage(err.message || "更新结构化抽取失败", "error");
  } finally {
    const roleCode = roleCodeFromUser(state.currentUser);
    els.triggerResumeExtractBtn.disabled = !(roleCode === "administrator" || roleCode === "hr_specialist");
  }
}

async function uploadResume(event) {
  event.preventDefault();
  setUploadMessage("");

  const files = Array.from(els.uploadFile.files || []);
  if (files.length === 0) {
    setUploadMessage("请选择至少一个 PDF 文件", "error");
    return;
  }
  const linkedJob = selectedUploadJob();
  if (!linkedJob) {
    setUploadMessage("请选择关联岗位", "error");
    return;
  }
  const jobPayload = buildUploadJobPayload(linkedJob);
  const candidateName = els.uploadCandidateName.value.trim();
  const departmentScope = normalizeDepartmentScope(els.uploadDepartment?.value || linkedJob.department);
  if (!departmentScope) {
    setUploadMessage(`请选择部门：${DEPARTMENT_SCOPES.join(" / ")}`, "error");
    return;
  }

  const applyCandidateName = files.length === 1 && candidateName;
  const createdIds = [];
  let successCount = 0;
  const failed = [];

  els.uploadSubmitBtn.disabled = true;
  try {
    for (const file of files) {
      if (!String(file.name || "").toLowerCase().endsWith(".pdf")) {
        failed.push({ name: file.name || "未命名文件", reason: "仅支持上传 PDF 文件" });
        continue;
      }

      const formData = new FormData();
      formData.append("file", file);
      formData.append("department_scope", departmentScope);
      formData.append("job_id", linkedJob.job_id);
      formData.append("job_code", linkedJob.job_code || "");
      formData.append("job_title", linkedJob.title);
      formData.append("job_payload", JSON.stringify(jobPayload));
      if (applyCandidateName) {
        formData.append("candidate_name", candidateName);
      }

      try {
        const data = await fetchJSON("/api/resumes/upload", {
          method: "POST",
          body: formData,
        });
        successCount += 1;
        const created = data.item || {};
        const createdId = created.candidate_id || "";
        if (createdId) {
          createdIds.push(createdId);
        }
      } catch (err) {
        if (err.status === 401) {
          redirectToLogin(false);
          return;
        }
        if (err.status === 403 && err.code === "must_change_password") {
          redirectToLogin(true);
          return;
        }
        failed.push({ name: file.name || "未命名文件", reason: err.message || "上传失败" });
      }
    }
  } catch (err) {
    if (err.status === 401) {
      redirectToLogin(false);
      return;
    }
    if (err.status === 403 && err.code === "must_change_password") {
      redirectToLogin(true);
      return;
    }
    setUploadMessage(err.message || "上传失败", "error");
  } finally {
    els.uploadSubmitBtn.disabled = false;
  }

  const failedCount = failed.length;
  const summary = `批量上传完成：成功 ${successCount}，失败 ${failedCount}`;
  const asyncNote = "结构化抽取与自动评分在后台任务中生成，可在候选人详情页或手动触发 `/auto-score`、`/resume-extract` 后查看";
  if (successCount > 0) {
    closeUploadModal();
    await loadCandidates(createdIds[0] || null);
    if (failedCount === 0) {
      setMessage(`${summary}。${asyncNote}`, "success");
      return;
    }
    const failPreview = failed
      .slice(0, 3)
      .map((item) => `${item.name}(${item.reason})`)
      .join("；");
    const overflow = failedCount > 3 ? `；其余 ${failedCount - 3} 份失败` : "";
    setMessage(`${summary}。失败示例：${failPreview}${overflow}。${asyncNote}`, "error");
    return;
  }

  const allFailedPreview = failed
    .slice(0, 3)
    .map((item) => `${item.name}(${item.reason})`)
    .join("；");
  const overflow = failedCount > 3 ? `；其余 ${failedCount - 3} 份失败` : "";
  setUploadMessage(`${summary}。${allFailedPreview}${overflow}。${asyncNote}`, "error");
}

els.form.addEventListener("submit", (event) => {
  event.preventDefault();
});

els.experienceType.addEventListener("change", (e) => {
  updateExperienceInputs(e.target.value);
});

els.plannedQuestions.addEventListener("input", () => autoResizeTextarea(els.plannedQuestions));
els.interviewReview.addEventListener("input", () => autoResizeTextarea(els.interviewReview));

els.stageNextBtn.addEventListener("click", () => runStageAction("next"));
els.stageEndBtn.addEventListener("click", () => runStageAction("end"));
els.stageResetBtn.addEventListener("click", () => runStageAction("reset"));
if (els.triggerAutoScoreBtn) {
  els.triggerAutoScoreBtn.addEventListener("click", triggerAutoScore);
}
if (els.triggerResumeExtractBtn) {
  els.triggerResumeExtractBtn.addEventListener("click", triggerResumeExtract);
}
els.saveRoundBtn.addEventListener("click", saveRound);
els.saveProfileBtn.addEventListener("click", saveProfile);
els.deleteCandidateBtn.addEventListener("click", deleteActiveCandidate);
els.logoutBtn.addEventListener("click", logout);
els.uploadResumeBtn.addEventListener("click", openUploadModal);
els.syncResumesBtn.addEventListener("click", syncResumes);
els.uploadCancelBtn.addEventListener("click", closeUploadModal);
els.uploadForm.addEventListener("submit", uploadResume);
els.uploadFile.addEventListener("change", () => {
  const files = Array.from(els.uploadFile.files || []);
  if (files.length === 0) {
    els.uploadCandidateName.disabled = false;
    return;
  }
  if (files.length === 1) {
    els.uploadCandidateName.disabled = false;
    if (!els.uploadCandidateName.value.trim()) {
      els.uploadCandidateName.value = suggestedNameFromFilename(files[0].name);
    }
    return;
  }
  els.uploadCandidateName.value = "";
  els.uploadCandidateName.disabled = true;
});
els.uploadModal.addEventListener("click", (event) => {
  if (event.target === els.uploadModal) {
    closeUploadModal();
  }
});
if (els.uploadJob) {
  els.uploadJob.addEventListener("change", () => {
    const linkedJob = selectedUploadJob();
    if (!linkedJob || !els.uploadDepartment) {
      return;
    }
    const department = normalizeDepartmentScope(linkedJob.department);
    if (department) {
      els.uploadDepartment.value = department;
    }
  });
}
if (els.candidateJob) {
  els.candidateJob.addEventListener("change", () => {
    const linkedJob = selectedCandidateJob();
    if (!linkedJob) {
      return;
    }
    if (!els.appliedPosition.value.trim()) {
      els.appliedPosition.value = linkedJob.title || "";
    }
    if (!els.presetPosition.value.trim()) {
      els.presetPosition.value = linkedJob.title || "";
    }
    const department = normalizeDepartmentScope(linkedJob.department);
    if (department && els.candidateDepartment && !normalizeDepartmentScope(els.candidateDepartment.value)) {
      els.candidateDepartment.value = department;
    }
  });
}
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !els.uploadModal.classList.contains("hidden")) {
    closeUploadModal();
  }
});

els.filterName.addEventListener("input", () => {
  updateCandidateFiltersFromInputs();
  triggerCandidateFilterReload();
});

els.filterPosition.addEventListener("input", () => {
  updateCandidateFiltersFromInputs();
  triggerCandidateFilterReload();
});

els.filterPositionMatch.addEventListener("change", () => {
  updateCandidateFiltersFromInputs();
  triggerCandidateFilterReload();
});

if (els.filterDepartment) {
  els.filterDepartment.addEventListener("change", () => {
    updateCandidateFiltersFromInputs();
    triggerCandidateFilterReload();
  });
}

if (els.filterStageStatus) {
  els.filterStageStatus.addEventListener("change", () => {
    updateCandidateFiltersFromInputs();
    triggerCandidateFilterReload();
  });
}

if (els.filterUploadFrom) {
  els.filterUploadFrom.addEventListener("change", () => {
    updateCandidateFiltersFromInputs();
    triggerCandidateFilterReload();
  });
}

if (els.filterUploadTo) {
  els.filterUploadTo.addEventListener("change", () => {
    updateCandidateFiltersFromInputs();
    triggerCandidateFilterReload();
  });
}

if (els.filterUploadDate) {
  els.filterUploadDate.addEventListener("change", () => {
    updateCandidateFiltersFromInputs();
    triggerCandidateFilterReload();
  });
}

els.filterResetBtn.addEventListener("click", async () => {
  clearCandidateReloadTimer();
  resetCandidateFilters();
  setMessage("");
  try {
    await loadCandidates(state.activeId);
  } catch (err) {
    handleCandidateReloadError(err);
  }
});

els.sortMode.value = state.sortMode;
els.showAll.checked = state.showAllCandidates;
initCandidateFilterSelects();
syncCandidateFilterInputs();

els.sortMode.addEventListener("change", (event) => {
  const value = event.target.value;
  state.sortMode = SORT_MODES.has(value) ? value : DEFAULT_SORT_MODE;
  window.localStorage.setItem("candidateSortMode", state.sortMode);

  const visibleCandidates = getVisibleCandidates();
  if (state.activeId && !visibleCandidates.some((item) => item.candidate_id === state.activeId)) {
    state.activeId = visibleCandidates.length > 0 ? visibleCandidates[0].candidate_id : null;
  }

  renderList();
});

els.showAll.addEventListener("change", async (event) => {
  state.showAllCandidates = Boolean(event.target.checked);
  window.localStorage.setItem("showAllCandidates", state.showAllCandidates ? "1" : "0");

  const visibleCandidates = getVisibleCandidates();
  const hasActive = visibleCandidates.some((item) => item.candidate_id === state.activeId);
  if (!hasActive) {
    state.activeId = visibleCandidates.length > 0 ? visibleCandidates[0].candidate_id : null;
    renderList();
    if (state.activeId) {
      await selectCandidate(state.activeId);
      return;
    }
    clearWorkspaceForEmptyList();
    return;
  }

  renderList();
});

(async () => {
  const ok = await ensureAuthenticated();
  if (!ok) {
    return;
  }
  try {
    await loadInterviewerOptions();
    await refreshUploadJobs();
    await loadCandidates();
  } catch (err) {
    if (err.status === 401) {
      redirectToLogin(false);
      return;
    }
    if (err.status === 403 && err.code === "must_change_password") {
      redirectToLogin(true);
      return;
    }
    setMessage(err.message || "加载失败", "error");
    els.count.textContent = "加载失败";
  }
})();
