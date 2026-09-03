(() => {
  const BACKEND = "http://127.0.0.1:8322";

  const KEYWORDS =
    /(requisitos|responsabilidades|experi[eê]ncia|compet[eê]ncias|benef[ií]cios|sal[aá]rio|contrata|vaga|obrigat[oó]ri|desej[aá]vel|requirements|responsibilities|qualifications|benefits|seniority|years of experience|apply now|full[- ]time|part[- ]time)/gi;

  function score(el) {
    const text = el.innerText || "";
    const len = text.length;
    if (len < 400) return 0;
    const hits = (text.match(KEYWORDS) || []).length;
    return Math.min(len, 20000) + hits * 800;
  }

  function detectPanel() {
    const candidates = document.querySelectorAll(
      'article, main, [role="main"], section, div[class*="job"], div[class*="description"], div[class*="apply"], div[class*="content"]'
    );
    let best = null;
    let bestScore = 0;
    for (const el of candidates) {
      const s = score(el);
      if (s >= bestScore) {
        bestScore = s;
        best = el;
      }
    }
    if (!best && document.body) {
      let max = 0;
      for (const el of document.body.children) {
        if (!(el instanceof HTMLElement)) continue;
        const s = score(el);
        if (s > max) {
          max = s;
          best = el;
        }
      }
    }
    if (best) {
      // Prefer the deepest candidate holding nearly all of the best score
      // (e.g. the <article> panel inside a <main> wrapper).
      const ref = bestScore;
      for (const el of candidates) {
        if (el === best || !best.contains(el)) continue;
        if (score(el) >= ref * 0.85) best = el;
      }
    }
    return best;
  }

  function highlight(el) {
    const rect = el.getBoundingClientRect();
    const box = document.createElement("div");
    box.style.cssText =
      "position:fixed;z-index:2147483647;left:" +
      rect.left + "px;top:" + rect.top +
      "px;width:" + rect.width + "px;height:" + rect.height +
      "px;border:3px solid #ffff00;box-shadow:0 0 0 9999px rgba(0,0,0,0.35);pointer-events:none;";
    const tag = document.createElement("div");
    tag.textContent = "PAINEL DA VAGA";
    tag.style.cssText =
      'position:absolute;top:-24px;left:0;background:#ffff00;color:#000;border:1px solid #000;' +
      'font:bold 11px/1.4 "Space Mono",monospace;padding:2px 8px;letter-spacing:0.05em;';
    box.appendChild(tag);
    document.documentElement.appendChild(box);
    setTimeout(() => box.remove(), 900);
  }

  async function capture() {
    const panel = detectPanel();
    if (!panel) throw new Error("Nenhum painel de vaga identificado nesta pagina.");
    highlight(panel);
    const text = (panel.innerText || "").slice(0, 30000);
    if (text.trim().length < 80) throw new Error("Painel identificado tem pouco texto para extrair.");
    const res = await fetch(BACKEND + "/api/adapt-text", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        job_text: text,
        page_title: document.title,
        page_url: location.href,
      }),
    });
    if (!res.ok) {
      let detail = String(res.status);
      try {
        detail = (await res.json()).detail || detail;
      } catch {}
      throw new Error("Backend: " + detail);
    }
    return await res.json();
  }

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg && msg.type === "autojob-capture") {
      capture().then(
        (result) => sendResponse({ ok: true, result }),
        (err) => sendResponse({ ok: false, error: String(err && err.message ? err.message : err) })
      );
      return true;
    }
  });
})();
