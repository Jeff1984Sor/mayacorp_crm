const output = document.getElementById("output");
const toast = document.getElementById("toast");
const panelCache = window.__PANEL_CACHE__ || (window.__PANEL_CACHE__ = {});
const panelEditor = window.__PANEL_EDITOR__ || (window.__PANEL_EDITOR__ = {});
const panelInspector = window.__PANEL_INSPECTOR__ || (window.__PANEL_INSPECTOR__ = { tab: "summary", detail: null });
const panelAuth = window.__PANEL_AUTH__ || (window.__PANEL_AUTH__ = { centralToken: null, tenantToken: null, tenantSlug: null });
const nativeFetch = window.fetch.bind(window);

function unwrapPayload(parsed) {
  if (parsed && Object.prototype.hasOwnProperty.call(parsed, "ok") && Object.prototype.hasOwnProperty.call(parsed, "data")) {
    return parsed.data;
  }
  return parsed;
}

function showToast(message, type = "success") {
  if (!toast) {
    return;
  }
  toast.textContent = message;
  toast.className = `toast show ${type}`;
  window.clearTimeout(showToast._timer);
  showToast._timer = window.setTimeout(() => {
    toast.className = "toast";
  }, 3000);
}

function handlePanelSessionFailure(detail) {
  if (detail !== "Panel central session required.") {
    return false;
  }
  setPanelVisibility(false);
  switchPanelSection("home");
  if (output) {
    output.textContent = detail;
  }
  showToast("Sua sessao central expirou. Entre novamente no painel.", "error");
  return true;
}

function renderList(targetId, items, renderItem) {
  const target = document.getElementById(targetId);
  if (!target) {
    return;
  }
  if (!items || items.length === 0) {
    target.innerHTML = '<div class="list-item">Sem registros.</div>';
    return;
  }
  target.innerHTML = items.map((item) => `<div class="list-item">${renderItem(item)}</div>`).join("");
}

async function showResult(response) {
  const contentType = response.headers.get("content-type") || "";
  const text = await response.text();
  if (contentType.includes("application/json")) {
    try {
      const parsed = JSON.parse(text);
      output.textContent = JSON.stringify(parsed, null, 2);
      const payload = unwrapPayload(parsed);
      if (response.ok) {
        showToast(parsed.message || "Operacao concluida.", "success");
      } else {
        if (handlePanelSessionFailure(parsed.detail || "")) {
          return null;
        }
        showToast(parsed.detail || "Falha na operacao.", "error");
      }
      if (payload && payload.sales_orders && payload.proposals && payload.contracts) {
        renderSummary(payload);
      }
      return payload;
    } catch (error) {}
  }
  output.textContent = text;
  showToast(response.ok ? "Operacao concluida." : text, response.ok ? "success" : "error");
  return text;
}

function toOptionalInt(value) {
  const clean = (value || "").trim();
  return clean ? Number(clean) : null;
}

function getTenantSlug() {
  return document.getElementById("tenantSlug").value.trim();
}

function selectedValue(id, fallback = "") {
  const element = document.getElementById(id);
  if (!element) {
    return fallback;
  }
  const value = (element.value || "").trim();
  return value || fallback;
}

function setPanelCache(key, value) {
  panelCache[key] = value;
  return value;
}

function getPanelCache(key) {
  return panelCache[key];
}

function buildCentralRequestOptions(extra = {}) {
  const headers = { ...(extra.headers || {}) };
  if (panelAuth.centralToken) {
    headers["X-Panel-Central-Token"] = panelAuth.centralToken;
  }
  return { ...extra, headers, credentials: "same-origin" };
}

window.fetch = (input, init = {}) => {
  const url = typeof input === "string" ? input : String(input?.url || "");
  const headers = new Headers(init.headers || {});
  if (url.startsWith("/admin/panel") && panelAuth.centralToken && !headers.has("X-Panel-Central-Token")) {
    headers.set("X-Panel-Central-Token", panelAuth.centralToken);
  }
  if (
    url.startsWith("/admin/panel/") &&
    panelAuth.tenantToken &&
    panelAuth.tenantSlug &&
    !headers.has("X-Panel-Tenant-Token")
  ) {
    headers.set("X-Panel-Tenant-Token", panelAuth.tenantToken);
    headers.set("X-Panel-Tenant-Slug", panelAuth.tenantSlug);
  }
  return nativeFetch(input, { ...init, headers, credentials: init.credentials || "same-origin" });
};

