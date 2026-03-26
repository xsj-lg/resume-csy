const INTERVIEW_STAGES = ["鍒濈瓫", "涓€闈?, "浜岄潰", "HR闈?];
const STATUS_PENDING = "pending";
const STATUS_PASSED = "passed";
const STATUS_ENDED = "ended";

const CANDIDATE_STATUS_BY_STAGE = {
  鍒濈瓫: "寰呭垵绛?,
  涓€闈? "寰呬竴闈?,
  浜岄潰: "寰呬簩闈?,
  HR闈? "寰匟R闈?,
};
const FAILED_STATUS_BY_STAGE = {
  鍒濈瓫: "鏈€氳繃鍒濈瓫",
  涓€闈? "鏈€氳繃涓€闈?,
  浜岄潰: "鏈€氳繃浜岄潰",
  HR闈? "鏈€氳繃HR闈?,
};
const FAILED_CANDIDATE_STATUSES = new Set(Object.values(FAILED_STATUS_BY_STAGE));

const DEFAULT_SORT_MODE = "star_time";
const SORT_MODES = new Set(["star_time", "time", "name"]);
const POSITION_MATCH_MODES = new Set(["fuzzy", "exact"]);
const FILTER_DEBOUNCE_MS = 260;
const ROLE_ORDER = ["administrator", "hr_specialist", "interviewer", "hiring_manager"];
const DEPARTMENT_SCOPES = ["閿€鍞儴", "鐮斿彂閮?, "绠楁硶閮?, "椤圭洰閮?, "浜轰簨閮?];
const ROLE_LABELS = {
  administrator: "绠＄悊鍛?,
  hr_specialist: "HR / 鎷涜仒涓撳憳",
  interviewer: "闈㈣瘯瀹?,
  hiring_manager: "閮ㄩ棬璐熻矗浜?/ 鐢ㄤ汉缁忕悊",
};
const EMAIL_PATTERN = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;
const MOBILE_PHONE_PATTERN = /(?:\+?86[-\s]?)?(1[3-9]\d[-\s]?\d{4}[-\s]?\d{4})/;
const LANDLINE_PHONE_PATTERN = /(0\d{2,3}[-\s]?\d{7,8})/;
const JOB_STORAGE_KEY = "rs_jobs_v012";

