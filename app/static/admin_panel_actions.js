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
  const payload = await showResult(response);
  if (payload) {
    panelAuth.centralToken = payload.token || null;
    setPanelVisibility(true);
    switchPanelSection("home");
    loadCompanyAccounts().catch(() => {});
    loadCatalogProducts().catch(() => {});
    loadCatalogPlans().catch(() => {});
    if (output) {
      output.textContent = JSON.stringify({ ok: true, message: "Sessao central iniciada." }, null, 2);
    }
    showToast("Login central realizado. Agora carregue o dashboard.", "success");
  }
}

async function logoutPanel() {
  const response = await fetch("/admin/panel/logout", buildCentralRequestOptions({ method: "POST" }));
  await showResult(response);
  panelAuth.centralToken = null;
  panelAuth.tenantToken = null;
  panelAuth.tenantSlug = null;
  setPanelVisibility(false);
}

async function centralDashboard() {
  const response = await fetch("/admin/panel/central/dashboard", buildCentralRequestOptions());
  const payload = await showResult(response);
  if (payload) {
    panelAuth.tenantToken = payload.token || null;
    panelAuth.tenantSlug = payload.workspace_slug || slug;
    setPanelVisibility(true);
    activateSectionAndScroll("home", "topMetrics");
    loadCompanyAccounts().catch(() => {});
    loadCatalogProducts().catch(() => {});
    loadCatalogPlans().catch(() => {});
    await loadWorkspaceSummary();
  }
}

async function createTenant() {
  const response = await fetch("/admin/panel/tenant", {
    ...buildCentralRequestOptions({
      method: "POST",
      headers: { "Content-Type": "application/json" }
    }),
    body: JSON.stringify({
      account_id: toOptionalInt(document.getElementById("tenantAccountId").value) || getActiveCompanyAccountId(),
      company_name: document.getElementById("tenantCompanyName").value,
      workspace_slug: document.getElementById("tenantWorkspaceSlug").value,
      account_stage: "client",
      admin_name: document.getElementById("tenantAdminCreateName").value,
      admin_email: document.getElementById("tenantAdminCreateEmail").value,
      admin_password: document.getElementById("tenantAdminCreatePassword").value
    })
  });
  const payload = await showResult(response);
  if (payload) {
    const tenantSlug = document.getElementById("tenantSlug");
    if (tenantSlug) {
      tenantSlug.value = payload.workspace_slug || document.getElementById("tenantWorkspaceSlug").value;
    }
    await loadCompanyAccounts();
  }
}

function buildCompanyAccountPayload() {
  return {
    name: document.getElementById("companyName").value,
    lifecycle_stage: selectedValue("companyStage", "lead"),
    admin_email: document.getElementById("tenantAdminEmail").value,
    phone: document.getElementById("companyPhone").value,
    company_document: document.getElementById("companyDocument").value,
    notes: document.getElementById("companyNotes").value
  };
}

function buildRelationshipLeadPayload() {
  return {
    name: document.getElementById("accountLeadName").value,
    lifecycle_stage: "lead",
    admin_email: document.getElementById("accountLeadEmail").value || null,
    phone: null,
    company_document: null,
    notes: "Lead criado na etapa comercial."
  };
}

function getActiveCompanyAccountId() {
  return toOptionalInt(document.getElementById("activeCompanyAccountId")?.value || "");
}

function getClientAccounts() {
  const cache = getPanelCache("companyAccounts");
  return (cache?.items || []).filter((item) => item.lifecycle_stage === "client");
}

function getCompanyAccountStageFilter() {
  return getPanelCache("companyAccountStageFilter") || "all";
}

function getVisibleCompanyAccounts() {
  const cache = getPanelCache("companyAccounts");
  const items = cache?.items || [];
  const stage = getCompanyAccountStageFilter();
  if (stage === "all") {
    return items;
  }
  return items.filter((item) => item.lifecycle_stage === stage);
}

function renderClientDirectory(items) {
  const target = document.getElementById("clientDirectoryList");
  const activeId = getActiveCompanyAccountId();
  if (!target) {
    return;
  }
  if (!items || items.length === 0) {
    target.innerHTML = '<div class="list-item">Nenhum cliente encontrado.</div>';
    return;
  }
  target.innerHTML = items
    .map(
      (item) => `
        <div class="list-item ${activeId === item.id ? "active-client-row" : ""}">
          <div class="client-directory-row">
            <button type="button" class="tenant-account-result client-directory-main ${activeId === item.id ? "active" : ""}" onclick="selectClientProfile(${item.id}, 'summary')">
              <strong>#${item.id}</strong> ${item.name}
              <span>${item.tenant_id ? `Tenant ${item.tenant_id}` : "Sem tenant"}</span>
            </button>
            <div class="client-directory-tabs">
              <button type="button" class="table-action ${activeId === item.id ? "active" : ""}" onclick="selectClientProfile(${item.id}, 'summary')">Resumo</button>
              <button type="button" class="table-action ${activeId === item.id ? "active" : ""}" onclick="selectClientProfile(${item.id}, 'tenant')">Tenant</button>
              <button type="button" class="table-action ${activeId === item.id ? "active" : ""}" onclick="selectClientProfile(${item.id}, 'sales')">Vendas</button>
              <button type="button" class="table-action ${activeId === item.id ? "active" : ""}" onclick="selectClientProfile(${item.id}, 'plans')">Planos</button>
            </div>
          </div>
        </div>
      `
    )
    .join("");
}

function applyTenantAccountSelection(selected) {
  const hidden = document.getElementById("tenantAccountId");
  const status = document.getElementById("tenantAccountTenantStatus");
  if (!hidden) {
    return;
  }
  hidden.value = selected ? String(selected.id) : "";
  if (!selected) {
    if (status) {
      status.textContent = "Selecione uma conta para ver o tenant vinculado.";
    }
    return;
  }
  if (status) {
    status.textContent = selected.tenant_id
      ? `Tenant atual: ID ${selected.tenant_id} ja vinculado a este cliente.`
      : "Este cliente ainda nao possui tenant vinculado.";
  }
  const companyName = document.getElementById("tenantCompanyName");
  const adminEmail = document.getElementById("tenantAdminCreateEmail");
  if (companyName) {
    companyName.value = selected.name || "";
  }
  if (adminEmail) {
    adminEmail.value = selected.admin_email || "";
  }
  const tenantEmail = document.getElementById("tenantEmail");
  if (tenantEmail) {
    tenantEmail.value = selected.admin_email || "";
  }
}

