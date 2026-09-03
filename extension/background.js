chrome.sidePanel
  .setPanelBehavior({ openPanelOnActionClick: true })
  .catch(() => {});

chrome.commands.onCommand.addListener(async (command) => {
  if (command !== "capture") return;
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) return;
  try {
    const res = await chrome.tabs.sendMessage(tab.id, { type: "autojob-capture" });
    chrome.runtime
      .sendMessage({ type: "autojob-capture-result", payload: res })
      .catch(() => {});
  } catch (err) {
    chrome.runtime
      .sendMessage({
        type: "autojob-capture-result",
        payload: { ok: false, error: String(err?.message || err) },
      })
      .catch(() => {});
  }
});
