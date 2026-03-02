function renderDataRow(targetId, items, mapper) {
  renderList(targetId, items, (item) => mapper(item));
}

function buildDataRow(title, subtitle, status, actionsHtml = "") {
  return `
    <div class="data-row">
      <div class="data-row-main">
        <div>
          <div class="data-row-title">${title}</div>
          <div class="data-row-subtitle">${subtitle}</div>
        </div>
        ${status ? `<div class="status-chip">${status}</div>` : ""}
      </div>
      ${actionsHtml ? `<div class="data-row-actions">${actionsHtml}</div>` : ""}
    </div>
  `;
}

function metricCard(label, value, section, targetId) {
  return `
    <button class="metric-card" type="button" onclick="activateSectionAndScroll('${section}', '${targetId}')">
      <span>${label}</span>
      <strong>${value}</strong>
    </button>
  `;
}

function renderSummary(summary) {
  const topMetrics = document.getElementById("topMetrics");
  if (topMetrics) {
    const metricCards = [
      metricCard("Pedidos", summary.sales_orders_total || 0, "sales", "salesOrdersList"),
      metricCard("Pendentes", summary.pending_orders_total || 0, "sales", "salesOrdersList"),
      metricCard("Leads", summary.leads_total || 0, "crm", "leadsList"),
      metricCard("Clients", summary.clients_total || 0, "crm", "clientsList"),
      metricCard("Docs", summary.documents_total || 0, "docs", "proposalsList"),
      metricCard("Prop Send", summary.proposals_sendable_total || 0, "docs", "proposalsList"),
      metricCard("Ctr Assin", summary.contracts_signed_total || 0, "docs", "contractsList"),
      metricCard("Ctr Pend", summary.contracts_pending_signature_total || 0, "docs", "contractsList"),
      metricCard("Msgs", summary.messages_total || 0, "whatsapp", "messagesList"),
      metricCard("Falhas", summary.failed_messages_total || 0, "whatsapp", "messagesList"),
      metricCard("AR", `R$ ${Number(summary.finance?.receivable_total || 0).toFixed(2)}`, "finance", "receivablesList"),
      metricCard("AP", `R$ ${Number(summary.finance?.payable_total || 0).toFixed(2)}`, "finance", "payablesList")
    ];
    topMetrics.innerHTML = metricCards.join("");
  }

  const activeFilters = [];
  if (summary.query) activeFilters.push(`Busca: ${summary.query}`);
  if (summary.people_email) activeFilters.push(`Email: ${summary.people_email}`);
  if (summary.people_phone) activeFilters.push(`Telefone: ${summary.people_phone}`);
  if (summary.order_status) activeFilters.push(`Pedido: ${summary.order_status}`);
  if (summary.contract_status) activeFilters.push(`Contrato: ${summary.contract_status}`);
  if (summary.message_status) activeFilters.push(`Msg status: ${summary.message_status}`);
  if (summary.message_direction) activeFilters.push(`Msg dir: ${summary.message_direction}`);
  renderList("activeFilters", activeFilters, (item) => item);

  const qrBlock = document.getElementById("whatsappQrCard");
  if (qrBlock) {
    if (summary.whatsapp && summary.whatsapp.last_qr_code) {
      qrBlock.innerHTML = `
        <div class="qr-panel">
          <div class="qr-label">QR WhatsApp</div>
          <div class="tiny">${summary.whatsapp.status || "-"}</div>
          <div class="qr-value" id="whatsappQrValue">${summary.whatsapp.last_qr_code}</div>
          <button onclick="copyWhatsappQr()">Copiar QR</button>
        </div>
      `;
    } else {
      qrBlock.innerHTML = '<div class="list-item">Sem QR de WhatsApp disponivel.</div>';
    }
  }

  renderDataRow("salesOrdersList", summary.sales_orders || [], (item) =>
    buildDataRow(
      `Pedido #${item.id}`,
      `Total R$ ${Number(item.total_amount).toFixed(2)}`,
      item.status,
      `
        <button class="table-action" onclick="openStatusEditor('sales_order', ${item.id}, '${item.status}')">Atualizar status</button>
        <button class="table-action" onclick="deleteSalesOrder(${item.id})">Excluir</button>
      `
    )
  );

  renderDataRow("proposalsList", summary.proposals || [], (item) =>
    buildDataRow(
      item.title,
      item.pdf_path || "Sem PDF gerado",
      "proposta",
      `
        <button class="table-action" onclick="openProposalEditor(${item.id}, '${String(item.title).replace(/'/g, "\\'")}')">Renomear</button>
        <button class="table-action" onclick="deleteProposal(${item.id})">Excluir</button>
      `
    )
  );

  renderDataRow("contractsList", summary.contracts || [], (item) =>
    buildDataRow(
      item.title,
      `Contrato #${item.id}`,
      item.status,
      `
        <button class="table-action" onclick="openContractEditor(${item.id}, '${String(item.title).replace(/'/g, "\\'")}')">Renomear</button>
        <button class="table-action" onclick="openStatusEditor('contract', ${item.id}, '${item.status}')">Atualizar status</button>
        <button class="table-action" onclick="deleteContract(${item.id})">Excluir</button>
      `
    )
  );

  renderDataRow("leadsList", summary.leads || [], (item) =>
    buildDataRow(
      item.name,
      item.email || "-",
      "lead",
      `
        <button class="table-action" onclick="openLeadEditor(${item.id}, '${String(item.name).replace(/'/g, "\\'")}')">Editar</button>
        <button class="table-action" onclick="deleteLead(${item.id})">Excluir</button>
      `
    )
  );

  renderDataRow("clientsList", summary.clients || [], (item) =>
    buildDataRow(
      item.name,
      item.email || "-",
      "client",
      `
        <button class="table-action" onclick="openClientEditor(${item.id}, '${String(item.name).replace(/'/g, "\\'")}')">Editar</button>
        <button class="table-action" onclick="deleteClient(${item.id})">Excluir</button>
      `
    )
  );

  const workspaceMeta = [];
  workspaceMeta.push(`Categorias: ${summary.finance?.category_count || 0}`);
  workspaceMeta.push(`AR total: R$ ${Number(summary.finance?.receivable_total || 0).toFixed(2)}`);
  workspaceMeta.push(`AR pendente: R$ ${Number(summary.finance?.receivable_pending || 0).toFixed(2)}`);
  if (summary.whatsapp) {
    workspaceMeta.push(
      `WhatsApp: ${summary.whatsapp.status} (${summary.whatsapp.provider_session_id || "-"})<br>
      Sessao ativa: ${summary.whatsapp_connected ? "sim" : "nao"}<br>
      <button onclick="updateWhatsappSessionStatus()">Atualizar status</button>`
    );
  } else {
    workspaceMeta.push("WhatsApp: sem sessao");
  }
  renderList("workspaceMeta", workspaceMeta, (item) => item);

  renderDataRow("receivablesList", summary.receivables || [], (item) =>
    buildDataRow(
      `Receber #${item.id}`,
      `${item.category || "-"} | ${item.due_date || "-"} | R$ ${Number(item.amount).toFixed(2)}`,
      item.status,
      `
        <button class="table-action" onclick="settleReceivable(${item.id})">Dar baixa</button>
        <button class="table-action" onclick="openStatusEditor('receivable', ${item.id}, '${item.status}')">Atualizar status</button>
        <button class="table-action" onclick="deleteReceivable(${item.id})">Excluir</button>
      `
    )
  );

  renderDataRow("payablesList", summary.payables || [], (item) =>
    buildDataRow(
      `Pagar #${item.id}`,
      `${item.category || "-"} | ${item.due_date || "-"} | R$ ${Number(item.amount).toFixed(2)}`,
      item.status,
      `
        <button class="table-action" onclick="settlePayable(${item.id})">Conciliar</button>
        <button class="table-action" onclick="openStatusEditor('payable', ${item.id}, '${item.status}')">Atualizar status</button>
        <button class="table-action" onclick="deletePayable(${item.id})">Excluir</button>
      `
    )
  );

  renderDataRow("messagesList", summary.messages || [], (item) =>
    buildDataRow(
      `Mensagem #${item.id}`,
      `${item.direction} | ${item.body}`,
      item.status,
      `<button class="table-action" onclick="openStatusEditor('message', ${item.id}, '${item.status}')">Atualizar status</button>`
    )
  );

  const ordersMeta = document.getElementById("ordersMeta");
  if (ordersMeta) {
    ordersMeta.textContent = `Pagina ${summary.page}/${Math.max(1, Math.ceil((summary.sales_orders_total || 0) / Math.max(summary.page_size || 1, 1)))} | total ${summary.sales_orders_total || 0}`;
  }
  const docsMeta = document.getElementById("documentsMeta");
  if (docsMeta) {
    docsMeta.textContent = `Pagina ${summary.documents_page}/${Math.max(1, Math.ceil((summary.documents_total || 0) / Math.max(summary.documents_page_size || 1, 1)))} | total ${summary.documents_total || 0}`;
  }
  const proposalsMeta = document.getElementById("proposalsMeta");
  if (proposalsMeta) {
    proposalsMeta.textContent = `Itens ${summary.proposals?.length || 0}`;
  }
  const contractsMeta = document.getElementById("contractsMeta");
  if (contractsMeta) {
    contractsMeta.textContent = `Itens ${summary.contracts?.length || 0}`;
  }
  const leadsMeta = document.getElementById("leadsMeta");
  if (leadsMeta) {
    leadsMeta.textContent = `Pagina ${summary.leads_page || 1}/${Math.max(1, Math.ceil((summary.leads_total || 0) / Math.max(summary.leads_page_size || 1, 1)))} | total ${summary.leads_total || 0}`;
  }
  const clientsMeta = document.getElementById("clientsMeta");
  if (clientsMeta) {
    clientsMeta.textContent = `Pagina ${summary.clients_page || 1}/${Math.max(1, Math.ceil((summary.clients_total || 0) / Math.max(summary.clients_page_size || 1, 1)))} | total ${summary.clients_total || 0}`;
  }
  const messagesMeta = document.getElementById("messagesMeta");
  if (messagesMeta) {
    messagesMeta.textContent = `Pagina ${summary.messages_page}/${Math.max(1, Math.ceil((summary.messages_total || 0) / Math.max(summary.messages_page_size || 1, 1)))} | total ${summary.messages_total || 0} | out ${summary.outbound_messages_total || 0} | in ${summary.inbound_messages_total || 0}`;
  }
  const financeMeta = document.getElementById("financeMeta");
  if (financeMeta) {
    financeMeta.textContent = `AR R$ ${Number(summary.finance?.receivable_total || 0).toFixed(2)} | AP R$ ${Number(summary.finance?.payable_total || 0).toFixed(2)} | pendente R$ ${Number(summary.finance?.receivable_pending || 0).toFixed(2)}`;
  }
  const receivablesMeta = document.getElementById("receivablesMeta");
  if (receivablesMeta) {
    receivablesMeta.textContent = `Itens ${summary.receivables?.length || 0}`;
  }
  const payablesMeta = document.getElementById("payablesMeta");
  if (payablesMeta) {
    payablesMeta.textContent = `Itens ${summary.payables?.length || 0}`;
  }
}