function applyClientHeaderActions(selected) {
  const primary = document.getElementById("clientPrimaryAction");
  const secondary = document.getElementById("clientSecondaryAction");
  if (!primary || !secondary) {
    return;
  }
  if (!selected) {
    primary.textContent = "Abrir";
    secondary.textContent = "Detalhes";
    return;
  }
  if (selected.lifecycle_stage === "lead") {
    primary.textContent = "Converter";
    secondary.textContent = "Editar lead";
    return;
  }
  primary.textContent = selected.tenant_id ? "Abrir tenant" : "Criar tenant";
  secondary.textContent = "Nova venda";
}

function runClientPrimaryAction() {
  const activeId = getActiveCompanyAccountId();
  if (!activeId) {
    showToast("Selecione uma conta antes de executar a acao.", "error");
    return;
  }
  const selected = (getPanelCache("companyAccounts")?.items || []).find((item) => item.id === activeId) || null;
  if (!selected) {
    showToast("Conta ativa nao encontrada.", "error");
    return;
  }
  if (selected.lifecycle_stage === "lead") {
    promoteCompanyAccount(activeId).catch(() => {});
    return;
  }
  openClientProfileTab("tenant");
}

function runClientSecondaryAction() {
  const activeId = getActiveCompanyAccountId();
  if (!activeId) {
    showToast("Selecione uma conta antes de executar a acao.", "error");
    return;
  }
  const selected = (getPanelCache("companyAccounts")?.items || []).find((item) => item.id === activeId) || null;
  if (!selected) {
    showToast("Conta ativa nao encontrada.", "error");
    return;
  }
  if (selected.lifecycle_stage === "lead") {
    openClientProfileTab("summary");
    return;
  }
  prepareClientSale();
}

function renderClientProfile(selected) {
  const empty = document.getElementById("clientProfileEmpty");
  const panel = document.getElementById("clientProfilePanel");
  if (!empty || !panel) {
    return;
  }
  if (!selected) {
    empty.classList.remove("hidden");
    panel.classList.add("hidden");
    return;
  }
  empty.classList.add("hidden");
  panel.classList.remove("hidden");
  document.getElementById("clientProfileStage").textContent = selected.lifecycle_stage || "client";
  document.getElementById("clientProfileTenantBadge").textContent = selected.tenant_id
    ? `Tenant ${selected.tenant_id}`
    : "Sem tenant";
  document.getElementById("clientProfileName").textContent = selected.name || "-";
  document.getElementById("clientProfileMeta").textContent = `${selected.admin_email || "-"} | Conta #${selected.id}`;
  document.getElementById("clientSummaryStage").textContent = `Estagio: ${selected.lifecycle_stage}`;
  document.getElementById("clientSummaryEmail").textContent = `Email: ${selected.admin_email || "-"}`;
  document.getElementById("clientSummaryTenant").textContent = selected.tenant_id
    ? `Tenant vinculado: ${selected.tenant_id}`
    : "Tenant vinculado: nenhum";
  document.getElementById("clientSalesHint").textContent = `Conta ativa: ${selected.name} (#${selected.id})`;
  document.getElementById("clientSalesFilter").textContent = `Vendas e documentos serao abertos com filtro pela conta ${selected.id}.`;
  applyTenantAccountSelection(selected);
  applyClientHeaderActions(selected);
}

