const ROLE_ORDER = ["administrator", "hr_specialist", "interviewer", "hiring_manager"];
const ROLE_LABELS = {
  administrator: "管理员",
  hr_specialist: "HR / 招聘专员",
  interviewer: "面试官",
  hiring_manager: "部门负责人 / 用人经理",
};
const DEPARTMENT_SCOPES = ["销售部", "研发部", "算法部", "项目部", "人事部"];

const state = {
  me: null,
  users: [],
  roleDefinitions: {},
  editingUserId: "",
  llmConfig: null,
};

const els = {
  currentUser: document.getElementById("users-current-user"),
  logoutBtn: document.getElementById("users-logout-btn"),
  tableBody: document.getElementById("users-table-body"),
  createForm: document.getElementById("create-user-form"),
  newUsername: document.getElementById("new-username"),
  newDisplayName: document.getElementById("new-display-name"),
  newPassword: document.getElementById("new-password"),
  newRole: document.getElementById("new-role"),
  newDepartmentScope: document.getElementById("new-department-scope"),
  message: document.getElementById("users-message"),
  editModal: document.getElementById("edit-user-modal"),
  editForm: document.getElementById("edit-user-form"),
  editCancelBtn: document.getElementById("edit-user-cancel-btn"),
  editTitle: document.getElementById("edit-user-title"),
  editUsername: document.getElementById("edit-username"),
  editDisplayName: document.getElementById("edit-display-name"),
  editIsActive: document.getElementById("edit-is-active"),
  editRole: document.getElementById("edit-role"),
  editDepartmentScope: document.getElementById("edit-department-scope"),
  editMessage: document.getElementById("edit-user-message"),
  llmConfigPanel: document.getElementById("llm-config-panel"),
  llmConfigRefreshBtn: document.getElementById("llm-config-refresh-btn"),
  llmConfigEnabled: document.getElementById("llm-config-enabled"),
  llmConfigProvider: document.getElementById("llm-config-provider"),
  llmConfigModel: document.getElementById("llm-config-model"),
  llmConfigBaseUrl: document.getElementById("llm-config-base-url"),
  llmConfigApiKeyEnv: document.getElementById("llm-config-api-key-env"),
  llmConfigApiKeyPresent: document.getElementById("llm-config-api-key-present"),
  llmConfigTemperature: document.getElementById("llm-config-temperature"),
  llmConfigMaxTokens: document.getElementById("llm-config-max-tokens"),
  llmConfigTimeout: document.getElementById("llm-config-timeout"),
  llmConfigSource: document.getElementById("llm-config-source"),
  llmConfigPath: document.getElementById("llm-config-path"),
  llmConfigMessage: document.getElementById("llm-config-message"),
};

function normalizeRoleCode(value) {
  const text = String(value || "").trim().toLowerCase();
  return ROLE_ORDER.includes(text) ? text : "";
}

function roleLabelByCode(roleCode) {
  if (!roleCode) {
    return "";
  }
  const fromDefinitions = state.roleDefinitions[roleCode]?.role_name;
  if (fromDefinitions) {
    return fromDefinitions;
  }
  return ROLE_LABELS[roleCode] || roleCode;
}

function roleCodeFromUser(user) {
  const normalized = normalizeRoleCode(user?.role_code);
  if (normalized) {
    return normalized;
  }
  return Number(user?.is_admin || 0) === 1 ? "administrator" : "hr_specialist";
}

function roleLabelFromUser(user) {
  return roleLabelByCode(roleCodeFromUser(user));
}

function normalizeDepartmentScope(value) {
  const text = String(value || "").trim();
  return DEPARTMENT_SCOPES.includes(text) ? text : "";
}

function departmentScopeFromUser(user) {
  return normalizeDepartmentScope(user?.department_scope);
}

function isAdminUser(user) {
  return roleCodeFromUser(user) === "administrator";
}

function setMessage(text, kind = "") {
  els.message.textContent = text;
  els.message.className = "form-message";
  if (kind) {
    els.message.classList.add(kind);
  }
}

function setEditMessage(text, kind = "") {
  els.editMessage.textContent = text;
  els.editMessage.className = "form-message";
  if (kind) {
    els.editMessage.classList.add(kind);
  }
}

function setLlmConfigMessage(text, kind = "") {
  if (!els.llmConfigMessage) {
    return;
  }
  els.llmConfigMessage.textContent = text;
  els.llmConfigMessage.className = "form-message";
  if (kind) {
    els.llmConfigMessage.classList.add(kind);
  }
}

