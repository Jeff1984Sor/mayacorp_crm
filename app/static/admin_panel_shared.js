const output = document.getElementById("output");
const toast = document.getElementById("toast");
const panelCache = window.__PANEL_CACHE__ || (window.__PANEL_CACHE__ = {});

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
