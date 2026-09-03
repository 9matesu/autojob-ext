// Service worker: side panel behavior + capture shortcut.
// Toda a avaliacao roda dentro de try/catch: nada aqui pode lancar no
// registro do SW (falha de registro = extensao inutilizavel).
try {
  if (chrome.sidePanel && chrome.sidePanel.setPanelBehavior) {
    chrome.sidePanel
      .setPanelBehavior({ openPanelOnActionClick: true })
      .catch(() => {});
  }

  if (chrome.commands && chrome.commands.onCommand) {
    chrome.commands.onCommand.addListener(async (command) => {
      if (command !== "capture") return;
      try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (!tab?.id) return;
        const ack = await chrome.tabs.sendMessage(tab.id, { type: "autojob-capture-start" });
        if (ack && !ack.ok) {
          chrome.runtime
            .sendMessage({
              type: "autojob-capture-result",
              payload: { ok: false, error: ack.error || "Falha ao iniciar seleção." },
            })
            .catch(() => {});
        }
      } catch (err) {
        chrome.runtime
          .sendMessage({
            type: "autojob-capture-result",
            payload: { ok: false, error: "Recarregue a pagina da vaga (F5) e tente de novo." },
          })
          .catch(() => {});
      }
    });
  }
} catch (e) {
  console.error("AutoJob SW:", e);
}
