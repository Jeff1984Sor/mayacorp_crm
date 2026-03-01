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
  await loadLeadsOnly();
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
  await loadClientsOnly();
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
  await loadOrdersSummary();
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
  await loadProposalsOnly();
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
  await loadContractsOnly();
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
  await loadContractsOnly();
}

async function loadWorkspaceSummary() {
  const query = new URLSearchParams({
    page: document.getElementById("summaryPage").value || "1",
    page_size: document.getElementById("summaryPageSize").value || "5",
    leads_page: document.getElementById("leadsPage").value || "1",
    leads_page_size: document.getElementById("leadsPageSize").value || "5",
    clients_page: document.getElementById("clientsPage").value || "1",
    clients_page_size: document.getElementById("clientsPageSize").value || "5",
    documents_page: document.getElementById("documentsPage").value || "1",
    documents_page_size: document.getElementById("documentsPageSize").value || "5",
    messages_page: document.getElementById("messagesPage").value || "1",
    messages_page_size: document.getElementById("messagesPageSize").value || "5"
  });
  const filterValue = document.getElementById("summaryQuery").value.trim();
  const peopleEmail = document.getElementById("peopleEmailFilter").value.trim();
  const peoplePhone = document.getElementById("peoplePhoneFilter").value.trim();
  const orderStatus = selectedValue("orderStatusFilter");
  const orderSortBy = selectedValue("orderSortBy", "id");
  const orderSortDir = selectedValue("orderSortDir", "desc");
  const documentFilter = document.getElementById("documentQuery").value.trim();
  const contractStatus = selectedValue("contractStatusFilter");
  const documentSortBy = selectedValue("documentSortBy", "id");
  const documentSortDir = selectedValue("documentSortDir", "desc");
  const peopleSortBy = selectedValue("peopleSortBy", "id");
  const peopleSortDir = selectedValue("peopleSortDir", "desc");
  const messageStatus = selectedValue("messageStatusFilter");
  const messageDirection = selectedValue("messageDirectionFilter");
  if (filterValue) {
    query.set("q", filterValue);
  }
  if (orderStatus) {
    query.set("order_status", orderStatus);
  }
  if (peopleEmail) {
    query.set("people_email", peopleEmail);
  }
  if (peoplePhone) {
    query.set("people_phone", peoplePhone);
  }
  query.set("order_sort_by", orderSortBy);
  query.set("order_sort_dir", orderSortDir);
  query.set("people_sort_by", peopleSortBy);
  query.set("people_sort_dir", peopleSortDir);
  if (documentFilter) {
    query.set("document_q", documentFilter);
  }
  if (contractStatus) {
    query.set("contract_status", contractStatus);
  }
  query.set("document_sort_by", documentSortBy);
  query.set("document_sort_dir", documentSortDir);
  if (messageStatus) {
    query.set("message_status", messageStatus);
  }
  if (messageDirection) {
    query.set("message_direction", messageDirection);
  }
  const response = await fetch(`/admin/panel/${getTenantSlug()}/summary?${query.toString()}`, { credentials: "same-origin" });
  const payload = await showResult(response);
  if (payload) {
    setPanelCache("summary", payload);
  }
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

function buildScopedFinanceQuery(pageId, pageSizeId) {
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
  query.set("page", document.getElementById(pageId).value || "1");
  query.set("page_size", document.getElementById(pageSizeId).value || "10");
  query.set("sort_by", selectedValue("financeSortBy", "due_date"));
  query.set("sort_dir", selectedValue("financeSortDir", "asc"));
  return query;
}

function buildFinanceQuery() {
  return buildScopedFinanceQuery("financePage", "financePageSize");
}

function clearPanelCache(keys) {
  if (!keys || keys.length === 0) {
    return;
  }
  keys.forEach((key) => setPanelCache(key, null));
}

function invalidatePanelDomains(...domains) {
  const constants = window.PANEL_CONSTANTS || PANEL_CONSTANTS;
  const keys = new Set();
  domains.forEach((domain) => {
    const mapped = constants.cacheKeysByDomain?.[domain] || [domain];
    mapped.forEach((key) => keys.add(key));
  });
  clearPanelCache(Array.from(keys));
}

function setFilterValue(id, value) {
  const element = document.getElementById(id);
  if (element) {
    element.value = value;
  }
}

async function copyWhatsappQr() {
  const qrElement = document.getElementById("whatsappQrValue");
  const qrValue = qrElement ? (qrElement.textContent || "").trim() : "";
  if (!qrValue) {
    showToast("Nenhum QR disponivel para copiar.", "error");
    return;
  }
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(qrValue);
      showToast("QR copiado.");
      return;
    }
  } catch (error) {}
  output.textContent = qrValue;
  showToast("QR exibido no output para copia manual.");
}

async function quickFilterPendingOrders() {
  setFilterValue("orderStatusFilter", "pending");
  setFilterValue("summaryPage", "1");
  await loadOrdersSummary();
}

async function quickFilterSignedContracts() {
  setFilterValue("contractStatusFilter", "signed");
  setFilterValue("contractsPage", "1");
  await loadContractsOnly();
}

async function quickFilterCancelledContracts() {
  setFilterValue("contractStatusFilter", "cancelled");
  setFilterValue("contractsPage", "1");
  await loadContractsOnly();
}

