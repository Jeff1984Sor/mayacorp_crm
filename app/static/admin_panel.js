// Entry point kept small on purpose; panel logic now lives in:
// /static/admin_panel_shared.js
// /static/admin_panel_render.js
// /static/admin_panel_actions.js

window.addEventListener("DOMContentLoaded", () => {
  setPanelVisibility(false);
  switchPanelSection("home");
  switchWorkspaceFlowTab("account");
  window.fetch("/admin/panel/central/dashboard", { credentials: "same-origin" })
    .then(async (response) => {
      if (!response.ok) {
        return;
      }
      const text = await response.text();
      try {
        const parsed = JSON.parse(text);
        setPanelVisibility(true);
        output.textContent = JSON.stringify(parsed, null, 2);
        showToast(parsed.message || "Sessao central restaurada.", "success");
        switchPanelSection("home");
        loadCompanyAccounts().catch(() => {});
        loadWorkspaceSummary().catch(() => {});
      } catch (error) {}
    })
    .catch(() => {});
});
