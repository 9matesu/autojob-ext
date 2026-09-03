try {
  if (chrome.sidePanel && chrome.sidePanel.setPanelBehavior) {
    chrome.sidePanel
      .setPanelBehavior({ openPanelOnActionClick: true })
      .catch(() => {});
  }
} catch {}


chrome.commands.onCommand.addListener(async (command) => {
  if (command !== "capture") return;
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) return;
  try {
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