async function quickFilterOutboundMessages() {
  setFilterValue("messageDirectionFilter", "outbound");
  setFilterValue("messagesPage", "1");
  await loadMessagesSummary();
}

async function quickFilterInboundMessages() {
  setFilterValue("messageDirectionFilter", "inbound");
  setFilterValue("messagesPage", "1");
  await loadMessagesSummary();
}

async function quickFilterFailedMessages() {
  setFilterValue("messageStatusFilter", "failed");
  setFilterValue("messagesPage", "1");
  await loadMessagesSummary();
}

async function quickFilterPendingFinance() {
  setFilterValue("financeFilterStatus", "pending");
  setFilterValue("financePage", "1");
  setFilterValue("payablesPage", "1");
  await Promise.all([loadReceivables(), loadPayables()]);
}

async function quickFilterPaidFinance() {
  setFilterValue("financeFilterStatus", "paid");
  setFilterValue("financePage", "1");
  setFilterValue("payablesPage", "1");
  await Promise.all([loadReceivables(), loadPayables()]);
}

async function clearQuickFilters() {
  setFilterValue("orderStatusFilter", "");
  setFilterValue("contractStatusFilter", "");
  setFilterValue("messageStatusFilter", "");
  setFilterValue("messageDirectionFilter", "");
  setFilterValue("financeFilterStatus", "");
  setFilterValue("summaryPage", "1");
  setFilterValue("documentsPage", "1");
  setFilterValue("messagesPage", "1");
  setFilterValue("financePage", "1");
  setFilterValue("payablesPage", "1");
  await loadWorkspaceSummary();
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
  invalidatePanelDomains("finance");
  await loadReceivables();
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
  const financeMeta = document.getElementById("financeMeta");
  if (financeMeta && payload) {
    financeMeta.textContent = `Financeiro: pagina ${payload.page}/${Math.max(1, Math.ceil((payload.total || 0) / Math.max(payload.page_size || 1, 1)))}, total ${payload.total || 0}`;
  }
  const receivablesMeta = document.getElementById("receivablesMeta");
  if (receivablesMeta && payload) {
    receivablesMeta.textContent = `AR pagina ${payload.page} | itens ${payload.items?.length || 0} | total ${payload.total || 0}`;
  }
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
  invalidatePanelDomains("finance");
  await loadPayables();
}