function selectClientProfile(accountId, tab = "summary") {
  const selected = (getPanelCache("companyAccounts")?.items || []).find((item) => item.id === accountId) || null;
  if (!selected) {
    return;
  }
  setActiveCompanyAccount(selected.id);
  renderClientProfile(selected);
  openClientProfileTab(tab);
  const profilePanel = document.getElementById("clientProfilePanel");
  if (profilePanel && typeof profilePanel.scrollIntoView === "function") {
    profilePanel.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function filterClientDirectory() {
  const input = document.getElementById("clientDirectorySearch");
  const items = getVisibleCompanyAccounts();
  if (!input) {
    return;
  }
  const term = (input.value || "").trim().toLowerCase();
  if (!term) {
    renderClientDirectory(items);
    return;
  }
  renderClientDirectory(
    items.filter((item) => `${item.id} ${item.name} ${item.admin_email || ""}`.toLowerCase().includes(term))
  );
}

function setCompanyAccountStageFilter(stage, trigger = null) {
  setPanelCache("companyAccountStageFilter", stage);
  document.querySelectorAll("[data-account-filter]").forEach((node) => {
    node.classList.toggle("active", node.dataset.accountFilter === stage);
  });
  if (trigger && trigger.classList) {
    trigger.classList.add("active");
  }
  filterClientDirectory();
}

function openClientProfileTab(tab, trigger = null) {
  document.querySelectorAll(".client-tab-panel").forEach((node) => {
    node.classList.toggle("active", node.dataset.clientPanel === tab);
  });
  document.querySelectorAll("[data-client-tab]").forEach((node) => {
    node.classList.toggle("active", node.dataset.clientTab === tab);
  });
  if (trigger && trigger.classList) {
    trigger.classList.add("active");
  }
}

function openCatalogTab(tab, trigger = null) {
  document.querySelectorAll(".catalog-tab-panel").forEach((node) => {
    node.classList.toggle("active", node.dataset.catalogPanel === tab);
  });
  document.querySelectorAll("[data-catalog-tab]").forEach((node) => {
    node.classList.toggle("active", node.dataset.catalogTab === tab);
  });
  if (trigger && trigger.classList) {
    trigger.classList.add("active");
  }
}

function openNewClientComposer() {
  switchPanelSection("tenant");
  const composer = document.getElementById("newClientComposer");
  if (composer) {
    composer.classList.remove("hidden");
  }
  const name = document.getElementById("companyName");
  if (name && typeof name.focus === "function") {
    name.focus();
  }
}

function closeNewClientComposer() {
  const composer = document.getElementById("newClientComposer");
  if (composer) {
    composer.classList.add("hidden");
  }
}

function buildCatalogProductPayload() {
  return {
    code: null,
    name: document.getElementById("catalogProductName").value,
    amount: Number(document.getElementById("catalogProductAmount").value || "0")
  };
}

function buildCatalogPlanPayload() {
  return {
    code: null,
    name: document.getElementById("catalogPlanName").value,
    product_id: toOptionalInt(document.getElementById("catalogPlanProductId").value),
    amount: Number(document.getElementById("catalogPlanAmount").value || "0"),
    billing_cycle: document.getElementById("catalogPlanBillingCycle").value,
    currency: document.getElementById("catalogPlanCurrency").value || "BRL",
    is_active: selectedValue("catalogPlanIsActive", "true") === "true"
  };
}

function syncCatalogProductOptions() {
  const select = document.getElementById("catalogPlanProductId");
  if (select) {
    const cache = getPanelCache("catalogProducts");
    const items = cache?.items || [];
    const currentValue = select.value;
    select.innerHTML = '<option value="">Sem produto</option>' + items
      .map((item) => `<option value="${item.id}">${item.name} (#${item.id})</option>`)
      .join("");
    if (currentValue) {
      select.value = currentValue;
    }
  }
  syncSalesCatalogOptions();
}

function syncSalesCatalogOptions() {
  const planSelect = document.getElementById("salesPlanId");
  const addonList = document.getElementById("salesAddonList");
  const plans = getPanelCache("catalogPlans")?.items || [];
  const products = getPanelCache("catalogProducts")?.items || [];
  if (planSelect) {
    const currentValue = planSelect.value;
    planSelect.innerHTML = '<option value="">Sem plano</option>' + plans
      .filter((item) => item.is_active !== false)
      .map((item) => `<option value="${item.id}">${item.name} | ${item.billing_cycle || "-"} | R$ ${Number(item.amount || 0).toFixed(2)}</option>`)
      .join("");
    if (currentValue) {
      planSelect.value = currentValue;
    }
  }
  if (addonList) {
    const currentValues = new Set(
      Array.from(addonList.querySelectorAll("input[type='checkbox']:checked")).map((node) => Number(node.value))
    );
    addonList.innerHTML = products.length
      ? products
          .map(
            (item) => `
              <label class="sales-addon-option">
                <input type="checkbox" value="${item.id}" ${currentValues.has(item.id) ? "checked" : ""} onchange="applySalesCatalogSelection()">
                <span>${item.name}</span>
                <strong>R$ ${Number(item.amount || 0).toFixed(2)}</strong>
              </label>
            `
          )
          .join("")
      : '<div class="list-item">Nenhum produto adicional cadastrado.</div>';
  }
  applySalesCatalogSelection();
}

function applySalesCatalogSelection() {
  const plans = getPanelCache("catalogPlans")?.items || [];
  const products = getPanelCache("catalogProducts")?.items || [];
  const planSelect = document.getElementById("salesPlanId");
  const description = document.getElementById("salesDescription");
  const price = document.getElementById("salesPrice");
  const quantity = document.getElementById("salesQuantity");
  if (!planSelect || !description || !price || !quantity) {
    return;
  }
  const selectedPlanId = toOptionalInt(planSelect.value || "");
  const selectedPlan = plans.find((item) => item.id === selectedPlanId) || null;
  const selectedProductIds = Array.from(document.querySelectorAll("#salesAddonList input[type='checkbox']:checked"))
    .map((input) => Number(input.value));
  const selectedProducts = products.filter((item) => selectedProductIds.includes(item.id));
  const parts = [];
  let total = 0;
  if (selectedPlan) {
    parts.push(`Plano ${selectedPlan.name}`);
    total += Number(selectedPlan.amount || 0);
  }
  if (selectedProducts.length) {
    parts.push(`Add-ons: ${selectedProducts.map((item) => item.name).join(", ")}`);
    total += selectedProducts.reduce((sum, item) => sum + Number(item.amount || 0), 0);
  }
  if (parts.length) {
    description.value = parts.join(" | ");
    price.value = total.toFixed(2);
    if (!quantity.value) {
      quantity.value = "1";
    }
  }
}

async function createCatalogProduct() {
  const response = await fetch("/admin/panel/catalog/product", {
    ...buildCentralRequestOptions({
      method: "POST",
      headers: { "Content-Type": "application/json" }
    }),
    body: JSON.stringify(buildCatalogProductPayload())
  });
  const payload = await showResult(response);
  if (payload) {
    await loadCatalogProducts();
  }
}

async function updateCatalogProduct(productId) {
  const products = getPanelCache("catalogProducts")?.items || [];
  const current = products.find((item) => item.id === productId);
  if (!current) {
    return;
  }
  const name = window.prompt("Nome do produto:", current.name);
  if (name === null) {
    return;
  }
  const amount = window.prompt("Valor base:", String(current.amount));
  if (amount === null) {
    return;
  }
  const response = await fetch(`/admin/panel/catalog/product/${productId}`, {
    ...buildCentralRequestOptions({
      method: "PATCH",
      headers: { "Content-Type": "application/json" }
    }),
    body: JSON.stringify({
      code: null,
      name: name.trim() || current.name,
      amount: Number(amount || current.amount)
    })
  });
  const payload = await showResult(response);
  if (payload) {
    await loadCatalogProducts();
  }
}

async function loadCatalogProducts() {
  const response = await fetch("/admin/panel/catalog/products", buildCentralRequestOptions());
  const payload = await showResult(response);
  if (!payload) {
    return;
  }
  setPanelCache("catalogProducts", payload);
  syncCatalogProductOptions();
  const meta = document.getElementById("catalogProductsMeta");
  if (meta) {
    meta.textContent = `Produtos ${payload.total || 0}`;
  }
  const list = document.getElementById("catalogProductsList");
  if (list) {
    list.innerHTML = (payload.items || []).length
      ? payload.items
          .map(
            (item) => `
              <div class="list-item">
                <strong>${item.name}</strong> | ${item.code} | R$ ${Number(item.amount || 0).toFixed(2)}
                <button class="table-action" type="button" onclick="updateCatalogProduct(${item.id})">Editar</button>
              </div>
            `
          )
          .join("")
      : '<div class="list-item">Nenhum produto cadastrado.</div>';
  }
}

async function createCatalogPlan() {
  const response = await fetch("/admin/panel/catalog/plan", {
    ...buildCentralRequestOptions({
      method: "POST",
      headers: { "Content-Type": "application/json" }
    }),
    body: JSON.stringify(buildCatalogPlanPayload())
  });
  const payload = await showResult(response);
  if (payload) {
    await loadCatalogPlans();
  }
}

async function updateCatalogPlan(planId) {
  const plans = getPanelCache("catalogPlans")?.items || [];
  const current = plans.find((item) => item.id === planId);
  if (!current) {
    return;
  }
  const name = window.prompt("Nome do plano:", current.name);
  if (name === null) {
    return;
  }
  const amount = window.prompt("Valor do plano:", String(current.amount));
  if (amount === null) {
    return;
  }
  const billingCycle = window.prompt("Duracao do plano:", current.billing_cycle || "monthly");
  if (billingCycle === null) {
    return;
  }
  const response = await fetch(`/admin/panel/catalog/plan/${planId}`, {
    ...buildCentralRequestOptions({
      method: "PATCH",
      headers: { "Content-Type": "application/json" }
    }),
    body: JSON.stringify({
      code: null,
      name: name.trim() || current.name,
      product_id: current.product_id || null,
      amount: Number(amount || current.amount),
      billing_cycle: billingCycle.trim() || current.billing_cycle || "monthly",
      currency: current.currency || "BRL",
      is_active: current.is_active !== false
    })
  });
  const payload = await showResult(response);
  if (payload) {
    await loadCatalogPlans();
  }
}

async function loadCatalogPlans() {
  const response = await fetch("/admin/panel/catalog/plans", buildCentralRequestOptions());
  const payload = await showResult(response);
  if (!payload) {
    return;
  }
  setPanelCache("catalogPlans", payload);
  syncSalesCatalogOptions();
  const meta = document.getElementById("catalogPlansMeta");
  if (meta) {
    meta.textContent = `Planos ${payload.total || 0}`;
  }
  const list = document.getElementById("catalogPlansList");
  if (list) {
    list.innerHTML = (payload.items || []).length
      ? payload.items
          .map(
            (item) => `
              <div class="list-item">
                <strong>${item.name}</strong> | ${item.code} | ${item.billing_cycle || "-"} | R$ ${Number(item.amount || 0).toFixed(2)} | Produto ${item.product_id || "-"}
                <button class="table-action" type="button" onclick="updateCatalogPlan(${item.id})">Editar</button>
              </div>
            `
          )
          .join("")
      : '<div class="list-item">Nenhum plano cadastrado.</div>';
  }
}

function prepareClientSale() {
  const activeId = getActiveCompanyAccountId();
  if (!activeId) {
    showToast("Selecione uma conta antes de abrir nova venda.", "error");
    return;
  }
  const salesAccount = document.getElementById("salesCompanyAccountId");
  if (salesAccount) {
    salesAccount.value = String(activeId);
  }
  const summaryAccount = document.getElementById("summaryCompanyAccountId");
  if (summaryAccount) {
    summaryAccount.value = String(activeId);
  }
  activateSectionAndScroll("sales", "salesDescription");
  loadOrdersSummary().catch(() => {});
}

function filterTenantAccounts() {
  filterClientDirectory();
}

function setActiveCompanyAccount(accountId) {
  const value = accountId ? String(accountId) : "";
  const ids = [
    "activeCompanyAccountId",
    "summaryCompanyAccountId",
    "relationshipCompanyAccountId",
    "crmCompanyAccountId",
    "tenantAccountId",
    "salesCompanyAccountId",
    "proposalCompanyAccountId",
    "contractCompanyAccountId"
  ];
  ids.forEach((id) => {
    const element = document.getElementById(id);
    if (element) {
      element.value = value;
    }
  });
  if (value) {
    const selected = (getPanelCache("companyAccounts")?.items || []).find((item) => item.id === accountId) || null;
    const tenantCompanyName = document.getElementById("tenantCompanyName");
    if (tenantCompanyName && document.getElementById("companyName")) {
      tenantCompanyName.value = document.getElementById("companyName").value;
    }
    const tenantAdminCreateEmail = document.getElementById("tenantAdminCreateEmail");
    if (tenantAdminCreateEmail && document.getElementById("tenantAdminEmail")) {
      tenantAdminCreateEmail.value = document.getElementById("tenantAdminEmail").value;
    }
    applyTenantAccountSelection(selected);
    renderClientProfile(selected);
    renderClientDirectory(getVisibleCompanyAccounts());
    showToast(`Conta ${value} selecionada para pedidos e documentos.`);
  }
}

async function createCompanyAccount() {
  const response = await fetch("/admin/panel/account", {
    ...buildCentralRequestOptions({
      method: "POST",
      headers: { "Content-Type": "application/json" }
    }),
    body: JSON.stringify(buildCompanyAccountPayload())
  });
  const payload = await showResult(response);
  if (payload) {
    closeNewClientComposer();
    await loadCompanyAccounts();
  }
}

async function loadCompanyAccounts() {
  const response = await fetch("/admin/panel/accounts", buildCentralRequestOptions());
  const payload = await showResult(response);
  if (!payload) {
    return;
  }
  setPanelCache("companyAccounts", payload);
  renderClientDirectory(getVisibleCompanyAccounts());
  const meta = document.getElementById("accountsMeta");
  if (meta) {
    const total = (payload.items || []).length;
    const visible = getVisibleCompanyAccounts().length;
    const stage = getCompanyAccountStageFilter();
    const label = stage === "all" ? "Todos" : stage === "lead" ? "Leads" : "Clients";
    meta.textContent = `${label}: ${visible} de ${total}`;
  }
}

async function updateCompanyAccount(accountId, data) {
  const response = await fetch(`/admin/panel/account/${accountId}`, {
    ...buildCentralRequestOptions({
      method: "PATCH",
      headers: { "Content-Type": "application/json" }
    }),
    body: JSON.stringify(data)
  });
  const payload = await showResult(response);
  if (payload) {
    await loadCompanyAccounts();
  }
}

async function promoteCompanyAccount(accountId) {
  const response = await fetch(`/admin/panel/account/${accountId}/convert`, buildCentralRequestOptions({ method: "POST" }));
  const payload = await showResult(response);
  if (payload) {
    await loadCompanyAccounts();
    selectClientProfile(accountId, "summary");
  }
}

async function renameCompanyAccount(accountId, currentName, lifecycleStage = "lead", adminEmail = "", phone = "", companyDocument = "", notes = "") {
  const nextName = window.prompt("Novo nome da conta:", currentName);
  if (nextName === null) {
    return;
  }
  const cleaned = nextName.trim();
  if (!cleaned) {
    showToast("Informe um nome valido para a conta.", "error");
    return;
  }
  await updateCompanyAccount(accountId, {
    name: cleaned,
    lifecycle_stage: lifecycleStage,
    admin_email: adminEmail || null,
    phone: phone || null,
    company_document: companyDocument || null,
    notes: notes || null
  });
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
  const payload = await showResult(response);
  if (payload) {
    setPanelVisibility(true);
    activateSectionAndScroll("home", "topMetrics");
    await loadWorkspaceSummary();
  }
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
      email: document.getElementById("leadEmail").value,
      company_account_id: toOptionalInt(document.getElementById("crmCompanyAccountId").value) || getActiveCompanyAccountId()
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
      email: document.getElementById("clientEmail").value,
      company_account_id: toOptionalInt(document.getElementById("crmCompanyAccountId").value) || getActiveCompanyAccountId()
    })
  });
  await showResult(response);
  await loadClientsOnly();
}

