const els = {
  loginForm: document.getElementById("login-form"),
  username: document.getElementById("login-username"),
  password: document.getElementById("login-password"),
  changeForm: document.getElementById("change-password-form"),
  oldPassword: document.getElementById("old-password"),
  newPassword: document.getElementById("new-password"),
  confirmPassword: document.getElementById("confirm-password"),
  message: document.getElementById("login-message"),
};

const state = {
  user: null,
};

function setMessage(text, kind = "") {
  els.message.textContent = text;
  els.message.className = "form-message";
  if (kind) {
    els.message.classList.add(kind);
  }
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

function showChangePasswordForm(prefillOldPassword = "") {
  els.loginForm.classList.add("hidden");
  els.changeForm.classList.remove("hidden");
  els.oldPassword.value = prefillOldPassword;
  els.newPassword.value = "";
  els.confirmPassword.value = "";
}

function showLoginForm() {
  els.loginForm.classList.remove("hidden");
  els.changeForm.classList.add("hidden");
}

function goHome() {
  window.location.href = "/";
}

async function checkExistingSession() {
  try {
    const data = await fetchJSON("/api/auth/me");
    state.user = data.item || null;
    if (!state.user) {
      return;
    }
    if (Number(state.user.must_change_password || 0) === 1) {
      showChangePasswordForm("");
      setMessage("当前账号需先修改密码", "error");
      return;
    }
    goHome();
  } catch (err) {
    if (err.status === 401) {
      showLoginForm();
      return;
    }
    setMessage(err.message || "登录状态检查失败", "error");
  }
}

async function handleLogin(event) {
  event.preventDefault();
  setMessage("");
  const username = els.username.value.trim();
  const password = els.password.value;
  if (!username || !password) {
    setMessage("请输入用户名和密码", "error");
    return;
  }

  try {
    const data = await fetchJSON("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    state.user = data.item || null;
    if (state.user && Number(state.user.must_change_password || 0) === 1) {
      showChangePasswordForm(password);
      setMessage("首次登录请先修改默认密码", "success");
      return;
    }
    goHome();
  } catch (err) {
    setMessage(err.message || "登录失败", "error");
  }
}

async function handleChangePassword(event) {
  event.preventDefault();
  setMessage("");

  const oldPassword = els.oldPassword.value;
  const newPassword = els.newPassword.value;
  const confirmPassword = els.confirmPassword.value;

  if (!oldPassword || !newPassword || !confirmPassword) {
    setMessage("请填写完整密码信息", "error");
    return;
  }
  if (newPassword.length < 8) {
    setMessage("新密码至少 8 位", "error");
    return;
  }
  if (newPassword !== confirmPassword) {
    setMessage("两次输入的新密码不一致", "error");
    return;
  }

  try {
    await fetchJSON("/api/auth/change-password", {
      method: "PUT",
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
    });
    setMessage("密码修改成功，正在进入系统", "success");
    setTimeout(() => goHome(), 300);
  } catch (err) {
    if (err.status === 401) {
      showLoginForm();
      setMessage("登录已失效，请重新登录", "error");
      return;
    }
    setMessage(err.message || "修改密码失败", "error");
  }
}

els.loginForm.addEventListener("submit", handleLogin);
els.changeForm.addEventListener("submit", handleChangePassword);

checkExistingSession();
