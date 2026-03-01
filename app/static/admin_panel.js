const output = document.getElementById("output");

function syncStoredTokens() {
  const centralToken = sessionStorage.getItem("mayacorp_central_token") || "";
  const tenantToken = sessionStorage.getItem("mayacorp_tenant_token") || "";
  document.getElementById("centralToken").value = centralToken;
  document.getElementById("tenantToken").value = tenantToken;
}

async function showResult(response) {
  const contentType = response.headers.get("content-type") || "";
  const text = await response.text();
  if (contentType.includes("application/json")) {
    try {
      const parsed = JSON.parse(text);
      output.textContent = JSON.stringify(parsed, null, 2);
      return parsed;
    } catch (error) {}
  }
  output.textContent = text;
  return text;
}

function authHeader(token) {
  const clean = (token || "").trim();
  return clean ? { "Authorization": "Bearer " + clean } : {};
}

function toOptionalInt(value) {
  const clean = (value || "").trim();
  return clean ? Number(clean) : null;
}

async function centralLogin() {
  const response = await fetch("/central/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: document.getElementById("centralEmail").value,
      password: document.getElementById("centralPassword").value
    })
  });
  const payload = await showResult(response);
  if (payload && payload.access_token) {
    sessionStorage.setItem("mayacorp_central_token", payload.access_token);
    document.getElementById("centralToken").value = payload.access_token;
  }
}

async function centralDashboard() {
  const response = await fetch("/central/dashboard", {
    headers: authHeader(document.getElementById("centralToken").value)
  });
  await showResult(response);
}

async function createTenant() {
  const response = await fetch("/admin/panel/tenant", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeader(document.getElementById("centralToken").value)
    },
    body: JSON.stringify({
      company_name: document.getElementById("companyName").value,
      workspace_slug: document.getElementById("workspaceSlug").value,
      admin_name: document.getElementById("tenantAdminName").value,
      admin_email: document.getElementById("tenantAdminEmail").value,
      admin_password: document.getElementById("tenantAdminPassword").value
    })
  });
  await showResult(response);
}

async function tenantLogin() {
  const slug = document.getElementById("tenantSlug").value.trim();
  const response = await fetch("/tenant/" + slug + "/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: document.getElementById("tenantEmail").value,
      password: document.getElementById("tenantPassword").value
    })
  });
  const payload = await showResult(response);
  if (payload && payload.access_token) {
    sessionStorage.setItem("mayacorp_tenant_token", payload.access_token);
    document.getElementById("tenantToken").value = payload.access_token;
  }
}

async function tenantHealth() {
  const slug = document.getElementById("tenantSlug").value.trim();
  const response = await fetch("/tenant/" + slug + "/health", {
    headers: authHeader(document.getElementById("tenantToken").value)
  });
  await showResult(response);
}

async function createSalesOrder() {
  const slug = document.getElementById("tenantSlug").value.trim();
  const response = await fetch("/admin/panel/" + slug + "/sales-order", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeader(document.getElementById("tenantToken").value)
    },
    body: JSON.stringify({
      title: document.getElementById("salesDescription").value,
      quantity: Number(document.getElementById("salesQuantity").value || "1"),
      unit_price: Number(document.getElementById("salesPrice").value || "0"),
      first_due_date: document.getElementById("salesDueDate").value
    })
  });
  const payload = await showResult(response);
  if (payload && payload.id) {
    document.getElementById("proposalOrderId").value = payload.id;
    document.getElementById("contractOrderId").value = payload.id;
  }
}

async function createProposal() {
  const slug = document.getElementById("tenantSlug").value.trim();
  const response = await fetch("/admin/panel/" + slug + "/proposal", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeader(document.getElementById("tenantToken").value)
    },
    body: JSON.stringify({
      title: document.getElementById("proposalTitle").value,
      sales_order_id: toOptionalInt(document.getElementById("proposalOrderId").value)
    })
  });
  await showResult(response);
}

async function createContract() {
  const slug = document.getElementById("tenantSlug").value.trim();
  const response = await fetch("/admin/panel/" + slug + "/contract", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeader(document.getElementById("tenantToken").value)
    },
    body: JSON.stringify({
      title: document.getElementById("contractTitle").value,
      sales_order_id: toOptionalInt(document.getElementById("contractOrderId").value)
    })
  });
  const payload = await showResult(response);
  if (payload && payload.id) {
    document.getElementById("signContractId").value = payload.id;
  }
}

async function signContract() {
  const slug = document.getElementById("tenantSlug").value.trim();
  const response = await fetch("/admin/panel/" + slug + "/contract/sign", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeader(document.getElementById("tenantToken").value)
    },
    body: JSON.stringify({
      contract_id: Number(document.getElementById("signContractId").value || "0"),
      file_name: document.getElementById("signFileName").value,
      content: document.getElementById("signContent").value
    })
  });
  await showResult(response);
}

async function loadWorkspaceSummary() {
  const slug = document.getElementById("tenantSlug").value.trim();
  const response = await fetch("/admin/panel/" + slug + "/summary", {
    headers: authHeader(document.getElementById("tenantToken").value)
  });
  await showResult(response);
}

async function createFinanceCategory() {
  const slug = document.getElementById("tenantSlug").value.trim();
  const response = await fetch("/admin/panel/" + slug + "/finance-category", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeader(document.getElementById("tenantToken").value)
    },
    body: JSON.stringify({
      name: document.getElementById("financeCategoryName").value,
      entry_type: document.getElementById("financeEntryType").value
    })
  });
  await showResult(response);
}

async function connectWhatsapp() {
  const slug = document.getElementById("tenantSlug").value.trim();
  const response = await fetch("/admin/panel/" + slug + "/whatsapp-session", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeader(document.getElementById("tenantToken").value)
    },
    body: JSON.stringify({
      provider_session_id: document.getElementById("whatsappSessionId").value
    })
  });
  await showResult(response);
}

syncStoredTokens();