async function loadPayables() {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/finance/payables?${buildScopedFinanceQuery("payablesPage", "payablesPageSize").toString()}`, {
    credentials: "same-origin"
  });
  const payload = await showResult(response);
  renderList("payablesList", (payload && payload.items) || [], (item) =>
    `#${item.id} | ${item.status} | R$ ${Number(item.amount).toFixed(2)}<br>
    ${item.category || "-"} | ${item.due_date}<br>
    <button onclick="updatePayableStatus(${item.id})">Atualizar status</button>
    <button onclick="deletePayable(${item.id})">Excluir</button>`
  );
  const financeMeta = document.getElementById("financeMeta");
  if (financeMeta && payload) {
    financeMeta.textContent = `Financeiro: pagina ${payload.page}/${Math.max(1, Math.ceil((payload.total || 0) / Math.max(payload.page_size || 1, 1)))}, total ${payload.total || 0}`;
  }
  const payablesMeta = document.getElementById("payablesMeta");
  if (payablesMeta && payload) {
    payablesMeta.textContent = `AP pagina ${payload.page} | itens ${payload.items?.length || 0} | total ${payload.total || 0}`;
  }
}

async function loadReceivablesOnly() {
  const query = new URLSearchParams({
    page: document.getElementById("financePage").value || "1",
    page_size: document.getElementById("financePageSize").value || "5"
  });
  const response = await fetch(`/admin/panel/${getTenantSlug()}/summary/receivables?${query.toString()}`, {
    credentials: "same-origin"
  });
  const payload = await showResult(response);
  if (payload) {
    setPanelCache("finance", payload);
    renderList("receivablesList", payload.receivables || [], (item) =>
      `#${item.id} | ${item.status} | R$ ${Number(item.amount).toFixed(2)}<br>
      ${item.category || "-"} | ${item.due_date || "-"}<br>
      <button onclick="updateReceivableStatus(${item.id})">Atualizar status</button>
      <button onclick="deleteReceivable(${item.id})">Excluir</button>`
    );
    const receivablesMeta = document.getElementById("receivablesMeta");
    if (receivablesMeta) {
      receivablesMeta.textContent = `AR pagina ${payload.page}/${Math.max(1, Math.ceil((payload.total || 0) / Math.max(payload.page_size || 1, 1)))}, total ${payload.total || 0}`;
    }
  }
}

async function loadPayablesOnly() {
  const query = new URLSearchParams({
    page: document.getElementById("payablesPage").value || "1",
    page_size: document.getElementById("payablesPageSize").value || "5"
  });
  const response = await fetch(`/admin/panel/${getTenantSlug()}/summary/payables?${query.toString()}`, {
    credentials: "same-origin"
  });
  const payload = await showResult(response);
  if (payload) {
    setPanelCache("finance", payload);
    renderList("payablesList", payload.payables || [], (item) =>
      `#${item.id} | ${item.status} | R$ ${Number(item.amount).toFixed(2)}<br>
      ${item.category || "-"} | ${item.due_date || "-"}<br>
      <button onclick="updatePayableStatus(${item.id})">Atualizar status</button>
      <button onclick="deletePayable(${item.id})">Excluir</button>`
    );
    const payablesMeta = document.getElementById("payablesMeta");
    if (payablesMeta) {
      payablesMeta.textContent = `AP pagina ${payload.page}/${Math.max(1, Math.ceil((payload.total || 0) / Math.max(payload.page_size || 1, 1)))}, total ${payload.total || 0}`;
    }
  }
}

async function loadOutboundMessagesOnly() {
  const query = new URLSearchParams({
    messages_page: document.getElementById("messagesPage").value || "1",
    messages_page_size: document.getElementById("messagesPageSize").value || "5",
    sort_by: selectedValue("messageSortBy", "id"),
    sort_dir: selectedValue("messageSortDir", "desc")
  });
  const messageStatus = selectedValue("messageStatusFilter");
  if (messageStatus) {
    query.set("message_status", messageStatus);
  }
  const response = await fetch(`/admin/panel/${getTenantSlug()}/summary/messages/outbound?${query.toString()}`, { credentials: "same-origin" });
  const payload = await showResult(response);
  if (payload) {
    setPanelCache("messages", payload);
    renderList("messagesList", payload.messages || [], (item) =>
      `#${item.id} | ${item.direction} | ${item.status}<br>${item.body}<br>
      <button onclick="updateMessageStatus(${item.id})">Atualizar status</button>`
    );
    const messagesMeta = document.getElementById("messagesMeta");
    if (messagesMeta) {
      messagesMeta.textContent = `Msgs OUT: pagina ${payload.messages_page}/${Math.max(1, Math.ceil((payload.messages_total || 0) / Math.max(payload.messages_page_size || 1, 1)))}, total ${payload.messages_total || 0}`;
    }
  }
}

async function loadInboundMessagesOnly() {
  const query = new URLSearchParams({
    messages_page: document.getElementById("messagesPage").value || "1",
    messages_page_size: document.getElementById("messagesPageSize").value || "5",
    sort_by: selectedValue("messageSortBy", "id"),
    sort_dir: selectedValue("messageSortDir", "desc")
  });
  const messageStatus = selectedValue("messageStatusFilter");
  if (messageStatus) {
    query.set("message_status", messageStatus);
  }
  const response = await fetch(`/admin/panel/${getTenantSlug()}/summary/messages/inbound?${query.toString()}`, { credentials: "same-origin" });
  const payload = await showResult(response);
  if (payload) {
    setPanelCache("messages", payload);
    renderList("messagesList", payload.messages || [], (item) =>
      `#${item.id} | ${item.direction} | ${item.status}<br>${item.body}<br>
      <button onclick="updateMessageStatus(${item.id})">Atualizar status</button>`
    );
    const messagesMeta = document.getElementById("messagesMeta");
    if (messagesMeta) {
      messagesMeta.textContent = `Msgs IN: pagina ${payload.messages_page}/${Math.max(1, Math.ceil((payload.messages_total || 0) / Math.max(payload.messages_page_size || 1, 1)))}, total ${payload.messages_total || 0}`;
    }
  }
}

async function connectWhatsapp() {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/whatsapp-session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ provider_session_id: document.getElementById("whatsappSessionId").value })
  });
  await showResult(response);
  invalidatePanelDomains("whatsapp");
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
  invalidatePanelDomains("messages", "whatsapp");
  await loadMessagesSummary();
}

async function updateWhatsappSessionStatus() {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/whatsapp-session/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ status: selectedValue("whatsappSessionStatus", "connected") })
  });
  await showResult(response);
  invalidatePanelDomains("whatsapp");
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
  invalidatePanelDomains("finance");
  await loadReceivables();
}

async function deleteReceivable(id) {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/finance/receivable/${id}`, {
    method: "DELETE",
    credentials: "same-origin"
  });
  await showResult(response);
  invalidatePanelDomains("finance");
  await loadReceivables();
}

async function updatePayableStatus(id) {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/finance/payable/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ status: selectedValue("payableStatusUpdate", "paid") })
  });
  await showResult(response);
  invalidatePanelDomains("finance");
  await loadPayables();
}

async function deletePayable(id) {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/finance/payable/${id}`, {
    method: "DELETE",
    credentials: "same-origin"
  });
  await showResult(response);
  invalidatePanelDomains("finance");
  await loadPayables();
}

async function updateMessageStatus(id) {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/message/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ status: selectedValue("messageStatusUpdate", "read") })
  });
  await showResult(response);
  invalidatePanelDomains("messages");
  await loadMessagesSummary();
}

async function renameLead(id) {
  const name = document.getElementById(`leadNameEdit-${id}`)?.value.trim() || "";
  if (!name) {
    showToast("Informe o novo nome do lead.", "error");
    return;
  }
  const response = await fetch(`/admin/panel/${getTenantSlug()}/lead/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ name, email: null, phone: null })
  });
  await showResult(response);
  invalidatePanelDomains("people");
  await loadLeadsOnly();
}

async function deleteLead(id) {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/lead/${id}`, { method: "DELETE", credentials: "same-origin" });
  await showResult(response);
  invalidatePanelDomains("people");
  await loadLeadsOnly();
}

async function renameClient(id) {
  const name = document.getElementById(`clientNameEdit-${id}`)?.value.trim() || "";
  if (!name) {
    showToast("Informe o novo nome do client.", "error");
    return;
  }
  const response = await fetch(`/admin/panel/${getTenantSlug()}/client/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ name, email: null, phone: null })
  });
  await showResult(response);
  invalidatePanelDomains("people");
  await loadClientsOnly();
}