async function createLeadFromAccount() {
  const response = await fetch("/admin/panel/account", {
    ...buildCentralRequestOptions({
      method: "POST",
      headers: { "Content-Type": "application/json" }
    }),
    body: JSON.stringify(buildRelationshipLeadPayload())
  });
  const payload = await showResult(response);
  if (payload) {
    setActiveCompanyAccount(payload.id);
    const relationshipAccount = document.getElementById("relationshipCompanyAccountId");
    if (relationshipAccount) {
      relationshipAccount.value = String(payload.id);
    }
    const crmLeadName = document.getElementById("leadName");
    const crmLeadEmail = document.getElementById("leadEmail");
    if (crmLeadName) {
      crmLeadName.value = document.getElementById("accountLeadName").value;
    }
    if (crmLeadEmail) {
      crmLeadEmail.value = document.getElementById("accountLeadEmail").value;
    }
    const tenantCompanyName = document.getElementById("tenantCompanyName");
    const tenantAdminCreateEmail = document.getElementById("tenantAdminCreateEmail");
    if (tenantCompanyName) {
      tenantCompanyName.value = document.getElementById("accountLeadName").value;
    }
    if (tenantAdminCreateEmail) {
      tenantAdminCreateEmail.value = document.getElementById("accountLeadEmail").value;
    }
    await loadCompanyAccounts();
  }
}

