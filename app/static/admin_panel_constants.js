const PANEL_CONSTANTS = {
  orderStatuses: ["pending", "confirmed", "closed", "cancelled"],
  financeStatuses: ["pending", "paid", "overdue", "cancelled"],
  whatsappSessionStatuses: ["connecting", "connected", "disconnected", "failed"],
  messageStatuses: ["sending", "sent", "delivered", "read", "failed"],
  contractStatuses: ["draft", "sent", "signed", "cancelled"],
  cacheKeysByDomain: {
    summary: ["summary"],
    people: ["summary", "people", "leads", "clients"],
    orders: ["summary", "orders"],
    documents: ["summary", "documents", "proposals", "contracts"],
    finance: ["summary", "finance"],
    messages: ["summary", "messages"],
    outboundMessages: ["summary", "messages"],
    inboundMessages: ["summary", "messages"],
    whatsapp: ["summary", "messages"],
    all: ["summary", "people", "orders", "documents", "proposals", "contracts", "finance", "messages", "leads", "clients"]
  }
};