async function deleteClient(id) {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/client/${id}`, { method: "DELETE", credentials: "same-origin" });
  await showResult(response);
  invalidatePanelDomains("people");
  await loadClientsOnly();
}

async function updateSalesOrderStatus(id) {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/sales-order/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ status: selectedValue("salesOrderStatusUpdate", "confirmed") })
  });
  await showResult(response);
  invalidatePanelDomains("orders");
  await loadOrdersSummary();
}

async function deleteSalesOrder(id) {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/sales-order/${id}`, { method: "DELETE", credentials: "same-origin" });
  await showResult(response);
  invalidatePanelDomains("orders");
  await loadOrdersSummary();
}

async function renameProposal(id) {
  const title = document.getElementById(`proposalTitleEdit-${id}`)?.value.trim() || "";
  if (!title) {
    showToast("Informe o novo titulo da proposta.", "error");
    return;
  }
  const cachedSummary = getPanelCache("summary");
  const cachedDocuments = getPanelCache("documents");
  const currentProposal = (cachedDocuments?.proposals || cachedSummary?.proposals || []).find((item) => item.id === id);
  const response = await fetch(`/admin/panel/${getTenantSlug()}/proposal/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({
      title,
      sales_order_id: currentProposal?.sales_order_id ?? toOptionalInt(document.getElementById("proposalOrderId").value)
    })
  });
  await showResult(response);
  invalidatePanelDomains("documents");
  await loadProposalsOnly();
}

async function deleteProposal(id) {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/proposal/${id}`, { method: "DELETE", credentials: "same-origin" });
  await showResult(response);
  invalidatePanelDomains("documents");
  await loadProposalsOnly();
}

async function renameContract(id) {
  const title = document.getElementById(`contractTitleEdit-${id}`)?.value.trim() || "";
  if (!title) {
    showToast("Informe o novo titulo do contrato.", "error");
    return;
  }
  const cachedSummary = getPanelCache("summary");
  const cachedDocuments = getPanelCache("documents");
  const currentContract = (cachedDocuments?.contracts || cachedSummary?.contracts || []).find((item) => item.id === id);
  const response = await fetch(`/admin/panel/${getTenantSlug()}/contract/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({
      title,
      sales_order_id: currentContract?.sales_order_id ?? toOptionalInt(document.getElementById("contractOrderId").value)
    })
  });
  await showResult(response);
  invalidatePanelDomains("documents");
  await loadContractsOnly();
}

async function deleteContract(id) {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/contract/${id}`, { method: "DELETE", credentials: "same-origin" });
  await showResult(response);
  invalidatePanelDomains("documents");
  await loadContractsOnly();
}

async function updateContractStatus(id) {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/contract/${id}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ status: selectedValue("contractStatusUpdate", "sent") })
  });
  await showResult(response);
  invalidatePanelDomains("documents");
  await loadContractsOnly();
}

async function loadDocumentsSummary() {
  const query = new URLSearchParams({
    documents_page: document.getElementById("documentsPage").value || "1",
    documents_page_size: document.getElementById("documentsPageSize").value || "5"
  });
  const documentFilter = document.getElementById("documentQuery").value.trim();
  const contractStatus = selectedValue("contractStatusFilter");
  query.set("sort_by", selectedValue("documentSortBy", "id"));
  query.set("sort_dir", selectedValue("documentSortDir", "desc"));
  if (documentFilter) {
    query.set("document_q", documentFilter);
  }
  if (contractStatus) {
    query.set("contract_status", contractStatus);
  }
  const response = await fetch(`/admin/panel/${getTenantSlug()}/summary/documents?${query.toString()}`, { credentials: "same-origin" });
  const payload = await showResult(response);
  if (payload) {
    setPanelCache("documents", payload);
    renderList("proposalsList", payload.proposals || [], (item) =>
      `#${item.id} | ${item.title}<br>${item.pdf_path || "sem pdf"}<br>
      <input id="proposalTitleEdit-${item.id}" placeholder="Novo titulo">
      <button onclick="renameProposal(${item.id})">Renomear</button>
      <button onclick="deleteProposal(${item.id})">Excluir</button>`
    );
    renderList("contractsList", payload.contracts || [], (item) =>
      `#${item.id} | ${item.title} | ${item.status}<br>
      <input id="contractTitleEdit-${item.id}" placeholder="Novo titulo">
      <button onclick="renameContract(${item.id})">Renomear</button>
      <button onclick="updateContractStatus(${item.id})">Atualizar status</button>
      <button onclick="deleteContract(${item.id})">Excluir</button>`
    );
    const docsMeta = document.getElementById("documentsMeta");
    if (docsMeta) {
      docsMeta.textContent = `Docs: pagina ${payload.documents_page}/${Math.max(1, Math.ceil((payload.documents_total || 0) / Math.max(payload.documents_page_size || 1, 1)))}, total ${payload.documents_total || 0}`;
    }
  }
}