function redirectToLogin(forceChangePassword = false) {
  const suffix = forceChangePassword ? "?force=1" : "";
  window.location.href = `/login${suffix}`;
}

async function fetchJSON(url, options = {}) {
  const req = { ...options };
  if (req.body) {
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

function syncRoleSelectOptions() {
  const options = ROLE_ORDER.map((roleCode) => {
    const roleLabel = roleLabelByCode(roleCode);
    return `<option value="${roleCode}">${roleLabel}</option>`;
  });
  const currentNewRole = normalizeRoleCode(els.newRole.value) || "hr_specialist";
  const currentEditRole = normalizeRoleCode(els.editRole.value) || "hr_specialist";
  els.newRole.innerHTML = options.join("");
  els.editRole.innerHTML = options.join("");
  els.newRole.value = currentNewRole;
  els.editRole.value = currentEditRole;
}

async function loadRoleDefinitions() {
  try {
    const data = await fetchJSON("/api/roles/definitions");
    const items = data.items || [];
    state.roleDefinitions = {};
    items.forEach((item) => {
      const roleCode = normalizeRoleCode(item?.role_code);
      if (!roleCode) {
        return;
      }
      state.roleDefinitions[roleCode] = item;
    });
  } catch {
    state.roleDefinitions = {};
  }
  syncRoleSelectOptions();
  syncNewDepartmentScopeControl();
  syncEditDepartmentScopeControl();
}

function syncDepartmentScopeControl(roleValue, scopeElement) {
  const roleCode = normalizeRoleCode(roleValue) || "hr_specialist";
  const isManager = roleCode === "hiring_manager";
  scopeElement.disabled = !isManager;
  if (!isManager) {
    scopeElement.value = "";
  } else if (!scopeElement.value) {
    scopeElement.value = DEPARTMENT_SCOPES[0];
  }
}

function syncNewDepartmentScopeControl() {
  syncDepartmentScopeControl(els.newRole.value, els.newDepartmentScope);
}

function syncEditDepartmentScopeControl() {
  syncDepartmentScopeControl(els.editRole.value, els.editDepartmentScope);
}

function renderCurrentUser() {
  if (!state.me) {
    els.currentUser.textContent = "未登录";
    return;
  }
  els.currentUser.textContent = `当前用户：${state.me.display_name} (@${state.me.username}) · ${roleLabelFromUser(state.me)}`;
}

function applyAdminVisibility() {
  const isAdmin = isAdminUser(state.me);
  const inputs = els.createForm.querySelectorAll("input, select, button");
  inputs.forEach((node) => {
    node.disabled = !isAdmin;
  });
  if (!isAdmin) {
    setMessage("仅管理员可创建或维护用户", "error");
  }
}

function setText(el, value) {
  if (!el) {
    return;
  }
  const text = String(value ?? "").trim();
  el.textContent = text || "-";
}

function applyLlmConfigVisibility() {
  const isAdmin = isAdminUser(state.me);
  if (!els.llmConfigPanel) {
    return;
  }
  els.llmConfigPanel.classList.toggle("hidden", !isAdmin);
}

function renderLlmConfig() {
  const item = state.llmConfig || {};
  setText(els.llmConfigEnabled, item.enabled ? "已启用" : "未启用");
  setText(els.llmConfigProvider, item.provider || "");
  setText(els.llmConfigModel, item.model || "");
  setText(els.llmConfigBaseUrl, item.base_url || "");
  setText(els.llmConfigApiKeyEnv, item.api_key_env || "");
  setText(els.llmConfigApiKeyPresent, item.api_key_present ? "是" : "否");
  setText(
    els.llmConfigTemperature,
    Number.isFinite(Number(item.temperature)) ? String(item.temperature) : "",
  );
  setText(
    els.llmConfigMaxTokens,
    Number.isFinite(Number(item.max_tokens)) ? String(item.max_tokens) : "",
  );
  setText(
    els.llmConfigTimeout,
    Number.isFinite(Number(item.timeout_seconds)) ? String(item.timeout_seconds) : "",
  );
  setText(els.llmConfigSource, item.source || "");
  setText(els.llmConfigPath, item.config_path || "");
  if (item.warning) {
    setLlmConfigMessage(`配置告警：${item.warning}`, "error");
  } else {
    setLlmConfigMessage("配置已加载", "success");
  }
}

async function loadLlmConfig() {
  if (!isAdminUser(state.me)) {
    applyLlmConfigVisibility();
    return;
  }
  if (els.llmConfigRefreshBtn) {
    els.llmConfigRefreshBtn.disabled = true;
  }
  setLlmConfigMessage("加载中...");
  try {
    const data = await fetchJSON("/api/settings/llm-config");
    state.llmConfig = data.item || null;
    renderLlmConfig();
  } catch (err) {
    if (err.status === 401) {
      redirectToLogin(false);
      return;
    }
    if (err.status === 403 && err.code === "must_change_password") {
      redirectToLogin(true);
      return;
    }
    if (err.status === 403 && err.code === "admin_only") {
      applyLlmConfigVisibility();
      return;
    }
    setLlmConfigMessage(err.message || "加载配置失败", "error");
  } finally {
    if (els.llmConfigRefreshBtn) {
      els.llmConfigRefreshBtn.disabled = false;
    }
  }
}

function renderTable() {
  els.tableBody.innerHTML = "";

  state.users.forEach((user) => {
    const tr = document.createElement("tr");
    const isActiveText = Number(user.is_active || 0) ? "启用" : "禁用";
    const roleText = roleLabelFromUser(user);
    const departmentScope = departmentScopeFromUser(user) || "-";
    const mustChangePwd = Number(user.must_change_password || 0) ? "是" : "否";

    tr.innerHTML = `
      <td>${user.username}</td>
      <td>${user.display_name}</td>
      <td>${isActiveText}</td>
      <td>${roleText}</td>
      <td>${departmentScope}</td>
      <td>${mustChangePwd}</td>
      <td><div class="cell-actions"></div></td>
    `;

    const actions = tr.querySelector(".cell-actions");
    if (isAdminUser(state.me)) {
      const editBtn = document.createElement("button");
      editBtn.type = "button";
      editBtn.className = "inline-btn";
      editBtn.textContent = "编辑";
      editBtn.addEventListener("click", () => editUser(user));
      actions.appendChild(editBtn);

      const resetBtn = document.createElement("button");
      resetBtn.type = "button";
      resetBtn.className = "inline-btn";
      resetBtn.textContent = "重置密码";
      resetBtn.addEventListener("click", () => resetPassword(user));
      actions.appendChild(resetBtn);
    } else {
      actions.textContent = "只读";
    }

    els.tableBody.appendChild(tr);
  });
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
    return true;
  } catch (err) {
    if (err.status === 401) {
      redirectToLogin(false);
      return false;
    }
    setMessage(err.message || "登录态校验失败", "error");
    return false;
  }
}

async function loadUsers() {
  const data = await fetchJSON("/api/users");
  state.users = data.items || [];
  renderTable();
}

function rolePromptHint() {
  return ROLE_ORDER.map((roleCode) => `${roleCode}=${roleLabelByCode(roleCode)}`).join("；");
}

function parseActiveFlagInput(value) {
  const text = String(value || "").trim();
  if (text === "1") {
    return 1;
  }
  if (text === "0") {
    return 0;
  }
  return null;
}

async function editUser(user) {
  const roleCode = roleCodeFromUser(user);
  state.editingUserId = String(user.id || "");
  els.editTitle.textContent = `编辑用户：${user.username || ""}`;
  els.editUsername.value = user.username || "";
  els.editDisplayName.value = user.display_name || "";
  els.editIsActive.value = Number(user.is_active || 0) === 1 ? "1" : "0";
  els.editRole.value = roleCode;
  els.editDepartmentScope.value = departmentScopeFromUser(user);
  syncEditDepartmentScopeControl();
  setEditMessage("");
  els.editModal.classList.remove("hidden");
  els.editDisplayName.focus();
  els.editDisplayName.select();
}

function closeEditModal() {
  state.editingUserId = "";
  els.editForm.reset();
  els.editRole.value = "hr_specialist";
  els.editDepartmentScope.value = "";
  syncEditDepartmentScopeControl();
  setEditMessage("");
  els.editModal.classList.add("hidden");
}

async function saveEditedUser(event) {
  event.preventDefault();
  if (!state.editingUserId) {
    closeEditModal();
    return;
  }

  const normalizedDisplayName = String(els.editDisplayName.value || "").trim();
  if (!normalizedDisplayName) {
    setEditMessage("显示名不能为空", "error");
    return;
  }

  const isActiveValue = parseActiveFlagInput(els.editIsActive.value);
  if (isActiveValue === null) {
    setEditMessage("用户状态仅支持 1（启用）或 0（禁用）", "error");
    return;
  }

  const roleCode = normalizeRoleCode(els.editRole.value);
  if (!roleCode) {
    setEditMessage(`角色编码不合法，请使用：${rolePromptHint()}`, "error");
    return;
  }

  let departmentScope = "";
  if (roleCode === "hiring_manager") {
    departmentScope = normalizeDepartmentScope(els.editDepartmentScope.value);
    if (!departmentScope) {
      setEditMessage(`部门范围仅支持 ${DEPARTMENT_SCOPES.join(" / ")}`, "error");
      return;
    }
  }

  const payload = {
    display_name: normalizedDisplayName,
    is_active: isActiveValue === 1,
    role_code: roleCode,
    department_scope: departmentScope,
  };

  try {
    await fetchJSON(`/api/users/${encodeURIComponent(state.editingUserId)}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    await loadUsers();
    closeEditModal();
    setMessage("用户已更新", "success");
  } catch (err) {
    if (err.status === 401) {
      redirectToLogin(false);
      return;
    }
    if (err.status === 403 && err.code === "must_change_password") {
      redirectToLogin(true);
      return;
    }
    setEditMessage(err.message || "更新用户失败", "error");
  }
}

async function resetPassword(user) {
  const nextPassword = window.prompt(`为 ${user.username} 设置新密码（至少8位）`, "");
  if (nextPassword === null) {
    return;
  }
  try {
    await fetchJSON(`/api/users/${encodeURIComponent(user.id)}/reset-password`, {
      method: "POST",
      body: JSON.stringify({ new_password: nextPassword }),
    });
    await loadUsers();
    setMessage("密码已重置，用户下次登录需改密", "success");
  } catch (err) {
    setMessage(err.message || "重置密码失败", "error");
  }
}

async function createUser(event) {
  event.preventDefault();
  setMessage("");

  if (!isAdminUser(state.me)) {
    setMessage("仅管理员可创建用户", "error");
    return;
  }

  const roleCode = normalizeRoleCode(els.newRole.value) || "hr_specialist";
  const payload = {
    username: els.newUsername.value.trim(),
    display_name: els.newDisplayName.value.trim(),
    password: els.newPassword.value,
    role_code: roleCode,
    department_scope:
      roleCode === "hiring_manager"
        ? normalizeDepartmentScope(els.newDepartmentScope.value) || DEPARTMENT_SCOPES[0]
        : "",
  };

  try {
    await fetchJSON("/api/users", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    els.createForm.reset();
    els.newRole.value = "hr_specialist";
    els.newDepartmentScope.value = "";
    syncNewDepartmentScopeControl();
    await loadUsers();
    setMessage("用户创建成功", "success");
  } catch (err) {
    setMessage(err.message || "创建用户失败", "error");
  }
}

async function logout() {
  try {
    await fetchJSON("/api/auth/logout", { method: "POST" });
  } catch {
    // ignore
  }
  redirectToLogin(false);
}

els.createForm.addEventListener("submit", createUser);
els.logoutBtn.addEventListener("click", logout);
els.newRole.addEventListener("change", syncNewDepartmentScopeControl);
els.editRole.addEventListener("change", syncEditDepartmentScopeControl);
els.editForm.addEventListener("submit", saveEditedUser);
els.editCancelBtn.addEventListener("click", closeEditModal);
els.editModal.addEventListener("click", (event) => {
  if (event.target === els.editModal) {
    closeEditModal();
  }
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !els.editModal.classList.contains("hidden")) {
    closeEditModal();
  }
});
els.llmConfigRefreshBtn?.addEventListener("click", () => {
  loadLlmConfig();
});

(async () => {
  const ok = await ensureAuthenticated();
  if (!ok) {
    return;
  }
  await loadRoleDefinitions();
  renderCurrentUser();
  applyAdminVisibility();
  applyLlmConfigVisibility();
  await loadLlmConfig();
  try {
    await loadUsers();
  } catch (err) {
    if (err.status === 401) {
      redirectToLogin(false);
      return;
    }
    if (err.status === 403 && err.code === "must_change_password") {
      redirectToLogin(true);
      return;
    }
    if (err.status === 403 && err.code === "admin_only") {
      setMessage("仅管理员可查看用户列表", "error");
      return;
    }
    setMessage(err.message || "加载用户失败", "error");
  }
})();
