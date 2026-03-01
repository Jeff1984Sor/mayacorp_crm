const output = document.getElementById("output");
const toast = document.getElementById("toast");

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

function renderSummary(summary) {
  renderList("salesOrdersList", summary.sales_orders || [], (item) =>
    `#${item.id} | ${item.status} | R$ ${Number(item.total_amount).toFixed(2)}<br>
    <button onclick="updateSalesOrderStatus(${item.id})">Atualizar status</button>
    <button onclick="deleteSalesOrder(${item.id})">Excluir</button>`
  );
  renderList("proposalsList", summary.proposals || [], (item) =>
    `#${item.id} | ${item.title}<br>${item.pdf_path || "sem pdf"}<br>
    <button onclick="renameProposal(${item.id})">Renomear</button>
    <button onclick="deleteProposal(${item.id})">Excluir</button>`
  );
  renderList("contractsList", summary.contracts || [], (item) =>
    `#${item.id} | ${item.title} | ${item.status}<br>
    <button onclick="renameContract(${item.id})">Renomear</button>
    <button onclick="deleteContract(${item.id})">Excluir</button>`
  );
  renderList("leadsList", summary.leads || [], (item) =>
    `#${item.id} | ${item.name}<br>${item.email || "-"}<br>
    <button onclick="renameLead(${item.id})">Editar</button>
    <button onclick="deleteLead(${item.id})">Excluir</button>`
  );
  renderList("clientsList", summary.clients || [], (item) =>
    `#${item.id} | ${item.name}<br>${item.email || "-"}<br>
    <button onclick="renameClient(${item.id})">Editar</button>
    <button onclick="deleteClient(${item.id})">Excluir</button>`
  );
  const meta = [];
  meta.push(`Categorias: ${summary.finance?.category_count || 0}`);
  meta.push(`AR total: R$ ${Number(summary.finance?.receivable_total || 0).toFixed(2)}`);
  meta.push(`AR pendente: R$ ${Number(summary.finance?.receivable_pending || 0).toFixed(2)}`);
  if (summary.whatsapp) {
    meta.push(
      `WhatsApp: ${summary.whatsapp.status} (${summary.whatsapp.provider_session_id || "-"})<br>
      <button onclick="updateWhatsappSessionStatus()">Atualizar status</button>`
    );
  } else {
    meta.push("WhatsApp: sem sessao");
  }
  renderList("workspaceMeta", meta, (item) => item);
  renderList("receivablesList", summary.receivables || [], (item) =>
    `#${item.id} | ${item.status} | R$ ${Number(item.amount).toFixed(2)}<br>
    <button onclick="updateReceivableStatus(${item.id})">Atualizar status</button>
    <button onclick="deleteReceivable(${item.id})">Excluir</button>`
  );
  renderList("payablesList", summary.payables || [], (item) =>
    `#${item.id} | ${item.status} | R$ ${Number(item.amount).toFixed(2)}<br>
    <button onclick="updatePayableStatus(${item.id})">Atualizar status</button>
    <button onclick="deletePayable(${item.id})">Excluir</button>`
  );
  renderList("messagesList", summary.messages || [], (item) =>
    `#${item.id} | ${item.direction} | ${item.status}<br>${item.body}<br>
    <button onclick="updateMessageStatus(${item.id})">Atualizar status</button>`
  );
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
  const query = new URLSearchParams({
    page: document.getElementById("summaryPage").value || "1",
    page_size: document.getElementById("summaryPageSize").value || "5"
  });
  const filterValue = document.getElementById("summaryQuery").value.trim();
  if (filterValue) {
    query.set("q", filterValue);
  }
  const response = await fetch("/admin/panel/" + slug + "/summary?" + query.toString(), {
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

async function createReceivable() {
  const slug = document.getElementById("tenantSlug").value.trim();
  const response = await fetch(`/admin/panel/${slug}/finance/receivable`, {
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
  const slug = document.getElementById("tenantSlug").value.trim();
  const query = new URLSearchParams();
  const status = document.getElementById("financeFilterStatus").value.trim();
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
  const response = await fetch(`/admin/panel/${slug}/finance/receivables?` + query.toString(), {
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
  const slug = document.getElementById("tenantSlug").value.trim();
  const response = await fetch(`/admin/panel/${slug}/finance/payable`, {
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
  const slug = document.getElementById("tenantSlug").value.trim();
  const query = new URLSearchParams();
  const status = document.getElementById("financeFilterStatus").value.trim();
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
  const response = await fetch(`/admin/panel/${slug}/finance/payables?` + query.toString(), {
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

async function sendWhatsapp() {
  const slug = document.getElementById("tenantSlug").value.trim();
  const response = await fetch(`/admin/panel/${slug}/whatsapp/send`, {
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
  const slug = document.getElementById("tenantSlug").value.trim();
  const status = window.prompt("Novo status da sessao WhatsApp:", "connected");
  if (!status) {
    return;
  }
  const response = await fetch(`/admin/panel/${slug}/whatsapp-session/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ status })
  });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function updateReceivableStatus(id) {
  const slug = document.getElementById("tenantSlug").value.trim();
  const status = window.prompt("Novo status da conta a receber:", "paid");
  if (!status) {
    return;
  }
  const response = await fetch(`/admin/panel/${slug}/finance/receivable/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ status })
  });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function deleteReceivable(id) {
  const slug = document.getElementById("tenantSlug").value.trim();
  const response = await fetch(`/admin/panel/${slug}/finance/receivable/${id}`, {
    method: "DELETE",
    credentials: "same-origin"
  });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function updatePayableStatus(id) {
  const slug = document.getElementById("tenantSlug").value.trim();
  const status = window.prompt("Novo status da conta a pagar:", "paid");
  if (!status) {
    return;
  }
  const response = await fetch(`/admin/panel/${slug}/finance/payable/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ status })
  });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function deletePayable(id) {
  const slug = document.getElementById("tenantSlug").value.trim();
  const response = await fetch(`/admin/panel/${slug}/finance/payable/${id}`, {
    method: "DELETE",
    credentials: "same-origin"
  });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function updateMessageStatus(id) {
  const slug = document.getElementById("tenantSlug").value.trim();
  const status = window.prompt("Novo status da mensagem:", "read");
  if (!status) {
    return;
  }
  const response = await fetch(`/admin/panel/${slug}/message/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ status })
  });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function renameLead(id) {
  const name = window.prompt("Novo nome do lead:");
  if (!name) {
    return;
  }
  const slug = document.getElementById("tenantSlug").value.trim();
  const response = await fetch(`/admin/panel/${slug}/lead/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ name, email: null, phone: null })
  });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function deleteLead(id) {
  const slug = document.getElementById("tenantSlug").value.trim();
  const response = await fetch(`/admin/panel/${slug}/lead/${id}`, {
    method: "DELETE",
    credentials: "same-origin"
  });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function renameClient(id) {
  const name = window.prompt("Novo nome do client:");
  if (!name) {
    return;
  }
  const slug = document.getElementById("tenantSlug").value.trim();
  const response = await fetch(`/admin/panel/${slug}/client/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ name, email: null, phone: null })
  });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function deleteClient(id) {
  const slug = document.getElementById("tenantSlug").value.trim();
  const response = await fetch(`/admin/panel/${slug}/client/${id}`, {
    method: "DELETE",
    credentials: "same-origin"
  });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function updateSalesOrderStatus(id) {
  const status = window.prompt("Novo status do pedido:", "confirmed");
  if (!status) {
    return;
  }
  const slug = document.getElementById("tenantSlug").value.trim();
  const response = await fetch(`/admin/panel/${slug}/sales-order/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ status })
  });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function deleteSalesOrder(id) {
  const slug = document.getElementById("tenantSlug").value.trim();
  const response = await fetch(`/admin/panel/${slug}/sales-order/${id}`, {
    method: "DELETE",
    credentials: "same-origin"
  });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function renameProposal(id) {
  const title = window.prompt("Novo titulo da proposta:");
  if (!title) {
    return;
  }
  const slug = document.getElementById("tenantSlug").value.trim();
  const response = await fetch(`/admin/panel/${slug}/proposal/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ title, sales_order_id: toOptionalInt(document.getElementById("proposalOrderId").value) })
  });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function deleteProposal(id) {
  const slug = document.getElementById("tenantSlug").value.trim();
  const response = await fetch(`/admin/panel/${slug}/proposal/${id}`, {
    method: "DELETE",
    credentials: "same-origin"
  });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function renameContract(id) {
  const title = window.prompt("Novo titulo do contrato:");
  if (!title) {
    return;
  }
  const slug = document.getElementById("tenantSlug").value.trim();
  const response = await fetch(`/admin/panel/${slug}/contract/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ title, sales_order_id: toOptionalInt(document.getElementById("contractOrderId").value) })
  });
  await showResult(response);
  await loadWorkspaceSummary();
}

async function deleteContract(id) {
  const slug = document.getElementById("tenantSlug").value.trim();
  const response = await fetch(`/admin/panel/${slug}/contract/${id}`, {
    method: "DELETE",
    credentials: "same-origin"
  });
  await showResult(response);
  await loadWorkspaceSummary();
}
