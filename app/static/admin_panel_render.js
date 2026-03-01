function renderSummary(summary) {
  renderList("topMetrics", [
    `Pedidos: ${summary.sales_orders_total || 0}`,
    `Leads: ${summary.leads_total || 0}`,
    `Clients: ${summary.clients_total || 0}`,
    `Docs: ${summary.documents_total || 0}`,
    `Msgs: ${summary.messages_total || 0}`,
    `Out: ${summary.outbound_messages_total || 0}`,
    `In: ${summary.inbound_messages_total || 0}`,
    `AP: R$ ${Number(summary.finance?.payable_total || 0).toFixed(2)}`
  ], (item) => item);
  renderList("salesOrdersList", summary.sales_orders || [], (item) =>
    `#${item.id} | ${item.status} | R$ ${Number(item.total_amount).toFixed(2)}<br>
    <button onclick="updateSalesOrderStatus(${item.id})">Atualizar status</button>
    <button onclick="deleteSalesOrder(${item.id})">Excluir</button>`
  );
  const ordersMeta = document.getElementById("ordersMeta");
  if (ordersMeta) {
    ordersMeta.textContent = `Pedidos: pagina ${summary.page}/${Math.max(1, Math.ceil((summary.sales_orders_total || 0) / Math.max(summary.page_size || 1, 1)))}, total ${summary.sales_orders_total || 0}`;
  }
  renderList("proposalsList", summary.proposals || [], (item) =>
    `#${item.id} | ${item.title}<br>${item.pdf_path || "sem pdf"}<br>
    <input id="proposalTitleEdit-${item.id}" placeholder="Novo titulo">
    <button onclick="renameProposal(${item.id})">Renomear</button>
    <button onclick="deleteProposal(${item.id})">Excluir</button>`
  );
  renderList("contractsList", summary.contracts || [], (item) =>
    `#${item.id} | ${item.title} | ${item.status}<br>
    <input id="contractTitleEdit-${item.id}" placeholder="Novo titulo">
    <button onclick="renameContract(${item.id})">Renomear</button>
    <button onclick="updateContractStatus(${item.id})">Atualizar status</button>
    <button onclick="deleteContract(${item.id})">Excluir</button>`
  );
  renderList("leadsList", summary.leads || [], (item) =>
    `#${item.id} | ${item.name}<br>${item.email || "-"}<br>
    <input id="leadNameEdit-${item.id}" placeholder="Novo nome">
    <button onclick="renameLead(${item.id})">Editar</button>
    <button onclick="deleteLead(${item.id})">Excluir</button>`
  );
  renderList("clientsList", summary.clients || [], (item) =>
    `#${item.id} | ${item.name}<br>${item.email || "-"}<br>
    <input id="clientNameEdit-${item.id}" placeholder="Novo nome">
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
      QR: ${summary.whatsapp.last_qr_code || "-"}<br>
      <button onclick="updateWhatsappSessionStatus()">Atualizar status</button>`
    );
  } else {
    meta.push("WhatsApp: sem sessao");
  }
  renderList("workspaceMeta", meta, (item) => item);

  renderList("receivablesList", summary.receivables || [], (item) =>
    `#${item.id} | ${item.status} | R$ ${Number(item.amount).toFixed(2)}<br>
    ${item.category || "-"} | ${item.due_date || "-"}<br>
    <button onclick="updateReceivableStatus(${item.id})">Atualizar status</button>
    <button onclick="deleteReceivable(${item.id})">Excluir</button>`
  );
  renderList("payablesList", summary.payables || [], (item) =>
    `#${item.id} | ${item.status} | R$ ${Number(item.amount).toFixed(2)}<br>
    ${item.category || "-"} | ${item.due_date || "-"}<br>
    <button onclick="updatePayableStatus(${item.id})">Atualizar status</button>
    <button onclick="deletePayable(${item.id})">Excluir</button>`
  );
  renderList("messagesList", summary.messages || [], (item) =>
    `#${item.id} | ${item.direction} | ${item.status}<br>${item.body}<br>
    <button onclick="updateMessageStatus(${item.id})">Atualizar status</button>`
  );
  const docsMeta = document.getElementById("documentsMeta");
  if (docsMeta) {
    docsMeta.textContent = `Docs: pagina ${summary.documents_page}/${Math.max(1, Math.ceil((summary.documents_total || 0) / Math.max(summary.documents_page_size || 1, 1)))}, total ${summary.documents_total || 0}`;
  }
  const proposalsMeta = document.getElementById("proposalsMeta");
  if (proposalsMeta) {
    proposalsMeta.textContent = `Propostas: ${summary.proposals?.length || 0}`;
  }
  const contractsMeta = document.getElementById("contractsMeta");
  if (contractsMeta) {
    contractsMeta.textContent = `Contratos: ${summary.contracts?.length || 0}`;
  }
  const leadsMeta = document.getElementById("leadsMeta");
  if (leadsMeta) {
    leadsMeta.textContent = `Leads: pagina ${summary.leads_page || 1}/${Math.max(1, Math.ceil((summary.leads_total || 0) / Math.max(summary.leads_page_size || 1, 1)))}, total ${summary.leads_total || 0}`;
  }
  const clientsMeta = document.getElementById("clientsMeta");
  if (clientsMeta) {
    clientsMeta.textContent = `Clients: pagina ${summary.clients_page || 1}/${Math.max(1, Math.ceil((summary.clients_total || 0) / Math.max(summary.clients_page_size || 1, 1)))}, total ${summary.clients_total || 0}`;
  }
  const messagesMeta = document.getElementById("messagesMeta");
  if (messagesMeta) {
    messagesMeta.textContent = `Msgs: pagina ${summary.messages_page}/${Math.max(1, Math.ceil((summary.messages_total || 0) / Math.max(summary.messages_page_size || 1, 1)))}, total ${summary.messages_total || 0}`;
  }
  const financeMeta = document.getElementById("financeMeta");
  if (financeMeta) {
    financeMeta.textContent = `AR total: R$ ${Number(summary.finance?.receivable_total || 0).toFixed(2)} | AR pendente: R$ ${Number(summary.finance?.receivable_pending || 0).toFixed(2)} | AP total: R$ ${Number(summary.finance?.payable_total || 0).toFixed(2)} | AP pendente: R$ ${Number(summary.finance?.payable_pending || 0).toFixed(2)}`;
  }
}