async function createClientFromAccount() {
  const accountId = toOptionalInt(document.getElementById("relationshipCompanyAccountId").value) || getActiveCompanyAccountId();
  if (!accountId) {
    showToast("Crie ou selecione a conta lead antes de virar cliente.", "error");
    return;
  }
  const nextName = (document.getElementById("accountClientName").value || "").trim();
  const nextEmail = (document.getElementById("accountClientEmail").value || "").trim();
  if (nextName || nextEmail) {
    const response = await fetch(`/admin/panel/account/${accountId}`, {
      ...buildCentralRequestOptions({
        method: "PATCH",
        headers: { "Content-Type": "application/json" }
      }),
      body: JSON.stringify({
        name: nextName || document.getElementById("accountLeadName").value,
        lifecycle_stage: "lead",
        admin_email: nextEmail || document.getElementById("accountLeadEmail").value || null,
        phone: null,
        company_document: null,
        notes: "Lead preparado para conversao."
      })
    });
    const updatePayload = await showResult(response);
    if (!updatePayload) {
      return;
    }
  }
  await promoteCompanyAccount(accountId);
  const tenantCompanyName = document.getElementById("tenantCompanyName");
  const tenantAdminCreateEmail = document.getElementById("tenantAdminCreateEmail");
  if (tenantCompanyName) {
    tenantCompanyName.value = nextName || document.getElementById("accountLeadName").value;
  }
  if (tenantAdminCreateEmail) {
    tenantAdminCreateEmail.value = nextEmail || document.getElementById("accountLeadEmail").value;
  }
  switchWorkspaceFlowTab("workspace");
}

async function createSalesOrder() {
  const addonIds = Array.from(document.querySelectorAll("#salesAddonList input[type='checkbox']:checked"))
    .map((input) => Number(input.value));
  const response = await fetch(`/admin/panel/${getTenantSlug()}/sales-order`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({
      title: document.getElementById("salesDescription").value,
      quantity: Number(document.getElementById("salesQuantity").value || "1"),
      unit_price: Number(document.getElementById("salesPrice").value || "0"),
      first_due_date: document.getElementById("salesDueDate").value,
      company_account_id: toOptionalInt(document.getElementById("salesCompanyAccountId").value) || getActiveCompanyAccountId(),
      plan_id: toOptionalInt(document.getElementById("salesPlanId")?.value || ""),
      addon_ids: addonIds
    })
  });
  const payload = await showResult(response);
  if (payload && payload.id) {
    document.getElementById("proposalOrderId").value = payload.id;
    document.getElementById("contractOrderId").value = payload.id;
    document.getElementById("salesEditOrderId").value = payload.id;
  }
  await loadOrdersSummary();
}

async function updateSalesOrderDetails() {
  const orderId = Number(document.getElementById("salesEditOrderId").value || "0");
  if (!orderId) {
    showToast("Informe o ID do pedido para editar.", "error");
    return;
  }
  const response = await fetch(`/admin/panel/${getTenantSlug()}/sales-order/${orderId}/details`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({
      title: document.getElementById("salesEditDescription").value,
      quantity: Number(document.getElementById("salesEditQuantity").value || "1"),
      unit_price: Number(document.getElementById("salesEditPrice").value || "0"),
      first_due_date: document.getElementById("salesEditDueDate").value
    })
  });
  await showResult(response);
  invalidatePanelDomains("orders", "finance");
  await loadOrdersSummary();
}