async function loadMessagesSummary() {
  const query = new URLSearchParams({
    messages_page: document.getElementById("messagesPage").value || "1",
    messages_page_size: document.getElementById("messagesPageSize").value || "5"
  });
  const messageStatus = selectedValue("messageStatusFilter");
  const messageDirection = selectedValue("messageDirectionFilter");
  query.set("sort_by", selectedValue("messageSortBy", "id"));
  query.set("sort_dir", selectedValue("messageSortDir", "desc"));
  if (messageStatus) {
    query.set("message_status", messageStatus);
  }
  if (messageDirection) {
    query.set("message_direction", messageDirection);
  }
  const response = await fetch(`/admin/panel/${getTenantSlug()}/summary/messages?${query.toString()}`, { credentials: "same-origin" });
  const payload = await showResult(response);
  if (payload) {
    setPanelCache("messages", payload);
    renderList("messagesList", payload.messages || [], (item) =>
      `#${item.id} | ${item.direction} | ${item.status}<br>${item.body}<br>
      <button onclick="updateMessageStatus(${item.id})">Atualizar status</button>`
    );
    const messagesMeta = document.getElementById("messagesMeta");
    if (messagesMeta) {
      const outbound = (payload.messages || []).filter((item) => item.direction === "outbound").length;
      const inbound = (payload.messages || []).filter((item) => item.direction === "inbound").length;
      messagesMeta.textContent = `Msgs: pagina ${payload.messages_page}/${Math.max(1, Math.ceil((payload.messages_total || 0) / Math.max(payload.messages_page_size || 1, 1)))}, total ${payload.messages_total || 0}, out ${outbound}, in ${inbound}`;
    }
  }
}

