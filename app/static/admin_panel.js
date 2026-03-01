const output = document.getElementById("output");

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

function renderSummary(summary) {
  renderList("salesOrdersList", summary.sales_orders || [], (item) =>
    `#${item.id} | ${item.status} | R$ ${Number(item.total_amount).toFixed(2)}`
  );
  renderList("proposalsList", summary.proposals || [], (item) =>
    `#${item.id} | ${item.title}<br>${item.pdf_path || "sem pdf"}`
  );
  renderList("contractsList", summary.contracts || [], (item) =>
    `#${item.id} | ${item.title} | ${item.status}`
  );
  renderList("leadsList", summary.leads || [], (item) =>
    `#${item.id} | ${item.name}<br>${item.email || "-"}`
  );
  renderList("clientsList", summary.clients || [], (item) =>
    `#${item.id} | ${item.name}<br>${item.email || "-"}`
  );
  const meta = [];
  meta.push(`Categorias: ${summary.finance?.category_count || 0}`);
  meta.push(`AR total: R$ ${Number(summary.finance?.receivable_total || 0).toFixed(2)}`);
  meta.push(`AR pendente: R$ ${Number(summary.finance?.receivable_pending || 0).toFixed(2)}`);
  if (summary.whatsapp) {
    meta.push(`WhatsApp: ${summary.whatsapp.status} (${summary.whatsapp.provider_session_id || "-"})`);
  } else {
    meta.push("WhatsApp: sem sessao");
  }
  renderList("workspaceMeta", meta, (item) => item);
}

async function showResult(response) {
  const contentType = response.headers.get("content-type") || "";
  const text = await response.text();
  if (contentType.includes("application/json")) {
    try {
      const parsed = JSON.parse(text);
      output.textContent = JSON.stringify(parsed, null, 2);
      if (parsed && parsed.sales_orders && parsed.proposals && parsed.contracts) {
        renderSummary(parsed);
      }
      return parsed;
    } catch (error) {}
  }
  output.textContent = text;
  return text;
}

function toOptionalInt(value) {
  const clean = (value || "").trim();
  return clean ? Number(clean) : null;
}

async function centralLogin() {
  const response = await fetch("/admin/panel/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({
      email: document.getElementById("centralEmail").value,
      password: document.getElementById("centralPassword").value
    })
  });
  await showResult(response);
}

async function logoutPanel() {
  const response = await fetch("/admin/panel/logout", {
    method: "POST",
    credentials: "same-origin"
  });
  await showResult(response);
}

async function centralDashboard() {
  const response = await fetch("/admin/panel/central/dashboard", {
    credentials: "same-origin"
  });
  await showResult(response);
}

async function createTenant() {
  const response = await fetch("/admin/panel/tenant", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
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
  const response = await fetch("/admin/panel/" + slug + "/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({
      email: document.getElementById("tenantEmail").value,
      password: document.getElementById("tenantPassword").value
    })
  });
  await showResult(response);
}

async function tenantHealth() {
  const slug = document.getElementById("tenantSlug").value.trim();
  const response = await fetch("/admin/panel/" + slug + "/health", {
    credentials: "same-origin"
  });
  await showResult(response);
}

async function createLead() {
  const slug = document.getElementById("tenantSlug").value.trim();
  const response = await fetch("/admin/panel/" + slug + "/lead", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({
      name: document.getElementById("leadName").value,
      email: document.getElementById("leadEmail").value
    })
  });
  await showResult(response);
}

async function createClient() {
  const slug = document.getElementById("tenantSlug").value.trim();
  const response = await fetch("/admin/panel/" + slug + "/client", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({
      name: document.getElementById("clientName").value,
      email: document.getElementById("clientEmail").value
    })
  });
  await showResult(response);
}

async function createSalesOrder() {
  const slug = document.getElementById("tenantSlug").value.trim();
  const response = await fetch("/admin/panel/" + slug + "/sales-order", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
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
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
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
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
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
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
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
    credentials: "same-origin"
  });
  await showResult(response);
}

async function createFinanceCategory() {
  const slug = document.getElementById("tenantSlug").value.trim();
  const response = await fetch("/admin/panel/" + slug + "/finance-category", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
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
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({
      provider_session_id: document.getElementById("whatsappSessionId").value
    })
  });
  await showResult(response);
}