async function createProposal() {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/proposal`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({
      title: document.getElementById("proposalTitle").value,
      sales_order_id: toOptionalInt(document.getElementById("proposalOrderId").value),
      company_account_id: toOptionalInt(document.getElementById("proposalCompanyAccountId").value) || getActiveCompanyAccountId()
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
      sales_order_id: toOptionalInt(document.getElementById("contractOrderId").value),
      company_account_id: toOptionalInt(document.getElementById("contractCompanyAccountId").value) || getActiveCompanyAccountId()
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
  const companyAccountId = toOptionalInt(document.getElementById("summaryCompanyAccountId").value) || getActiveCompanyAccountId();
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
  if (companyAccountId) {
    query.set("company_account_id", String(companyAccountId));
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
    buildDataRow(
      `Receber #${item.id}`,
      `${item.category || "-"} | ${item.due_date} | R$ ${Number(item.amount).toFixed(2)}`,
      item.status,
      `
        <button class="table-action" onclick="settleReceivable(${item.id})">Dar baixa</button>
        <button class="table-action" onclick="openStatusEditor('receivable', ${item.id}, '${item.status}')">Atualizar status</button>
        <button class="table-action" onclick="deleteReceivable(${item.id})">Excluir</button>
      `,
      { entity: "recebivel", title: `Receber #${item.id}`, subtitle: `${item.category || "-"} | ${item.due_date} | R$ ${Number(item.amount).toFixed(2)}`, status: item.status, meta: [item.category || "Sem categoria", item.due_date || "Sem vencimento"] }
    )
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
    buildDataRow(
      `Pagar #${item.id}`,
      `${item.category || "-"} | ${item.due_date} | R$ ${Number(item.amount).toFixed(2)}`,
      item.status,
      `
        <button class="table-action" onclick="settlePayable(${item.id})">Conciliar</button>
        <button class="table-action" onclick="openStatusEditor('payable', ${item.id}, '${item.status}')">Atualizar status</button>
        <button class="table-action" onclick="deletePayable(${item.id})">Excluir</button>
      `,
      { entity: "pagavel", title: `Pagar #${item.id}`, subtitle: `${item.category || "-"} | ${item.due_date} | R$ ${Number(item.amount).toFixed(2)}`, status: item.status, meta: [item.category || "Sem categoria", item.due_date || "Sem vencimento"] }
    )
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
      buildDataRow(
        `Receber #${item.id}`,
        `${item.category || "-"} | ${item.due_date || "-"} | R$ ${Number(item.amount).toFixed(2)}`,
        item.status,
        `
          <button class="table-action" onclick="settleReceivable(${item.id})">Dar baixa</button>
          <button class="table-action" onclick="openStatusEditor('receivable', ${item.id}, '${item.status}')">Atualizar status</button>
          <button class="table-action" onclick="deleteReceivable(${item.id})">Excluir</button>
        `,
        { entity: "recebivel", title: `Receber #${item.id}`, subtitle: `${item.category || "-"} | ${item.due_date || "-"} | R$ ${Number(item.amount).toFixed(2)}`, status: item.status, meta: [item.category || "Sem categoria", item.due_date || "Sem vencimento"] }
      )
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
      buildDataRow(
        `Pagar #${item.id}`,
        `${item.category || "-"} | ${item.due_date || "-"} | R$ ${Number(item.amount).toFixed(2)}`,
        item.status,
        `
          <button class="table-action" onclick="settlePayable(${item.id})">Conciliar</button>
          <button class="table-action" onclick="openStatusEditor('payable', ${item.id}, '${item.status}')">Atualizar status</button>
          <button class="table-action" onclick="deletePayable(${item.id})">Excluir</button>
        `,
        { entity: "pagavel", title: `Pagar #${item.id}`, subtitle: `${item.category || "-"} | ${item.due_date || "-"} | R$ ${Number(item.amount).toFixed(2)}`, status: item.status, meta: [item.category || "Sem categoria", item.due_date || "Sem vencimento"] }
      )
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
      buildDataRow(
        `Mensagem #${item.id}`,
        `${item.direction} | ${item.body}`,
        item.status,
        `<button class="table-action" onclick="openStatusEditor('message', ${item.id}, '${item.status}')">Atualizar status</button>`,
        { entity: "mensagem", title: `Mensagem #${item.id}`, subtitle: `${item.direction} | ${item.body}`, status: item.status, meta: [item.direction, item.body] }
      )
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
      buildDataRow(
        `Mensagem #${item.id}`,
        `${item.direction} | ${item.body}`,
        item.status,
        `<button class="table-action" onclick="openStatusEditor('message', ${item.id}, '${item.status}')">Atualizar status</button>`,
        { entity: "mensagem", title: `Mensagem #${item.id}`, subtitle: `${item.direction} | ${item.body}`, status: item.status, meta: [item.direction, item.body] }
      )
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

async function updateReceivableStatus(id, statusOverride = "") {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/finance/receivable/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ status: statusOverride || selectedValue("receivableStatusUpdate", "paid") })
  });
  await showResult(response);
  invalidatePanelDomains("finance");
  await loadReceivables();
}

async function settleReceivable(id) {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/finance/receivable/${id}/settle`, {
    method: "POST",
    credentials: "same-origin"
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

async function updatePayableStatus(id, statusOverride = "") {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/finance/payable/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ status: statusOverride || selectedValue("payableStatusUpdate", "paid") })
  });
  await showResult(response);
  invalidatePanelDomains("finance");
  await loadPayables();
}

async function settlePayable(id) {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/finance/payable/${id}/settle`, {
    method: "POST",
    credentials: "same-origin"
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

async function updateMessageStatus(id, statusOverride = "") {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/message/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ status: statusOverride || selectedValue("messageStatusUpdate", "read") })
  });
  await showResult(response);
  invalidatePanelDomains("messages");
  await loadMessagesSummary();
}

async function renameLead(id, nameOverride = "") {
  const name = nameOverride || document.getElementById(`leadNameEdit-${id}`)?.value.trim() || "";
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

async function renameClient(id, nameOverride = "") {
  const name = nameOverride || document.getElementById(`clientNameEdit-${id}`)?.value.trim() || "";
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

async function updateSalesOrderStatus(id, statusOverride = "") {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/sales-order/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ status: statusOverride || selectedValue("salesOrderStatusUpdate", "confirmed") })
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

async function renameProposal(id, titleOverride = "") {
  const title = titleOverride || document.getElementById(`proposalTitleEdit-${id}`)?.value.trim() || "";
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

async function renameContract(id, titleOverride = "") {
  const title = titleOverride || document.getElementById(`contractTitleEdit-${id}`)?.value.trim() || "";
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

async function updateContractStatus(id, statusOverride = "") {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/contract/${id}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ status: statusOverride || selectedValue("contractStatusUpdate", "sent") })
  });
  await showResult(response);
  invalidatePanelDomains("documents");
  await loadContractsOnly();
}

function openLeadEditor(id, currentName = "") {
  openEditorDrawer({
    entity: "lead",
    id,
    title: `Editar lead #${id}`,
    value: currentName,
    placeholder: "Novo nome do lead",
    onSubmit: async ({ id: itemId, value }) => renameLead(itemId, value),
    onSuccess: closeEditorDrawer
  });
}

function openClientEditor(id, currentName = "") {
  openEditorDrawer({
    entity: "client",
    id,
    title: `Editar client #${id}`,
    value: currentName,
    placeholder: "Novo nome do client",
    onSubmit: async ({ id: itemId, value }) => renameClient(itemId, value),
    onSuccess: closeEditorDrawer
  });
}

function openProposalEditor(id, currentTitle = "") {
  openEditorDrawer({
    entity: "proposal",
    id,
    title: `Editar proposta #${id}`,
    value: currentTitle,
    placeholder: "Novo titulo da proposta",
    onSubmit: async ({ id: itemId, value }) => renameProposal(itemId, value),
    onSuccess: closeEditorDrawer
  });
}

