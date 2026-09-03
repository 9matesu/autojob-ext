(() => {
  const BACKEND = "http://127.0.0.1:8322";

  const KEYWORDS =
    /(requisitos|responsabilidades|experi[eê]ncia|compet[eê]ncias|benef[ií]cios|sal[aá]rio|contrata|vaga|obrigat[oó]ri|desej[aá]vel|requirements|responsibilities|qualifications|benefits|seniority|years of experience|apply now|full[- ]time|part[- ]time)/gi;

  const scoreCache = new WeakMap();
  function score(el) {
    if (scoreCache.has(el)) return scoreCache.get(el);
    const text = el.innerText || "";
    const len = text.length;
    let s = 0;
    if (len >= 400) {
      const hits = (text.match(KEYWORDS) || []).length;
      s = Math.min(len, 20000) + hits * 800;
    }
    scoreCache.set(el, s);
    return s;
  }

  function collectCandidates() {
    const sel =
      'article, main, [role="main"], section, div[class*="job"], div[class*="description"], div[class*="apply"], div[class*="content"]';
    const list = [];
    for (const el of document.querySelectorAll(sel)) {
      if (score(el) > 0) list.push(el);
    }
    if (!list.length && document.body) {
      for (const el of document.body.children) {
        if (el instanceof HTMLElement && score(el) > 0) list.push(el);
      }
    }
    list.sort((a, b) => score(b) - score(a));
    return list.slice(0, 40);
  }

  function bestOf(cands) {
    let best = cands[0] || null;
    if (!best) return null;
    const ref = score(best);
    for (const el of cands) {
      if (el === best || !best.contains(el)) continue;
      if (score(el) >= ref * 0.85) best = el;
    }
    return best;
  }

  let state = null;

  function positionOverlay() {
    const { hovered, overlay } = state;
    if (!hovered || !document.contains(hovered)) {
      overlay.style.display = "none";
      return;
    }
    const r = hovered.getBoundingClientRect();
    overlay.style.display = "block";
    overlay.style.left = r.left + "px";
    overlay.style.top = r.top + "px";
    overlay.style.width = r.width + "px";
    overlay.style.height = r.height + "px";
  }

  function loop() {
    if (!state) return;
    positionOverlay();
    state.raf = requestAnimationFrame(loop);
  }

  function onMouseMove(e) {
    if (!state) return;
    const el = document.elementFromPoint(e.clientX, e.clientY);
    if (!el) return;
    let cur = el;
    while (cur && !state.set.has(cur)) cur = cur.parentElement;
    if (cur) state.hovered = cur;
  }

  function onClick(e) {
    if (!state) return;
    e.preventDefault();
    e.stopPropagation();
    const target = state.hovered;
    if (!target) cancel("Nenhum painel sob o cursor.");
    else finish(target);
  }

  function onKey(e) {
    if (e.key === "Escape" && state) {
      e.preventDefault();
      e.stopPropagation();
      cancel(null);
    }
  }

  function cleanup() {
    if (!state) return;
    cancelAnimationFrame(state.raf);
    document.removeEventListener("mousemove", onMouseMove, true);
    document.removeEventListener("click", onClick, true);
    document.removeEventListener("keydown", onKey, true);
    state.overlay.remove();
    document.documentElement.style.cursor = state.prevCursor;
    state = null;
  }

  function cancel(errMsg) {
    cleanup();
    report(errMsg ? { ok: false, error: errMsg } : { ok: false, cancelled: true });
  }

  function report(payload) {
    try {
      chrome.runtime.sendMessage({ type: "autojob-capture-result", payload }).catch(() => {});
    } catch {}
  }

  async function finish(el) {
    cleanup();
    const text = (el.innerText || "").slice(0, 30000);
    if (text.trim().length < 80) {
      report({ ok: false, error: "O painel selecionado tem pouco texto para extrair." });
      return;
    }
    try {
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
        report({ ok: false, error: "Backend: " + detail });
        return;
      }
      report({ ok: true, result: await res.json() });
    } catch (err) {
      report({ ok: false, error: "Backend offline. Execute o motor local do AutoJob." });
    }
  }

  function startSelection(sendResponse) {
    if (state) {
      sendResponse({ ok: false, error: "Seleção já em andamento nesta página." });
      return;
    }
    const cands = collectCandidates();
    if (!cands.length) {
      sendResponse({ ok: false, error: "Nenhum painel de vaga detectado nesta página." });
      return;
    }
    sendResponse({ ok: true, mode: "selecting" });

    const overlay = document.createElement("div");
    overlay.style.cssText =
      "position:fixed;z-index:2147483647;left:0;top:0;border:3px solid #ffff00;" +
      "box-shadow:0 0 0 9999px rgba(0,0,0,0.35);pointer-events:none;display:none;";
    const label = document.createElement("div");
    label.textContent = "PAINEL DA VAGA — CLIQUE PARA CAPTURAR";
    label.style.cssText =
      'position:absolute;top:-26px;left:0;background:#ffff00;color:#000;border:1px solid #000;' +
      'font:bold 11px/1.4 "Space Mono",monospace;padding:2px 8px;letter-spacing:0.05em;white-space:nowrap;';
    overlay.appendChild(label);
    document.documentElement.appendChild(overlay);

    const prevCursor = document.documentElement.style.cursor;
    document.documentElement.style.cursor = "crosshair";

    state = {
      set: new Set(cands),
      hovered: bestOf(cands),
      overlay,
      prevCursor,
      raf: 0,
    };
    document.addEventListener("mousemove", onMouseMove, true);
    document.addEventListener("click", onClick, true);
    document.addEventListener("keydown", onKey, true);
    loop();
  }

  if (typeof chrome !== "undefined" && chrome.runtime && chrome.runtime.onMessage) {
    chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
      if (msg && msg.type === "autojob-capture-start") {
        startSelection(sendResponse);
      }
    });
  }
})();