const state = {
  candidates: [],
  candidateTotalCount: 0,
  candidateFilteredCount: 0,
  candidateFilters: {
    name: "",
    position: "",
    positionMatch: "fuzzy",
    department: "",
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
  candidateReloadTimer: null,
  candidateFetchSeq: 0,
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
  salaryMode: document.getElementById("salary-mode"),
  salaryRange: document.getElementById("salary-range"),
  experienceType: document.getElementById("experience-type"),
  graduationWrap: document.getElementById("graduation-wrap"),
  graduationYear: document.getElementById("graduation-year"),
  workWrap: document.getElementById("work-wrap"),
  workYears: document.getElementById("work-years"),
  highestEducation: document.getElementById("highest-education"),
  schoolName: document.getElementById("school-name"),
  phoneNumber: document.getElementById("phone-number"),
  email: document.getElementById("email"),
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

function normalizeFilterKeyword(value) {
  return String(value || "").trim();
}

function normalizeDepartmentScope(value) {
  const text = String(value || "").trim();
  return DEPARTMENT_SCOPES.includes(text) ? text : "";
}

function normalizePhoneNumber(value) {
  const text = String(value || "").trim();
  if (!text) {
    return "";
  }
  const mobile = text.match(MOBILE_PHONE_PATTERN);
  if (mobile && mobile[1]) {
    const digits = mobile[1].replace(/\D+/g, "");
    if (digits.length === 11) {
      return digits;
    }
  }
  const landline = text.match(LANDLINE_PHONE_PATTERN);
  if (landline && landline[1]) {
    return landline[1].replace(/\s+/g, "");
  }
  return "";
}

function readCandidateFiltersFromInputs() {
  const name = normalizeFilterKeyword(els.filterName.value);
  const position = normalizeFilterKeyword(els.filterPosition.value);
  const selectedMode = String(els.filterPositionMatch.value || "").trim().toLowerCase();
  const positionMatch = POSITION_MATCH_MODES.has(selectedMode) ? selectedMode : "fuzzy";
  const department = normalizeDepartmentScope(els.filterDepartment.value);
  return { name, position, positionMatch, department };
}

function syncCandidateFilterInputs() {
  els.filterName.value = state.candidateFilters.name;
  els.filterPosition.value = state.candidateFilters.position;
  els.filterPositionMatch.value = state.candidateFilters.positionMatch;
  els.filterDepartment.value = state.candidateFilters.department;
}

function hasActiveCandidateFilters() {
  return Boolean(state.candidateFilters.name || state.candidateFilters.position || state.candidateFilters.department);
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

function parseUploadJobsFromStorage() {
  try {
    const raw = JSON.parse(window.localStorage.getItem(JOB_STORAGE_KEY) || "[]");
    if (!Array.isArray(raw)) {
      return [];
    }
    return raw
      .map((item) => ({
        job_id: normalizeJobId(item?.job_id),
        job_code: String(item?.job_code || "").trim(),
        title: String(item?.title || "").trim(),
        department: normalizeDepartmentScope(item?.department),
        status: String(item?.status || "").trim(),
        updated_at: String(item?.updated_at || item?.created_at || "").trim(),
        jd: String(item?.jd || "").trim(),
        requirements: String(item?.requirements || "").trim(),
        criteria: item?.criteria && typeof item.criteria === "object" ? item.criteria : {},
        process: item?.process && typeof item.process === "object" ? item.process : {},
        auto_score_enabled: Boolean(item?.auto_score_enabled),
        active_template_version: Number(item?.active_template_version || 0),
        templates: Array.isArray(item?.templates) ? item.templates : [],
      }))
      .filter((item) => item.job_id && item.title && item.status !== "closed")
      .sort((a, b) => Date.parse(b.updated_at || "") - Date.parse(a.updated_at || ""));
  } catch {
    return [];
  }
}

function renderUploadJobOptions() {
  const selected = normalizeJobId(els.uploadJob.value);
  const jobs = state.uploadJobs;
  if (jobs.length === 0) {
    els.uploadJob.innerHTML = '<option value="">鏆傛棤鍙叧鑱斿矖浣嶏紙璇峰厛鍒板矖浣嶇鐞嗗垱寤猴級</option>';
    els.uploadJob.value = "";
    return;
  }

  els.uploadJob.innerHTML = ['<option value="">璇烽€夋嫨宀椾綅</option>']
    .concat(
      jobs.map((job) => {
        const codeText = job.job_code ? ` [${job.job_code}]` : "";
        const departmentText = job.department ? ` 路 ${job.department}` : "";
        return `<option value="${job.job_id}">${job.title}${codeText}${departmentText}</option>`;
      }),
    )
    .join("");
  els.uploadJob.value = jobs.some((job) => job.job_id === selected) ? selected : "";
}

function refreshUploadJobs() {
  state.uploadJobs = parseUploadJobsFromStorage();
  renderUploadJobOptions();
}

function selectedUploadJob() {
  const selectedJobId = normalizeJobId(els.uploadJob.value);
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

function openUploadModal() {
  refreshUploadJobs();
  els.uploadModal.classList.remove("hidden");
  els.uploadCandidateName.disabled = false;
  if (!normalizeDepartmentScope(els.uploadDepartment.value)) {
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
  const isFresh = type === "搴斿眾鐢?;
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
    els.currentUserText.textContent = "鏈櫥褰?;
    els.jobsManageLink.classList.add("hidden");
    els.usersManageLink.classList.add("hidden");
    els.triggerAutoScoreBtn.classList.add("hidden");
    els.triggerAutoScoreBtn.disabled = true;
    return;
  }
  const roleCode = roleCodeFromUser(user);
  const roleText = roleLabelFromCode(roleCode);
  els.currentUserText.textContent = `${user.display_name} (@${user.username}) 路 ${roleText}`;
  const canManageJobs = roleCode === "administrator" || roleCode === "hr_specialist" || roleCode === "hiring_manager";
  const canTriggerAutoScore = roleCode === "administrator" || roleCode === "hr_specialist";
  els.jobsManageLink.classList.toggle("hidden", !canManageJobs);
  els.usersManageLink.classList.toggle("hidden", roleCode !== "administrator");
  els.triggerAutoScoreBtn.classList.toggle("hidden", !canTriggerAutoScore);
  els.triggerAutoScoreBtn.disabled = !canTriggerAutoScore;
  syncDepartmentFilterVisibility();
  syncProfileDepartmentPermission();
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
  return ROLE_LABELS[roleCode] || "鐢ㄦ埛";
}

function syncDepartmentFilterVisibility() {
  const roleCode = roleCodeFromUser(state.currentUser);
  const shouldHide = roleCode === "hiring_manager";
  els.filterDepartmentWrap.classList.toggle("hidden", shouldHide);
  if (shouldHide && state.candidateFilters.department) {
    state.candidateFilters.department = "";
    syncCandidateFilterInputs();
  }
}

function syncProfileDepartmentPermission() {
  const roleCode = roleCodeFromUser(state.currentUser);
  const writable = roleCode === "administrator" || roleCode === "hr_specialist";
  els.candidateDepartment.disabled = !writable;
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
  return stage ? `鏈€氳繃${stage}` : "鏈€氳繃";
}

function isFailedInterviewStatus(status) {
  const text = String(status || "").trim();
  return FAILED_CANDIDATE_STATUSES.has(text) || /^鏈€氳繃/.test(text);
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
    return "閫氳繃";
  }
  const pendingStage = INTERVIEW_STAGES.find((stage) => statuses[stage] === STATUS_PENDING) || INTERVIEW_STAGES[0];
  return CANDIDATE_STATUS_BY_STAGE[pendingStage] || CANDIDATE_STATUS_BY_STAGE[INTERVIEW_STAGES[0]];
}

function stageStatusClass(status) {
  if (status === "寰呭垵绛?) {
    return "tag-status-wait-screen";
  }
  if (status === "寰呬竴闈?) {
    return "tag-status-wait-1";
  }
  if (status === "寰呬簩闈?) {
    return "tag-status-wait-2";
  }
  if (status === "寰匟R闈?) {
    return "tag-status-wait-hr";
  }
  if (status === "閫氳繃") {
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

  if (!state.showAllCandidates) {
    return sortedNormal;
  }

  const sortedFailed = [...failed].sort((a, b) => {
    const aTime = parseDatetimeMs(a.terminated_at) || 0;
    const bTime = parseDatetimeMs(b.terminated_at) || 0;
    return bTime - aTime;
  });

  return [...sortedNormal, ...sortedFailed];
}

function renderCalendar() {
  els.calendarList.innerHTML = "";
  const items = state.calendarItems || [];
  els.calendarCount.textContent = String(items.length);

  if (items.length === 0) {
    const li = document.createElement("li");
    li.className = "calendar-item empty";
    li.textContent = "鏆傛棤闈㈣瘯瀹夋帓";
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
          setMessage(err.message || "鍊欓€変汉鍔犺浇澶辫触", "error");
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
    li.textContent = "鏆傛棤鍙樉绀哄€欓€変汉";
    els.list.appendChild(li);
  }

  visibleCandidates.forEach((candidate) => {
    const li = document.createElement("li");
    li.className = `candidate-item ${candidate.candidate_id === state.activeId ? "active" : ""}`;

    const stageStatus = candidate.interview_status || CANDIDATE_STATUS_BY_STAGE[INTERVIEW_STAGES[0]];
    const stageClass = stageStatusClass(stageStatus);
    const inflowDisplay = formatDateTag(candidate.inflow_date);
    li.innerHTML = `
      <div class="candidate-title-row">
        <div class="candidate-name">${candidate.name}</div>
        <button type="button" class="star-btn ${Number(candidate.is_starred || 0) ? "on" : ""}">${
          Number(candidate.is_starred || 0) ? "鈽? : "鈽?
        }</button>
      </div>
      <div class="candidate-tags">
        <span class="tag">${candidate.experience_tag || "鏈煡"}</span>
        <span class="tag">${candidate.duration_tag || "鏈煡"}</span>
        <span class="tag">${candidate.education_tag || "鏈煡"}</span>
        <span class="tag">${candidate.school_tag || "鏈煡"}</span>
        <span class="tag">${candidate.department_scope || "鏈垎閰嶉儴闂?}</span>
        <span class="tag tag-inflow">${inflowDisplay || "鏈煡"}</span>
        <span class="tag tag-stage ${stageClass}">${stageStatus}</span>
      </div>
      <div class="candidate-note">${candidate.applied_position_text || "鐢宠宀椾綅:鏈煡"}</div>
    `;

    const starBtn = li.querySelector(".star-btn");
    starBtn.addEventListener("click", async (event) => {
      event.stopPropagation();
      await toggleCandidateStar(candidate);
    });

    li.addEventListener("click", () => {
      selectCandidate(candidate.candidate_id).catch((err) => {
        setMessage(err.message || "鍔犺浇澶辫触", "error");
      });
    });
    els.list.appendChild(li);
  });

  const hiddenFailed =
    state.showAllCandidates === true
      ? 0
      : state.candidates.filter((item) => isFailedInterviewStatus(item.interview_status)).length;

  const totalCount = Number.isFinite(state.candidateTotalCount) ? state.candidateTotalCount : state.candidates.length;
  const filteredCount = Number.isFinite(state.candidateFilteredCount)
    ? state.candidateFilteredCount
    : state.candidates.length;

  if (hasActiveCandidateFilters()) {
    els.count.textContent =
      hiddenFailed > 0
        ? `绛涢€夌粨鏋?${visibleCandidates.length}/${filteredCount} 浣嶏紙鍏ㄩ噺 ${totalCount} 浣嶏紝闅愯棌鏈€氳繃 ${hiddenFailed} 浣嶏級`
        : `绛涢€夌粨鏋?${visibleCandidates.length}/${filteredCount} 浣嶏紙鍏ㄩ噺 ${totalCount} 浣嶏級`;
    return;
  }

  els.count.textContent =
    hiddenFailed > 0
      ? `鏄剧ず ${visibleCandidates.length}/${filteredCount} 浣嶏紙闅愯棌鏈€氳繃 ${hiddenFailed} 浣嶏級`
      : `鍏?${visibleCandidates.length} 浣嶅€欓€変汉`;
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
    const error = new Error(data.error || "璇锋眰澶辫触");
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
    return "鏈畾";
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
    return text || "鏈煡";
  }
  return `${text.slice(0, 4)}-${text.slice(4, 6)}-${text.slice(6, 8)}`;
}

function formatCandidateJobText(candidate) {
  const jobTitle = String(candidate?.job_title || "").trim();
  const jobCode = String(candidate?.job_code || "").trim();
  if (jobTitle && jobCode) {
    return `${jobTitle}锛?{jobCode}锛塦;
  }
  if (jobTitle) {
    return jobTitle;
  }
  const appliedPosition = String(candidate?.applied_position || "").trim();
  return appliedPosition || "鏈叧鑱斿矖浣?;
}

function updateActiveMeta(candidate) {
  const departmentText = normalizeDepartmentScope(candidate?.department_scope) || "鏈垎閰嶉儴闂?;
  const jobText = formatCandidateJobText(candidate);
  els.activeMeta.textContent = `鏂囦欢锛?{candidate?.filename || "-"} 路 娴佸叆鏃ワ細${formatDateTag(candidate?.inflow_date)} 路 閮ㄩ棬锛?{departmentText} 路 宀椾綅锛?{jobText}`;
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
    actionStage === INTERVIEW_STAGES[INTERVIEW_STAGES.length - 1] ? "閫氳繃闈㈣瘯" : "杩涘叆涓嬩竴闃舵";
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
    els.currentStageText.textContent = `褰撳墠娴佺▼锛氬凡缁撴潫锛?{failedStatusByStage(closedStage || actionStage)}锛塦;
  } else if (allPassed) {
    els.currentStageText.textContent = "褰撳墠娴佺▼锛氬凡閫氳繃闈㈣瘯";
  } else {
    els.currentStageText.textContent = `褰撳墠娴佺▼锛?{current}锛堣繘琛屼腑锛塦;
  }

  if (closedStage) {
    els.stageEndedFrom.classList.remove("hidden");
    els.stageEndedFrom.textContent = `缁撴潫缁撴灉锛?{failedStatusByStage(closedStage)}`;
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
  els.candidateName.value = profile.candidate_name || candidate?.name || "";
  els.baseLocation.value = profile.base_location || "鍖椾含";
  els.candidateDepartment.value = normalizeDepartmentScope(profile.department_scope || candidate?.department_scope || "");
  els.appliedPosition.value = profile.applied_position || "";
  els.salaryMode.value = profile.salary_mode || "鏈堣柂";
  els.salaryRange.value = profile.salary_range || "";
  els.experienceType.value = profile.experience_type || "搴斿眾鐢?;
  els.graduationYear.value = profile.graduation_year || "";
  els.workYears.value = profile.work_years || "";
  els.highestEducation.value = profile.highest_education || "鏈煡";
  els.schoolName.value = profile.school_name || "鏈煡";
  els.phoneNumber.value = profile.phone_number || "";
  els.email.value = profile.email || "";
  els.hireType.value = profile.hire_type || "瀹炰範";
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
  empty.textContent = "鏈寚瀹?;
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
    fallback.textContent = `${selectedId} (宸蹭笉鍙敤)`;
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
  els.roundSectionTitle.textContent = `绗?{stageNo}闃舵鐨勯潰璇勪俊鎭痐;
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
    els.jobConfigMeta.textContent = "鏈叧鑱斿矖浣嶉厤缃?;
    return;
  }

  const titleText = jobCode ? `${jobTitle || "-"}锛?{jobCode}锛塦 : jobTitle || "-";
  const activeVersion = snapshot.score_table_version || "v1";
  els.jobConfigMeta.textContent = `宀椾綅锛?{titleText} 路 璇勫垎椤癸細${scoreItems.length} 路 璇勫垎鐗堟湰锛?{activeVersion} 路 鑷姩璇勫垎锛?{autoEnabled ? "宸插惎鐢? : "鏈惎鐢?}`;

  INTERVIEW_STAGES.forEach((stage) => {
    const stageRequirement = String(process[stage] || "").trim();
    if (!stageRequirement) {
      return;
    }
    const li = document.createElement("li");
    li.textContent = `娴佺▼-${stage}锛?{stageRequirement}`;
    els.jobConfigList.appendChild(li);
  });

  const criteriaItems = [
    ["瀛﹀巻", criteria.education],
    ["涓撲笟", criteria.major],
    ["鎶€鑳?, criteria.skills],
    ["椤圭洰缁忛獙", criteria.project_experience],
  ];
  criteriaItems.forEach(([label, value]) => {
    const text = String(value || "").trim();
    if (!text) {
      return;
    }
    const li = document.createElement("li");
    li.textContent = `绛涢€?${label}锛?{text}`;
    els.jobConfigList.appendChild(li);
  });

  if (els.jobConfigList.childElementCount === 0) {
    const li = document.createElement("li");
    li.textContent = "宸插叧鑱斿矖浣嶏紝浣嗘湭閰嶇疆娴佺▼璇存槑鎴栫瓫閫夋爣鍑嗐€?;
    els.jobConfigList.appendChild(li);
  }
}

function renderAutoScore(score) {
  els.aiScoreRiskList.innerHTML = "";
  els.aiScoreDimensionList.innerHTML = "";
  if (!score) {
    els.aiScoreMeta.textContent = "鏆傛棤鑷姩璇勫垎缁撴灉";
    els.aiScoreSummary.textContent = "";
    return;
  }

  const scoreSource = score.score_source === "llm" ? "LLM" : "瑙勫垯闄嶇骇";
  const scoreStatus = score.score_status || "success";
  const createdAt = score.created_at ? new Date(score.created_at).toLocaleString("zh-CN") : "-";
  const modelName = score.model_name || "-";
  const promptId = score.prompt_id || "-";
  els.aiScoreMeta.textContent =
    `鏉ユ簮锛?{scoreSource} 路 鐘舵€侊細${scoreStatus} 路 鎬诲垎锛?{score.total_score || 0}/${score.max_score || 0} 路 缁撹锛?{score.match_level || "寰呭畾"} 路 鏃堕棿锛?{createdAt} 路 妯″瀷锛?{modelName} 路 Prompt锛?{promptId}`;
  els.aiScoreSummary.textContent = score.summary || "";

  const riskFlags = Array.isArray(score.risk_flags) ? score.risk_flags : [];
  if (riskFlags.length > 0) {
    riskFlags.forEach((flag) => {
      const li = document.createElement("li");
      li.textContent = `椋庨櫓锛?{flag}`;
      els.aiScoreRiskList.appendChild(li);
    });
  }

  const dimensions = Array.isArray(score.dimension_scores) ? score.dimension_scores : [];
  dimensions.slice(0, 8).forEach((dim) => {
    const name = String(dim?.dimension_name || "鏈懡鍚嶇淮搴?);
    const dimScore = Number(dim?.dimension_score || 0);
    const dimMax = Number(dim?.dimension_max || 0);
    const li = document.createElement("li");
    li.textContent = `${name}锛?{dimScore}/${dimMax}`;
    els.aiScoreDimensionList.appendChild(li);
  });

  if (score.error_message) {
    const li = document.createElement("li");
    li.textContent = `璇存槑锛氬凡浣跨敤瑙勫垯璇勫垎鍏滃簳锛孡LM閿欒锛?{score.error_message}`;
    els.aiScoreRiskList.appendChild(li);
  }
}

function applyEvaluation(item, preserveViewStage = false) {
  state.evaluation = item;
  applyProfileFields(item.profile || {});

  const statuses = normalizeStageStatuses(item.profile || {});
  const workflowStage = currentWorkflowStage(item.profile || {}, statuses);
  if (!preserveViewStage || !INTERVIEW_STAGES.includes(state.viewStage)) {
    state.viewStage = workflowStage;
  }

  renderStageAxis();
  applyRoundFields();
  renderJobSnapshot(item);
  renderAutoScore(item.auto_score || null);

  const updated = item.profile?.updated_at
    ? `鏈€杩戜繚瀛橈細${new Date(item.profile.updated_at).toLocaleString("zh-CN")}`
    : "鏈繚瀛?;
  els.hint.textContent = updated;
}

function syncCandidateListFromProfile() {
  const profile = state.evaluation?.profile;
  const candidate = activeCandidate();
  if (!profile || !candidate) {
    return;
  }

  candidate.name = profile.candidate_name || candidate.name || "鏈懡鍚嶅€欓€変汉";
  candidate.experience_tag = profile.experience_type || "鏈煡";
  candidate.duration_tag =
    profile.experience_type === "搴斿眾鐢?
      ? profile.graduation_year
        ? `${profile.graduation_year}姣曚笟`
        : "鏈煡"
      : profile.work_years || "鏈煡";
  candidate.education_tag = profile.highest_education || "鏈煡";
  candidate.school_tag = profile.school_name || "鏈煡";
  candidate.interview_status = deriveInterviewStatusFromProfile(profile);
  candidate.stage_tag = candidate.interview_status;
  candidate.applied_position = profile.applied_position || candidate.applied_position || "";
  candidate.job_id = profile.job_id || candidate.job_id || "";
  candidate.job_code = profile.job_code || candidate.job_code || "";
  candidate.job_title = profile.job_title || candidate.job_title || "";
  const appliedText = formatCandidateJobText(candidate);
  candidate.applied_position_text = `鐢宠宀椾綅:${appliedText}`;
  candidate.department_scope = normalizeDepartmentScope(profile.department_scope || candidate.department_scope || "");
  candidate.is_starred = Number(profile.is_starred || 0);
  candidate.terminated_at = profile.terminated_at || "";
  if (candidate.candidate_id === state.activeId) {
    els.activeCandidate.textContent = candidate.name;
    updateActiveMeta(candidate);
  }
}

function buildProfilePayload() {
  return {
    candidate_name: els.candidateName.value.trim(),
    base_location: els.baseLocation.value,
    department_scope: normalizeDepartmentScope(els.candidateDepartment.value),
    applied_position: els.appliedPosition.value.trim(),
    salary_mode: els.salaryMode.value,
    salary_range: els.salaryRange.value.trim(),
    experience_type: els.experienceType.value,
    graduation_year: els.graduationYear.value.trim(),
    work_years: els.workYears.value.trim(),
    highest_education: els.highestEducation.value,
    school_name: els.schoolName.value.trim(),
    phone_number: normalizePhoneNumber(els.phoneNumber.value),
    email: els.email.value.trim().toLowerCase(),
    hire_type: els.hireType.value,
    preset_position: els.presetPosition.value.trim(),
  };
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
  renderList();

  els.activeCandidate.textContent = candidate.name;
  updateActiveMeta(candidate);
  els.frame.src = candidate.pdf_url;
  setMessage("");

  const data = await fetchJSON(`/api/evaluations/${encodeURIComponent(candidateId)}`);
  applyEvaluation(data.item);
  syncCandidateListFromProfile();
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
    setMessage(nextStarred ? "宸插姞鏄熸爣" : "宸插彇娑堟槦鏍?, "success");
  } catch (err) {
    if (err.status === 401) {
      redirectToLogin(false);
      return;
    }
    if (err.status === 403 && err.code === "must_change_password") {
      redirectToLogin(true);
      return;
    }
    setMessage(err.message || "鏄熸爣淇濆瓨澶辫触", "error");
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
    next: activeStage === INTERVIEW_STAGES[INTERVIEW_STAGES.length - 1] ? "宸查€氳繃闈㈣瘯" : "宸茶繘鍏ヤ笅涓€闃舵",
    end: `宸叉爣璁?{failedStatusByStage(activeStage)}`,
    reset: "宸查噸缃樁娈电姸鎬?,
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
    setMessage(successMap[action] || "闃舵鐘舵€佸凡鏇存柊", "success");
  } catch (err) {
    if (err.status === 403 && err.code === "must_change_password") {
      redirectToLogin(true);
      return;
    }
    setMessage(err.message || "闃舵娴佽浆澶辫触", "error");
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
    setMessage("闈㈣瘎淇℃伅宸蹭繚瀛?, "success");
  } catch (err) {
    if (err.status === 403 && err.code === "must_change_password") {
      redirectToLogin(true);
      return;
    }
    setMessage(err.message || "闈㈣瘎淇℃伅淇濆瓨澶辫触", "error");
  }
}

async function triggerAutoScore() {
  if (!state.activeId) {
    setMessage("璇峰厛閫夋嫨鍊欓€変汉", "error");
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
    setMessage("宸茶Е鍙戣嚜鍔ㄨ瘎鍒嗗苟鏇存柊缁撴灉", "success");
  } catch (err) {
    if (err.status === 401) {
      redirectToLogin(false);
      return;
    }
    if (err.status === 403 && err.code === "must_change_password") {
      redirectToLogin(true);
      return;
    }
    setMessage(err.message || "瑙﹀彂鑷姩璇勫垎澶辫触", "error");
  } finally {
    els.triggerAutoScoreBtn.disabled = false;
  }
}

async function saveProfile() {
  if (!state.activeId) {
    return;
  }

  const payload = buildProfilePayload();
  if (!payload.candidate_name) {
    setMessage("鍊欓€変汉鍚嶇О涓嶈兘涓虹┖", "error");
    return;
  }
  if (!normalizeDepartmentScope(payload.department_scope)) {
    setMessage(`閮ㄩ棬浠呮敮鎸侊細${DEPARTMENT_SCOPES.join(" / ")}`, "error");
    return;
  }
  if (payload.salary_range && !payload.salary_range.includes("-")) {
    setMessage("钖祫鍖洪棿闇€涓哄尯闂村€硷紝渚嬪 30k-40k", "error");
    return;
  }
  if (els.phoneNumber.value.trim() && !payload.phone_number) {
    setMessage("鑱旂郴鐢佃瘽鏍煎紡涓嶆纭?, "error");
    return;
  }
  if (payload.email && !EMAIL_PATTERN.test(payload.email)) {
    setMessage("閭鏍煎紡涓嶆纭?, "error");
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
    setMessage("閫氱敤淇℃伅宸蹭繚瀛?, "success");
  } catch (err) {
    if (err.status === 403 && err.code === "must_change_password") {
      redirectToLogin(true);
      return;
    }
    setMessage(err.message || "閫氱敤淇℃伅淇濆瓨澶辫触", "error");
  }
}

async function deleteActiveCandidate() {
  if (!state.activeId) {
    return;
  }
  const candidate = activeCandidate();
  const displayName = candidate?.name || "璇ュ€欓€変汉";
  const confirmed = window.confirm(`纭鍒犻櫎 ${displayName}锛熻鎿嶄綔浼氬垹闄ゅ€欓€変汉淇℃伅鍜屾湰鍦?PDF锛屼笖涓嶅彲鎭㈠銆俙);
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
    setMessage("鍊欓€変汉宸插垹闄?, "success");
  } catch (err) {
    if (err.status === 401) {
      redirectToLogin(false);
      return;
    }
    if (err.status === 403 && err.code === "must_change_password") {
      redirectToLogin(true);
      return;
    }
    setMessage(err.message || "鍊欓€変汉鍒犻櫎澶辫触", "error");
  }
}

async function uploadResume(event) {
  event.preventDefault();
  setUploadMessage("");

  const files = Array.from(els.uploadFile.files || []);
  if (files.length === 0) {
    setUploadMessage("璇烽€夋嫨鑷冲皯涓€涓?PDF 鏂囦欢", "error");
    return;
  }
  const linkedJob = selectedUploadJob();
  if (!linkedJob) {
    setUploadMessage("璇烽€夋嫨鍏宠仈宀椾綅", "error");
    return;
  }
  const jobPayload = buildUploadJobPayload(linkedJob);
  const candidateName = els.uploadCandidateName.value.trim();
  const departmentScope = normalizeDepartmentScope(els.uploadDepartment.value || linkedJob.department);
  if (!departmentScope) {
    setUploadMessage(`璇烽€夋嫨閮ㄩ棬锛?{DEPARTMENT_SCOPES.join(" / ")}`, "error");
    return;
  }
  const applyCandidateName = files.length === 1 && candidateName;
  const createdIds = [];
  let successCount = 0;
  const failed = [];
  const scored = [];
  const scoreFailed = [];

  els.uploadSubmitBtn.disabled = true;
  try {
    for (const file of files) {
      if (!String(file.name || "").toLowerCase().endsWith(".pdf")) {
        failed.push({ name: file.name || "鏈懡鍚嶆枃浠?, reason: "浠呮敮鎸佷笂浼?PDF 鏂囦欢" });
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
        if (created.auto_score && typeof created.auto_score === "object") {
          scored.push({
            name: created.candidate_name || file.name || "未命名候选人",
            total: Number(created.auto_score.total_score || 0),
            max: Number(created.auto_score.max_score || 0),
            level: created.auto_score.match_level || "待定",
          });
        } else if (Boolean(jobPayload.auto_score_enabled)) {
          scoreFailed.push({
            name: created.candidate_name || file.name || "未命名候选人",
            reason: created.auto_score_error || "自动评分未生成结果",
          });
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
        failed.push({ name: file.name || "鏈懡鍚嶆枃浠?, reason: err.message || "涓婁紶澶辫触" });
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
    setUploadMessage(err.message || "涓婁紶澶辫触", "error");
  } finally {
    els.uploadSubmitBtn.disabled = false;
  }

  const failedCount = failed.length;
  const summary = `鎵归噺涓婁紶瀹屾垚锛氭垚鍔?${successCount}锛屽け璐?${failedCount}`;
  const scoreSummary = scored.length > 0 ? ` 鑷姩璇勫垎鎴愬姛 ${scored.length}` : "";
  const scoreFailedSummary = scoreFailed.length > 0 ? `锛涜瘎鍒嗘湭鐢熸垚 ${scoreFailed.length}` : "";
  if (successCount > 0) {
    closeUploadModal();
    await loadCandidates(createdIds[0] || null);
    if (failedCount === 0) {
      if (scored.length > 0) {
        const first = scored[0];
        setMessage(
          `${summary}${scoreSummary}${scoreFailedSummary}。示例：${first.name} ${first.total}/${first.max}，${first.level}`,
          "success",
        );
        return;
      }
      setMessage(`${summary}${scoreSummary}${scoreFailedSummary}`, scoreFailed.length > 0 ? "error" : "success");
      return;
    }
    const failPreview = failed
      .slice(0, 3)
      .map((item) => `${item.name}(${item.reason})`)
      .join("锛?);
    const overflow = failedCount > 3 ? `锛涘叾浣?${failedCount - 3} 浠藉け璐 : "";
    setMessage(`${summary}${scoreSummary}${scoreFailedSummary}銆傚け璐ョず渚嬶細${failPreview}${overflow}`, "error");
    return;
  }

  const allFailedPreview = failed
    .slice(0, 3)
    .map((item) => `${item.name}(${item.reason})`)
    .join("锛?);
  const overflow = failedCount > 3 ? `锛涘叾浣?${failedCount - 3} 浠藉け璐 : "";
  setUploadMessage(`${summary}銆?{allFailedPreview}${overflow}`, "error");
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
    setMessage(`鍚屾瀹屾垚锛氭柊澧?${addedCount} 浠斤紝鎵弿 ${scannedCount} 浠?PDF`, "success");
  } catch (err) {
    if (err.status === 401) {
      redirectToLogin(false);
      return;
    }
    if (err.status === 403 && err.code === "must_change_password") {
      redirectToLogin(true);
      return;
    }
    setMessage(err.message || "鐩綍鍚屾澶辫触", "error");
  } finally {
    els.syncResumesBtn.disabled = false;
  }
}

function clearWorkspaceForEmptyList() {
  els.activeCandidate.textContent = "鏆傛棤鍊欓€変汉";
  els.activeMeta.textContent = "";
  els.frame.src = "about:blank";
  renderJobSnapshot(null);
  els.hint.textContent = "鏈繚瀛?;
  renderAutoScore(null);
  setMessage("");
}

async function reconcileActiveCandidateSelection() {
  const visibleCandidates = getVisibleCandidates();
  if (visibleCandidates.length === 0) {
    state.activeId = null;
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
  setMessage(err.message || "鍊欓€変汉鍒楄〃鍔犺浇澶辫触", "error");
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
  if (requestSeq !== state.candidateFetchSeq) {
    return;
  }

  state.candidates = candidateData.items || [];
  state.candidateTotalCount = Number(candidateData.total_count ?? state.candidates.length);
  state.candidateFilteredCount = Number(candidateData.filtered_count ?? state.candidates.length);
  state.calendarItems = calendarData.items || [];

  renderCalendar();

  if (preferredCandidateId && state.candidates.some((item) => item.candidate_id === preferredCandidateId)) {
    state.activeId = preferredCandidateId;
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
    setMessage(err.message || "鐧诲綍鐘舵€佹牎楠屽け璐?, "error");
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
  };
  syncCandidateFilterInputs();
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
els.triggerAutoScoreBtn.addEventListener("click", triggerAutoScore);
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
els.uploadJob.addEventListener("change", () => {
  const linkedJob = selectedUploadJob();
  if (!linkedJob) {
    return;
  }
  const jobDepartment = normalizeDepartmentScope(linkedJob.department);
  if (jobDepartment) {
    els.uploadDepartment.value = jobDepartment;
  }
});
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

els.filterDepartment.addEventListener("change", () => {
  updateCandidateFiltersFromInputs();
  triggerCandidateFilterReload();
});

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
    setMessage(err.message || "鍔犺浇澶辫触", "error");
    els.count.textContent = "鍔犺浇澶辫触";
  }
})();