function openContractEditor(id, currentTitle = "") {
  openEditorDrawer({
    entity: "contract",
    id,
    title: `Editar contrato #${id}`,
    value: currentTitle,
    placeholder: "Novo titulo do contrato",
    onSubmit: async ({ id: itemId, value }) => renameContract(itemId, value),
    onSuccess: closeEditorDrawer
  });
}

function openStatusEditor(entity, id, currentStatus = "") {
  const optionsMap = {
    sales_order: ["confirmed", "pending", "closed", "cancelled"],
    contract: ["draft", "sent", "signed", "cancelled"],
    receivable: ["paid", "pending", "overdue", "cancelled"],
    payable: ["paid", "pending", "overdue", "cancelled"],
    message: ["read", "sent", "delivered", "failed"]
  };
  const handlers = {
    sales_order: (payload) => updateSalesOrderStatus(payload.id, payload.status),
    contract: (payload) => updateContractStatus(payload.id, payload.status),
    receivable: (payload) => updateReceivableStatus(payload.id, payload.status),
    payable: (payload) => updatePayableStatus(payload.id, payload.status),
    message: (payload) => updateMessageStatus(payload.id, payload.status)
  };
  openEditorDrawer({
    entity,
    id,
    mode: "status",
    title: `Atualizar status`,
    value: currentStatus,
    options: optionsMap[entity] || [],
    hint: "Selecione o status e confirme.",
    onSubmit: async ({ id: itemId, status }) => handlers[entity]({ id: itemId, status }),
    onSuccess: closeEditorDrawer
  });
}

async function submitEditorDrawer() {
  const onSubmit = panelEditor.onSubmit;
  if (!onSubmit) {
    closeEditorDrawer();
    return;
  }
  const id = Number(document.getElementById("editorDrawerItemId").value || "0");
  const statusField = document.getElementById("editorStatusField");
  const isStatusMode = !statusField.classList.contains("hidden");
  const payload = {
    id,
    value: document.getElementById("editorDrawerName").value.trim(),
    status: document.getElementById("editorDrawerStatus").value
  };
  if (!id) {
    showToast("Item invalido para edicao.", "error");
    return;
  }
  if (!isStatusMode && !payload.value) {
    showToast("Informe um valor para salvar.", "error");
    return;
  }
  await onSubmit(payload);
  if (panelEditor.onSuccess) {
    panelEditor.onSuccess();
  }
}

