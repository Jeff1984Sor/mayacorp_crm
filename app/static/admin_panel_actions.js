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
  const response = await fetch("/admin/panel/logout", { method: "POST", credentials: "same-origin" });
  await showResult(response);
}

async function centralDashboard() {
  const response = await fetch("/admin/panel/central/dashboard", { credentials: "same-origin" });
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
  const slug = getTenantSlug();
  const response = await fetch(`/admin/panel/${slug}/login`, {
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
  const response = await fetch(`/admin/panel/${getTenantSlug()}/health`, { credentials: "same-origin" });
  await showResult(response);
}

async function createLead() {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/lead`, {
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
  const response = await fetch(`/admin/panel/${getTenantSlug()}/client`, {
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
  const response = await fetch(`/admin/panel/${getTenantSlug()}/sales-order`, {
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
  const response = await fetch(`/admin/panel/${getTenantSlug()}/proposal`, {
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
  const response = await fetch(`/admin/panel/${getTenantSlug()}/contract`, {
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
  const response = await fetch(`/admin/panel/${getTenantSlug()}/contract/sign`, {
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
  const query = new URLSearchParams({
    page: document.getElementById("summaryPage").value || "1",
    page_size: document.getElementById("summaryPageSize").value || "5"
  });
  const filterValue = document.getElementById("summaryQuery").value.trim();
  const documentFilter = document.getElementById("documentQuery").value.trim();
  const messageStatus = selectedValue("messageStatusFilter");
  const messageDirection = selectedValue("messageDirectionFilter");
  if (filterValue) {
    query.set("q", filterValue);
  }
  if (documentFilter) {
    query.set("document_q", documentFilter);
  }
  if (messageStatus) {
    query.set("message_status", messageStatus);
  }
  if (messageDirection) {
    query.set("message_direction", messageDirection);
  }
  const response = await fetch(`/admin/panel/${getTenantSlug()}/summary?${query.toString()}`, { credentials: "same-origin" });
  await showResult(response);
}

async function createFinanceCategory() {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/finance-category`, {
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

function buildFinanceQuery() {
  const query = new URLSearchParams();
  const status = selectedValue("financeFilterStatus");
  const category = document.getElementById("financeFilterCategory").value.trim();
  const dueFrom = document.getElementById("financeFilterFrom").value.trim();
  const dueTo = document.getElementById("financeFilterTo").value.trim();
  if (status) {
    query.set("status", status);
  }
  if (category) {
    query.set("category", category);
  }
  if (dueFrom) {
    query.set("due_from", dueFrom);
  }
  if (dueTo) {
    query.set("due_to", dueTo);
  }
  return query;
}

async function createReceivable() {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/finance/receivable`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({
      amount: Number(document.getElementById("receivableAmount").value || "0"),
      due_date: document.getElementById("financeDueDate").value,
      category: document.getElementById("financeCategoryName").value,
      cost_center: "Comercial",
      status: "pending"
    })
  });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function loadReceivables() {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/finance/receivables?${buildFinanceQuery().toString()}`, {
    credentials: "same-origin"
  });
  const payload = await showResult(response);
  renderList("receivablesList", (payload && payload.items) || [], (item) =>
    `#${item.id} | ${item.status} | R$ ${Number(item.amount).toFixed(2)}<br>
    ${item.category || "-"} | ${item.due_date}<br>
    <button onclick="updateReceivableStatus(${item.id})">Atualizar status</button>
    <button onclick="deleteReceivable(${item.id})">Excluir</button>`
  );
}

async function createPayable() {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/finance/payable`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({
      amount: Number(document.getElementById("payableAmount").value || "0"),
      due_date: document.getElementById("financeDueDate").value,
      category: "Operacional",
      cost_center: "Operacoes",
      status: "pending"
    })
  });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function loadPayables() {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/finance/payables?${buildFinanceQuery().toString()}`, {
    credentials: "same-origin"
  });
  const payload = await showResult(response);
  renderList("payablesList", (payload && payload.items) || [], (item) =>
    `#${item.id} | ${item.status} | R$ ${Number(item.amount).toFixed(2)}<br>
    ${item.category || "-"} | ${item.due_date}<br>
    <button onclick="updatePayableStatus(${item.id})">Atualizar status</button>
    <button onclick="deletePayable(${item.id})">Excluir</button>`
  );
}

async function connectWhatsapp() {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/whatsapp-session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ provider_session_id: document.getElementById("whatsappSessionId").value })
  });
  await showResult(response);
}

async function sendWhatsapp() {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/whatsapp/send`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({
      body: document.getElementById("whatsappBody").value,
      client_id: toOptionalInt(document.getElementById("whatsappClientId").value),
      lead_id: toOptionalInt(document.getElementById("whatsappLeadId").value)
    })
  });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function updateWhatsappSessionStatus() {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/whatsapp-session/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ status: selectedValue("whatsappSessionStatus", "connected") })
  });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function updateReceivableStatus(id) {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/finance/receivable/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ status: selectedValue("receivableStatusUpdate", "paid") })
  });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function deleteReceivable(id) {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/finance/receivable/${id}`, {
    method: "DELETE",
    credentials: "same-origin"
  });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function updatePayableStatus(id) {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/finance/payable/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ status: selectedValue("payableStatusUpdate", "paid") })
  });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function deletePayable(id) {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/finance/payable/${id}`, {
    method: "DELETE",
    credentials: "same-origin"
  });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function updateMessageStatus(id) {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/message/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ status: selectedValue("messageStatusUpdate", "read") })
  });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function renameLead(id) {
  const name = window.prompt("Novo nome do lead:");
  if (!name) {
    return;
  }
  const response = await fetch(`/admin/panel/${getTenantSlug()}/lead/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ name, email: null, phone: null })
  });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function deleteLead(id) {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/lead/${id}`, { method: "DELETE", credentials: "same-origin" });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function renameClient(id) {
  const name = window.prompt("Novo nome do client:");
  if (!name) {
    return;
  }
  const response = await fetch(`/admin/panel/${getTenantSlug()}/client/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ name, email: null, phone: null })
  });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function deleteClient(id) {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/client/${id}`, { method: "DELETE", credentials: "same-origin" });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function updateSalesOrderStatus(id) {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/sales-order/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ status: selectedValue("salesOrderStatusUpdate", "confirmed") })
  });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function deleteSalesOrder(id) {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/sales-order/${id}`, { method: "DELETE", credentials: "same-origin" });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function renameProposal(id) {
  const title = window.prompt("Novo titulo da proposta:");
  if (!title) {
    return;
  }
  const response = await fetch(`/admin/panel/${getTenantSlug()}/proposal/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ title, sales_order_id: toOptionalInt(document.getElementById("proposalOrderId").value) })
  });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function deleteProposal(id) {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/proposal/${id}`, { method: "DELETE", credentials: "same-origin" });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function renameContract(id) {
  const title = window.prompt("Novo titulo do contrato:");
  if (!title) {
    return;
  }
  const response = await fetch(`/admin/panel/${getTenantSlug()}/contract/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ title, sales_order_id: toOptionalInt(document.getElementById("contractOrderId").value) })
  });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function deleteContract(id) {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/contract/${id}`, { method: "DELETE", credentials: "same-origin" });
  await showResult(response);
  await loadWorkspaceSummary();
}
