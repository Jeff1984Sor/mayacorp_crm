function renderSummary(summary) {
  renderList("salesOrdersList", summary.sales_orders || [], (item) =>
    `#${item.id} | ${item.status} | R$ ${Number(item.total_amount).toFixed(2)}<br>
    <button onclick="updateSalesOrderStatus(${item.id})">Atualizar status</button>
    <button onclick="deleteSalesOrder(${item.id})">Excluir</button>`
  );
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
  const messagesMeta = document.getElementById("messagesMeta");
  if (messagesMeta) {
    messagesMeta.textContent = `Msgs: pagina ${summary.messages_page}/${Math.max(1, Math.ceil((summary.messages_total || 0) / Math.max(summary.messages_page_size || 1, 1)))}, total ${summary.messages_total || 0}`;
  }
}