async function loadDocumentsSummary() {
  const query = new URLSearchParams({
    documents_page: document.getElementById("documentsPage").value || "1",
    documents_page_size: document.getElementById("documentsPageSize").value || "5"
  });
  const documentFilter = document.getElementById("documentQuery").value.trim();
  const contractStatus = selectedValue("contractStatusFilter");
  const companyAccountId = toOptionalInt(document.getElementById("summaryCompanyAccountId").value) || getActiveCompanyAccountId();
  query.set("sort_by", selectedValue("documentSortBy", "id"));
  query.set("sort_dir", selectedValue("documentSortDir", "desc"));
  if (documentFilter) {
    query.set("document_q", documentFilter);
  }
  if (contractStatus) {
    query.set("contract_status", contractStatus);
  }
  if (companyAccountId) {
    query.set("company_account_id", String(companyAccountId));
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
      <button onclick="settleReceivable(${item.id})">Dar baixa</button>
      <button onclick="updateReceivableStatus(${item.id})">Atualizar status</button>
      <button onclick="deleteReceivable(${item.id})">Excluir</button>`
    );
    renderList("payablesList", payload.payables || [], (item) =>
      `#${item.id} | ${item.status} | R$ ${Number(item.amount).toFixed(2)}<br>
      ${item.category || "-"} | ${item.due_date || "-"}<br>
      <button onclick="settlePayable(${item.id})">Conciliar</button>
      <button onclick="updatePayableStatus(${item.id})">Atualizar status</button>
      <button onclick="deletePayable(${item.id})">Excluir</button>`
    );
  }
}

async function runFinanceReconcile() {
  const response = await fetch(`/admin/panel/${getTenantSlug()}/finance/reconcile`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({
      status: selectedValue("financeFilterStatus") || null,
      category: document.getElementById("financeFilterCategory").value.trim() || null,
      due_from: document.getElementById("financeFilterFrom").value.trim() || null,
      due_to: document.getElementById("financeFilterTo").value.trim() || null
    })
  });
  const payload = await showResult(response);
  if (payload) {
    const financeMeta = document.getElementById("financeMeta");
    if (financeMeta) {
      financeMeta.textContent = `Conciliacao: AR ${payload.receivable_count} / R$ ${Number(payload.receivable_total || 0).toFixed(2)} | AP ${payload.payable_count} / R$ ${Number(payload.payable_total || 0).toFixed(2)} | Saldo R$ ${Number(payload.net_total || 0).toFixed(2)}`;
    }
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
      buildDataRow(
        item.name,
        item.email || "-",
        "lead",
        `
          <button class="table-action" onclick="openLeadEditor(${item.id}, '${String(item.name).replace(/'/g, "\\'")}')">Editar</button>
          <button class="table-action" onclick="deleteLead(${item.id})">Excluir</button>
        `,
        { entity: "lead", title: item.name, subtitle: item.email || "-", status: "lead", meta: [`Lead #${item.id}`, item.email || "Sem email"] }
      )
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
      buildDataRow(
        item.name,
        item.email || "-",
        "client",
        `
          <button class="table-action" onclick="openClientEditor(${item.id}, '${String(item.name).replace(/'/g, "\\'")}')">Editar</button>
          <button class="table-action" onclick="deleteClient(${item.id})">Excluir</button>
        `,
        { entity: "client", title: item.name, subtitle: item.email || "-", status: "client", meta: [`Client #${item.id}`, item.email || "Sem email"] }
      )
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
  const companyAccountId = toOptionalInt(document.getElementById("summaryCompanyAccountId").value) || getActiveCompanyAccountId();
  if (documentFilter) query.set("document_q", documentFilter);
  if (companyAccountId) query.set("company_account_id", String(companyAccountId));
  const response = await fetch(`/admin/panel/${getTenantSlug()}/summary/proposals?${query.toString()}`, { credentials: "same-origin" });
  const payload = await showResult(response);
  if (payload) {
    setPanelCache("proposals", payload);
    renderList("proposalsList", payload.items || [], (item) =>
      (() => {
        const pkg = formatDocumentSalesPackage(item);
        return buildDataRow(
        item.title,
        `${item.pdf_path || "sem pdf"} | Conta ${item.company_account_id || "-"} | ${pkg.summary}`,
        "proposta",
        `
          <button class="table-action" onclick="openProposalEditor(${item.id}, '${String(item.title).replace(/'/g, "\\'")}')">Renomear</button>
          <button class="table-action" onclick="deleteProposal(${item.id})">Excluir</button>
        `,
        { entity: "proposta", title: item.title, subtitle: `${item.pdf_path || "sem pdf"} | Conta ${item.company_account_id || "-"} | ${pkg.summary}`, status: "proposta", meta: [`Proposta #${item.id}`, item.pdf_path || "Sem PDF gerado", `Conta ${item.company_account_id || "-"}`, `Plano ${pkg.planLabel}`, `Add-ons ${pkg.addonsLabel}`] }
      );
      })()
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
  const companyAccountId = toOptionalInt(document.getElementById("summaryCompanyAccountId").value) || getActiveCompanyAccountId();
  if (documentFilter) query.set("document_q", documentFilter);
  if (contractStatus) query.set("contract_status", contractStatus);
  if (companyAccountId) query.set("company_account_id", String(companyAccountId));
  const response = await fetch(`/admin/panel/${getTenantSlug()}/summary/contracts?${query.toString()}`, { credentials: "same-origin" });
  const payload = await showResult(response);
  if (payload) {
    setPanelCache("contracts", payload);
    renderList("contractsList", payload.items || [], (item) =>
      (() => {
        const pkg = formatDocumentSalesPackage(item);
        return buildDataRow(
        item.title,
        `Contrato #${item.id} | Conta ${item.company_account_id || "-"} | ${pkg.summary}`,
        item.status,
        `
          <button class="table-action" onclick="openContractEditor(${item.id}, '${String(item.title).replace(/'/g, "\\'")}')">Renomear</button>
          <button class="table-action" onclick="openStatusEditor('contract', ${item.id}, '${item.status}')">Atualizar status</button>
          <button class="table-action" onclick="deleteContract(${item.id})">Excluir</button>
        `,
        { entity: "contrato", title: item.title, subtitle: `Contrato #${item.id} | Conta ${item.company_account_id || "-"} | ${pkg.summary}`, status: item.status, meta: [`Contrato #${item.id}`, `Status ${item.status}`, `Conta ${item.company_account_id || "-"}`, `Plano ${pkg.planLabel}`, `Add-ons ${pkg.addonsLabel}`] }
      );
      })()
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
  const companyAccountId = toOptionalInt(document.getElementById("summaryCompanyAccountId").value) || getActiveCompanyAccountId();
  query.set("sort_by", selectedValue("orderSortBy", "id"));
  query.set("sort_dir", selectedValue("orderSortDir", "desc"));
  if (orderStatus) {
    query.set("order_status", orderStatus);
  }
  if (companyAccountId) {
    query.set("company_account_id", String(companyAccountId));
  }
  const response = await fetch(`/admin/panel/${getTenantSlug()}/summary/orders?${query.toString()}`, { credentials: "same-origin" });
  const payload = await showResult(response);
  if (payload) {
    setPanelCache("orders", payload);
    renderList("salesOrdersList", payload.sales_orders || [], (item) =>
      (() => {
        const pkg = formatSalesCatalogPackage(item);
        return `#${item.id} | ${item.status} | R$ ${Number(item.total_amount).toFixed(2)} | Conta ${item.company_account_id || "-"} | ${pkg.summary}<br>
      <button onclick="updateSalesOrderStatus(${item.id})">Atualizar status</button>
      <button onclick="deleteSalesOrder(${item.id})">Excluir</button>`;
      })()
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
      buildDataRow(
        item.name,
        item.email || "-",
        "lead",
        `
          <button class="table-action" onclick="openLeadEditor(${item.id}, '${String(item.name).replace(/'/g, "\\'")}')">Editar</button>
          <button class="table-action" onclick="deleteLead(${item.id})">Excluir</button>
        `,
        { entity: "lead", title: item.name, subtitle: item.email || "-", status: "lead", meta: [`Lead #${item.id}`, item.email || "Sem email"] }
      )
    );
    renderList("clientsList", clientsBlock.items || [], (item) =>
      buildDataRow(
        item.name,
        item.email || "-",
        "client",
        `
          <button class="table-action" onclick="openClientEditor(${item.id}, '${String(item.name).replace(/'/g, "\\'")}')">Editar</button>
          <button class="table-action" onclick="deleteClient(${item.id})">Excluir</button>
        `,
        { entity: "client", title: item.name, subtitle: item.email || "-", status: "client", meta: [`Client #${item.id}`, item.email || "Sem email"] }
      )
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
  const companyAccountId = toOptionalInt(document.getElementById("summaryCompanyAccountId").value) || getActiveCompanyAccountId();
  if (orderStatus) {
    query.set("order_status", orderStatus);
  }
  if (companyAccountId) {
    query.set("company_account_id", String(companyAccountId));
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
  const companyAccountId = toOptionalInt(document.getElementById("summaryCompanyAccountId").value) || getActiveCompanyAccountId();
  if (documentFilter) common.set("document_q", documentFilter);
  if (contractStatus) common.set("contract_status", contractStatus);
  if (companyAccountId) common.set("company_account_id", String(companyAccountId));
  common.set("sort_by", selectedValue("documentSortBy", "id"));
  common.set("sort_dir", selectedValue("documentSortDir", "desc"));
  openPanelDownload("/summary/proposals/export", common);
  openPanelDownload("/summary/contracts/export", common);
}

async function exportProposalsCsv() {
  const query = new URLSearchParams();
  const documentFilter = document.getElementById("documentQuery").value.trim();
  const companyAccountId = toOptionalInt(document.getElementById("summaryCompanyAccountId").value) || getActiveCompanyAccountId();
  if (documentFilter) query.set("document_q", documentFilter);
  if (companyAccountId) query.set("company_account_id", String(companyAccountId));
  query.set("sort_by", selectedValue("documentSortBy", "id"));
  query.set("sort_dir", selectedValue("documentSortDir", "desc"));
  openPanelDownload("/summary/proposals/export", query);
}

async function exportContractsCsv() {
  const query = new URLSearchParams();
  const documentFilter = document.getElementById("documentQuery").value.trim();
  const contractStatus = selectedValue("contractStatusFilter");
  const companyAccountId = toOptionalInt(document.getElementById("summaryCompanyAccountId").value) || getActiveCompanyAccountId();
  if (documentFilter) query.set("document_q", documentFilter);
  if (contractStatus) query.set("contract_status", contractStatus);
  if (companyAccountId) query.set("company_account_id", String(companyAccountId));
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