function setPanelVisibility(isAuthenticated) {
  const authScreen = document.getElementById("authScreen");
  const appShell = document.getElementById("appShell");
  if (authScreen) {
    authScreen.classList.toggle("hidden", isAuthenticated);
  }
  if (appShell) {
    appShell.classList.toggle("hidden", !isAuthenticated);
  }
}

function switchPanelSection(section, trigger = null) {
  document.querySelectorAll(".panel-section").forEach((node) => {
    node.classList.toggle("active", node.dataset.section === section);
  });
  document.querySelectorAll(".menu-btn").forEach((node) => {
    node.classList.toggle("active", node.dataset.panelSection === section);
  });
  if (trigger && trigger.classList) {
    trigger.classList.add("active");
  }
}

function switchWorkspaceFlowTab(tab, trigger = null) {
  document.querySelectorAll(".workspace-tab-panel").forEach((node) => {
    node.classList.toggle("active", node.dataset.workspacePanel === tab);
  });
  document.querySelectorAll(".workspace-tab").forEach((node) => {
    node.classList.toggle("active", node.dataset.workspaceTab === tab);
  });
  if (trigger && trigger.classList) {
    trigger.classList.add("active");
  }
}

function toggleSideNav() {
  const shell = document.getElementById("appShell");
  if (!shell) {
    return;
  }
  shell.classList.toggle("nav-collapsed");
  const toggle = document.querySelector(".nav-toggle");
  if (toggle) {
    toggle.textContent = shell.classList.contains("nav-collapsed") ? "Expandir menu" : "Recolher menu";
  }
}

function activateSectionAndScroll(section, targetId = "") {
  const trigger = document.querySelector(`.menu-btn[data-panel-section="${section}"]`);
  switchPanelSection(section, trigger);
  if (!targetId) {
    return;
  }
  const target = document.getElementById(targetId);
  if (target && typeof target.scrollIntoView === "function") {
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function openEditorDrawer(config) {
  const drawer = document.getElementById("editorDrawer");
  if (!drawer) {
    return;
  }
  panelEditor.entity = config.entity;
  panelEditor.itemId = config.id;
  panelEditor.onSubmit = config.onSubmit;
  panelEditor.onSuccess = config.onSuccess;
  document.getElementById("editorDrawerTitle").textContent = config.title || "Editar item";
  document.getElementById("editorDrawerEntity").value = config.entity || "";
  document.getElementById("editorDrawerItemId").value = String(config.id || "");
  const nameField = document.getElementById("editorNameField");
  const nameInput = document.getElementById("editorDrawerName");
  if (config.mode === "status") {
    nameField.classList.add("hidden");
  } else {
    nameField.classList.remove("hidden");
    nameInput.value = config.value || "";
    nameInput.placeholder = config.placeholder || "Digite o novo valor";
  }
  const statusField = document.getElementById("editorStatusField");
  const statusSelect = document.getElementById("editorDrawerStatus");
  statusSelect.innerHTML = "";
  if (config.mode === "status") {
    statusField.classList.remove("hidden");
    (config.options || []).forEach((optionValue) => {
      const option = document.createElement("option");
      option.value = optionValue;
      option.textContent = optionValue;
      if (optionValue === config.value) {
        option.selected = true;
      }
      statusSelect.appendChild(option);
    });
  } else {
    statusField.classList.add("hidden");
  }
  const hint = document.getElementById("editorDrawerHint");
  hint.textContent = config.hint || "Ajuste o valor e confirme para aplicar a alteracao.";
  drawer.classList.remove("hidden");
}

function closeEditorDrawer() {
  const drawer = document.getElementById("editorDrawer");
  if (!drawer) {
    return;
  }
  drawer.classList.add("hidden");
}