async function loadFinanceSummary() {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/summary/finance`, { credentials: "same-origin" });
  const payload = await showResult(response);
  if (payload) {
    setPanelCache("finance", payload);
    renderList("receivablesList", payload.receivables || [], (item) =>
      `#${item.id} | ${item.status} | R$ ${Number(item.amount).toFixed(2)}<br>
      ${item.category || "-"} | ${item.due_date || "-"}<br>
      <button onclick="updateReceivableStatus(${item.id})">Atualizar status</button>
      <button onclick="deleteReceivable(${item.id})">Excluir</button>`
    );
    renderList("payablesList", payload.payables || [], (item) =>
      `#${item.id} | ${item.status} | R$ ${Number(item.amount).toFixed(2)}<br>
      ${item.category || "-"} | ${item.due_date || "-"}<br>
      <button onclick="updatePayableStatus(${item.id})">Atualizar status</button>
      <button onclick="deletePayable(${item.id})">Excluir</button>`
    );
  }
}

async function loadLeadsOnly() {
  const query = new URLSearchParams({
    page: document.getElementById("leadsPage").value || "1",
    page_size: document.getElementById("leadsPageSize").value || "5",
    sort_by: selectedValue("peopleSortBy", "id"),
    sort_dir: selectedValue("peopleSortDir", "desc")
  });
  const filterValue = document.getElementById("summaryQuery").value.trim();
  const email = document.getElementById("peopleEmailFilter").value.trim();
  const phone = document.getElementById("peoplePhoneFilter").value.trim();
  if (filterValue) query.set("q", filterValue);
  if (email) query.set("email", email);
  if (phone) query.set("phone", phone);
  const response = await fetch(`/admin/panel/${getTenantSlug()}/summary/leads?${query.toString()}`, { credentials: "same-origin" });
  const payload = await showResult(response);
  if (payload) {
    setPanelCache("leads", payload);
    renderList("leadsList", payload.items || [], (item) =>
      `#${item.id} | ${item.name}<br>${item.email || "-"}<br>
      <input id="leadNameEdit-${item.id}" placeholder="Novo nome">
      <button onclick="renameLead(${item.id})">Editar</button>
      <button onclick="deleteLead(${item.id})">Excluir</button>`
    );
    const leadsMeta = document.getElementById("leadsMeta");
    if (leadsMeta) {
      leadsMeta.textContent = `Leads: pagina ${payload.page}/${Math.max(1, Math.ceil((payload.total || 0) / Math.max(payload.page_size || 1, 1)))}, total ${payload.total || 0}`;
    }
  }
}

async function loadClientsOnly() {
  const query = new URLSearchParams({
    page: document.getElementById("clientsPage").value || "1",
    page_size: document.getElementById("clientsPageSize").value || "5",
    sort_by: selectedValue("peopleSortBy", "id"),
    sort_dir: selectedValue("peopleSortDir", "desc")
  });
  const filterValue = document.getElementById("summaryQuery").value.trim();
  const email = document.getElementById("peopleEmailFilter").value.trim();
  const phone = document.getElementById("peoplePhoneFilter").value.trim();
  if (filterValue) query.set("q", filterValue);
  if (email) query.set("email", email);
  if (phone) query.set("phone", phone);
  const response = await fetch(`/admin/panel/${getTenantSlug()}/summary/clients?${query.toString()}`, { credentials: "same-origin" });
  const payload = await showResult(response);
  if (payload) {
    setPanelCache("clients", payload);
    renderList("clientsList", payload.items || [], (item) =>
      `#${item.id} | ${item.name}<br>${item.email || "-"}<br>
      <input id="clientNameEdit-${item.id}" placeholder="Novo nome">
      <button onclick="renameClient(${item.id})">Editar</button>
      <button onclick="deleteClient(${item.id})">Excluir</button>`
    );
    const clientsMeta = document.getElementById("clientsMeta");
    if (clientsMeta) {
      clientsMeta.textContent = `Clients: pagina ${payload.page}/${Math.max(1, Math.ceil((payload.total || 0) / Math.max(payload.page_size || 1, 1)))}, total ${payload.total || 0}`;
    }
  }
}

async function loadProposalsOnly() {
  const query = new URLSearchParams({
    page: document.getElementById("proposalsPage").value || "1",
    page_size: document.getElementById("proposalsPageSize").value || "5",
    sort_by: selectedValue("documentSortBy", "id"),
    sort_dir: selectedValue("documentSortDir", "desc")
  });
  const documentFilter = document.getElementById("documentQuery").value.trim();
  if (documentFilter) query.set("document_q", documentFilter);
  const response = await fetch(`/admin/panel/${getTenantSlug()}/summary/proposals?${query.toString()}`, { credentials: "same-origin" });
  const payload = await showResult(response);
  if (payload) {
    setPanelCache("proposals", payload);
    renderList("proposalsList", payload.items || [], (item) =>
      `#${item.id} | ${item.title}<br>${item.pdf_path || "sem pdf"}<br>
      <input id="proposalTitleEdit-${item.id}" placeholder="Novo titulo">
      <button onclick="renameProposal(${item.id})">Renomear</button>
      <button onclick="deleteProposal(${item.id})">Excluir</button>`
    );
    const docsMeta = document.getElementById("documentsMeta");
    if (docsMeta) {
      docsMeta.textContent = `Propostas: pagina ${payload.page}/${Math.max(1, Math.ceil((payload.total || 0) / Math.max(payload.page_size || 1, 1)))}, total ${payload.total || 0}`;
    }
    const proposalsMeta = document.getElementById("proposalsMeta");
    if (proposalsMeta) {
      proposalsMeta.textContent = `Pagina ${payload.page} | total ${payload.total || 0}`;
    }
  }
}

async function loadContractsOnly() {
  const query = new URLSearchParams({
    page: document.getElementById("contractsPage").value || "1",
    page_size: document.getElementById("contractsPageSize").value || "5",
    sort_by: selectedValue("documentSortBy", "id"),
    sort_dir: selectedValue("documentSortDir", "desc")
  });
  const documentFilter = document.getElementById("documentQuery").value.trim();
  const contractStatus = selectedValue("contractStatusFilter");
  if (documentFilter) query.set("document_q", documentFilter);
  if (contractStatus) query.set("contract_status", contractStatus);
  const response = await fetch(`/admin/panel/${getTenantSlug()}/summary/contracts?${query.toString()}`, { credentials: "same-origin" });
  const payload = await showResult(response);
  if (payload) {
    setPanelCache("contracts", payload);
    renderList("contractsList", payload.items || [], (item) =>
      `#${item.id} | ${item.title} | ${item.status}<br>
      <input id="contractTitleEdit-${item.id}" placeholder="Novo titulo">
      <button onclick="renameContract(${item.id})">Renomear</button>
      <button onclick="updateContractStatus(${item.id})">Atualizar status</button>
      <button onclick="deleteContract(${item.id})">Excluir</button>`
    );
    const docsMeta = document.getElementById("documentsMeta");
    if (docsMeta) {
      docsMeta.textContent = `Contratos: pagina ${payload.page}/${Math.max(1, Math.ceil((payload.total || 0) / Math.max(payload.page_size || 1, 1)))}, total ${payload.total || 0}`;
    }
    const contractsMeta = document.getElementById("contractsMeta");
    if (contractsMeta) {
      contractsMeta.textContent = `Pagina ${payload.page} | total ${payload.total || 0}`;
    }
  }
}

async function loadOrdersSummary() {
  const query = new URLSearchParams({
    page: document.getElementById("summaryPage").value || "1",
    page_size: document.getElementById("summaryPageSize").value || "5"
  });
  const orderStatus = selectedValue("orderStatusFilter");
  query.set("sort_by", selectedValue("orderSortBy", "id"));
  query.set("sort_dir", selectedValue("orderSortDir", "desc"));
  if (orderStatus) {
    query.set("order_status", orderStatus);
  }
  const response = await fetch(`/admin/panel/${getTenantSlug()}/summary/orders?${query.toString()}`, { credentials: "same-origin" });
  const payload = await showResult(response);
  if (payload) {
    setPanelCache("orders", payload);
    renderList("salesOrdersList", payload.sales_orders || [], (item) =>
      `#${item.id} | ${item.status} | R$ ${Number(item.total_amount).toFixed(2)}<br>
      <button onclick="updateSalesOrderStatus(${item.id})">Atualizar status</button>
      <button onclick="deleteSalesOrder(${item.id})">Excluir</button>`
    );
    const ordersMeta = document.getElementById("ordersMeta");
    if (ordersMeta) {
      ordersMeta.textContent = `Pedidos: pagina ${payload.page}/${Math.max(1, Math.ceil((payload.sales_orders_total || 0) / Math.max(payload.page_size || 1, 1)))}, total ${payload.sales_orders_total || 0}`;
    }
  }
}

async function loadPeopleSummary() {
  const query = new URLSearchParams({
    leads_page: document.getElementById("leadsPage").value || "1",
    leads_page_size: document.getElementById("leadsPageSize").value || "5",
    clients_page: document.getElementById("clientsPage").value || "1",
    clients_page_size: document.getElementById("clientsPageSize").value || "5"
  });
  const filterValue = document.getElementById("summaryQuery").value.trim();
  const email = document.getElementById("peopleEmailFilter").value.trim();
  const phone = document.getElementById("peoplePhoneFilter").value.trim();
  query.set("sort_by", selectedValue("peopleSortBy", "id"));
  query.set("sort_dir", selectedValue("peopleSortDir", "desc"));
  if (filterValue) {
    query.set("q", filterValue);
  }
  if (email) {
    query.set("email", email);
  }
  if (phone) {
    query.set("phone", phone);
  }
  const response = await fetch(`/admin/panel/${getTenantSlug()}/summary/people?${query.toString()}`, { credentials: "same-origin" });
  const payload = await showResult(response);
  if (payload) {
    setPanelCache("people", payload);
    const leadsBlock = payload.leads || {};
    const clientsBlock = payload.clients || {};
    renderList("leadsList", leadsBlock.items || [], (item) =>
      `#${item.id} | ${item.name}<br>${item.email || "-"}<br>
      <input id="leadNameEdit-${item.id}" placeholder="Novo nome">
      <button onclick="renameLead(${item.id})">Editar</button>
      <button onclick="deleteLead(${item.id})">Excluir</button>`
    );
    renderList("clientsList", clientsBlock.items || [], (item) =>
      `#${item.id} | ${item.name}<br>${item.email || "-"}<br>
      <input id="clientNameEdit-${item.id}" placeholder="Novo nome">
      <button onclick="renameClient(${item.id})">Editar</button>
      <button onclick="deleteClient(${item.id})">Excluir</button>`
    );
    const leadsMeta = document.getElementById("leadsMeta");
    if (leadsMeta) {
      leadsMeta.textContent = `Leads: pagina ${leadsBlock.page || 1}/${Math.max(1, Math.ceil((leadsBlock.total || 0) / Math.max(leadsBlock.page_size || 1, 1)))}, total ${leadsBlock.total || 0}`;
    }
    const clientsMeta = document.getElementById("clientsMeta");
    if (clientsMeta) {
      clientsMeta.textContent = `Clients: pagina ${clientsBlock.page || 1}/${Math.max(1, Math.ceil((clientsBlock.total || 0) / Math.max(clientsBlock.page_size || 1, 1)))}, total ${clientsBlock.total || 0}`;
    }
  }
}

function openPanelDownload(path, query) {
  const url = `/admin/panel/${getTenantSlug()}${path}?${query.toString()}`;
  window.open(url, "_blank", "noopener");
}

async function exportOrdersCsv() {
  const query = new URLSearchParams();
  const orderStatus = selectedValue("orderStatusFilter");
  if (orderStatus) {
    query.set("order_status", orderStatus);
  }
  query.set("sort_by", selectedValue("orderSortBy", "id"));
  query.set("sort_dir", selectedValue("orderSortDir", "desc"));
  openPanelDownload("/summary/orders/export", query);
}

async function exportPeopleCsv() {
  const query = new URLSearchParams();
  const filterValue = document.getElementById("summaryQuery").value.trim();
  const email = document.getElementById("peopleEmailFilter").value.trim();
  const phone = document.getElementById("peoplePhoneFilter").value.trim();
  if (filterValue) {
    query.set("q", filterValue);
  }
  if (email) {
    query.set("email", email);
  }
  if (phone) {
    query.set("phone", phone);
  }
  query.set("sort_by", selectedValue("peopleSortBy", "id"));
  query.set("sort_dir", selectedValue("peopleSortDir", "desc"));
  openPanelDownload("/summary/people/export", query);
}

async function exportLeadsCsv() {
  const query = new URLSearchParams();
  const filterValue = document.getElementById("summaryQuery").value.trim();
  const email = document.getElementById("peopleEmailFilter").value.trim();
  const phone = document.getElementById("peoplePhoneFilter").value.trim();
  if (filterValue) query.set("q", filterValue);
  if (email) query.set("email", email);
  if (phone) query.set("phone", phone);
  query.set("sort_by", selectedValue("peopleSortBy", "id"));
  query.set("sort_dir", selectedValue("peopleSortDir", "desc"));
  openPanelDownload("/summary/leads/export", query);
}

async function exportClientsCsv() {
  const query = new URLSearchParams();
  const filterValue = document.getElementById("summaryQuery").value.trim();
  const email = document.getElementById("peopleEmailFilter").value.trim();
  const phone = document.getElementById("peoplePhoneFilter").value.trim();
  if (filterValue) query.set("q", filterValue);
  if (email) query.set("email", email);
  if (phone) query.set("phone", phone);
  query.set("sort_by", selectedValue("peopleSortBy", "id"));
  query.set("sort_dir", selectedValue("peopleSortDir", "desc"));
  openPanelDownload("/summary/clients/export", query);
}

async function exportDocumentsCsv() {
  const common = new URLSearchParams();
  const documentFilter = document.getElementById("documentQuery").value.trim();
  const contractStatus = selectedValue("contractStatusFilter");
  if (documentFilter) common.set("document_q", documentFilter);
  if (contractStatus) common.set("contract_status", contractStatus);
  common.set("sort_by", selectedValue("documentSortBy", "id"));
  common.set("sort_dir", selectedValue("documentSortDir", "desc"));
  openPanelDownload("/summary/proposals/export", common);
  openPanelDownload("/summary/contracts/export", common);
}

async function exportProposalsCsv() {
  const query = new URLSearchParams();
  const documentFilter = document.getElementById("documentQuery").value.trim();
  if (documentFilter) query.set("document_q", documentFilter);
  query.set("sort_by", selectedValue("documentSortBy", "id"));
  query.set("sort_dir", selectedValue("documentSortDir", "desc"));
  openPanelDownload("/summary/proposals/export", query);
}

async function exportContractsCsv() {
  const query = new URLSearchParams();
  const documentFilter = document.getElementById("documentQuery").value.trim();
  const contractStatus = selectedValue("contractStatusFilter");
  if (documentFilter) query.set("document_q", documentFilter);
  if (contractStatus) query.set("contract_status", contractStatus);
  query.set("sort_by", selectedValue("documentSortBy", "id"));
  query.set("sort_dir", selectedValue("documentSortDir", "desc"));
  openPanelDownload("/summary/contracts/export", query);
}

async function exportMessagesCsv() {
  const query = new URLSearchParams();
  const messageStatus = selectedValue("messageStatusFilter");
  const messageDirection = selectedValue("messageDirectionFilter");
  if (messageStatus) query.set("message_status", messageStatus);
  if (messageDirection) query.set("message_direction", messageDirection);
  query.set("sort_by", selectedValue("messageSortBy", "id"));
  query.set("sort_dir", selectedValue("messageSortDir", "desc"));
  openPanelDownload("/summary/messages/export", query);
}

async function exportOutboundMessagesCsv() {
  const query = new URLSearchParams();
  query.set("message_direction", "outbound");
  query.set("sort_by", selectedValue("messageSortBy", "id"));
  query.set("sort_dir", selectedValue("messageSortDir", "desc"));
  openPanelDownload("/summary/messages/export", query);
}

async function exportInboundMessagesCsv() {
  const query = new URLSearchParams();
  query.set("message_direction", "inbound");
  query.set("sort_by", selectedValue("messageSortBy", "id"));
  query.set("sort_dir", selectedValue("messageSortDir", "desc"));
  openPanelDownload("/summary/messages/export", query);
}

async function exportFinanceCsv() {
  const receivableQuery = buildFinanceQuery();
  receivableQuery.set("entry_type", "receivable");
  openPanelDownload("/finance/export", receivableQuery);
  const payableQuery = buildScopedFinanceQuery("payablesPage", "payablesPageSize");
  payableQuery.set("entry_type", "payable");
  openPanelDownload("/finance/export", payableQuery);
}

async function exportReceivablesCsv() {
  const query = buildFinanceQuery();
  query.set("entry_type", "receivable");
  openPanelDownload("/finance/export", query);
}

async function exportPayablesCsv() {
  const query = buildScopedFinanceQuery("payablesPage", "payablesPageSize");
  query.set("entry_type", "payable");
  openPanelDownload("/finance/export", query);
}

function shiftNumericInput(id, delta, minimum = 1) {
  const element = document.getElementById(id);
  if (!element) {
    return;
  }
  const current = Number(element.value || minimum);
  element.value = String(Math.max(minimum, current + delta));
}

async function prevOrdersPage() {
  shiftNumericInput("summaryPage", -1);
  await loadOrdersSummary();
}

async function nextOrdersPage() {
  shiftNumericInput("summaryPage", 1);
  await loadOrdersSummary();
}

async function prevDocumentsPage() {
  shiftNumericInput("documentsPage", -1);
  await loadDocumentsSummary();
}

async function nextDocumentsPage() {
  shiftNumericInput("documentsPage", 1);
  await loadDocumentsSummary();
}

async function prevProposalsPage() {
  shiftNumericInput("proposalsPage", -1);
  await loadProposalsOnly();
}

async function nextProposalsPage() {
  shiftNumericInput("proposalsPage", 1);
  await loadProposalsOnly();
}

async function prevContractsPage() {
  shiftNumericInput("contractsPage", -1);
  await loadContractsOnly();
}

async function nextContractsPage() {
  shiftNumericInput("contractsPage", 1);
  await loadContractsOnly();
}

async function prevMessagesPage() {
  shiftNumericInput("messagesPage", -1);
  await loadMessagesSummary();
}

async function nextMessagesPage() {
  shiftNumericInput("messagesPage", 1);
  await loadMessagesSummary();
}

async function prevFinancePage() {
  shiftNumericInput("financePage", -1);
  await loadReceivables();
}

async function nextFinancePage() {
  shiftNumericInput("financePage", 1);
  await loadReceivables();
}

async function prevReceivablesPage() {
  shiftNumericInput("financePage", -1);
  await loadReceivablesOnly();
}

async function nextReceivablesPage() {
  shiftNumericInput("financePage", 1);
  await loadReceivablesOnly();
}

async function prevPayablesPage() {
  shiftNumericInput("payablesPage", -1);
  await loadPayablesOnly();
}

async function nextPayablesPage() {
  shiftNumericInput("payablesPage", 1);
  await loadPayablesOnly();
}

async function prevLeadsPage() {
  shiftNumericInput("leadsPage", -1);
  await loadPeopleSummary();
}

async function nextLeadsPage() {
  shiftNumericInput("leadsPage", 1);
  await loadPeopleSummary();
}

async function prevClientsPage() {
  shiftNumericInput("clientsPage", -1);
  await loadPeopleSummary();
}

async function nextClientsPage() {
  shiftNumericInput("clientsPage", 1);
  await loadPeopleSummary();
}
