var chrome = { runtime: { sendMessage: function(m){ window.__reports.push(m.payload); return Promise.resolve(); } } };
window.fetch = function(url, opts) { window.__posts.push(JSON.parse(opts.body)); return Promise.resolve({ ok: true, json: async function(){ return { fake: true }; } }); };
(() => {
  const BACKEND = "http://127.0.0.1:8322";
  const HOST = (location.hostname || "").toLowerCase();

  const KEYWORDS =
    /(requisitos|responsabilidades|experi[eê]ncia|compet[eê]ncias|benef[ií]cios|sal[aá]rio|contrata|vaga|obrigat[oó]ri|desej[aá]vel|requirements|responsibilities|qualifications|benefits|seniority|years of experience|apply now|full[- ]time|part[- ]time)/gi;

  // Site-specific job-panel roots, tried before the generic heuristics.
  // Gupy usa classes hash instáveis -> cai no genérico (documentado).
  const SITE_ROOTS = [
    { host: /(^|\.)linkedin\.com$/i, sels: [".jobs-description__content", "#job-details"] },
    { host: /(^|\.)indeed\./i, sels: ["#jobDescriptionText"] },
    { host: /boards\.greenhouse\.io$/i, sels: ["#content"] },
    { host: /(^|\.)lever\.co$/i, sels: ["div.content"] },
  ];

  const NOISE_SEL =
    "nav, header, footer, aside, form, script, style, noscript, iframe, object, " +
    "embed, select, input, textarea, video, audio, " +
    '[role="navigation"], [role="banner"], [role="contentinfo"], ' +
    '[role="complementary"], [role="search"], [role="dialog"], [aria-hidden="true"]';

  const NOISE_CLASS =
    /cookie|consent|lgpd|banner|ad[-_]|ads\b|promo|course|curso|related|relacionad|recommend|recomend|similar|suggest|rail|sidebar|aside|menu|share|social|comment|signup|sign-up|signin|login|newsletter|subscribe|overlay|modal|popup|tooltip|toast|breadcrumb|pagination|skip/i;

  function isNoiseNode(n) {
    if (!(n instanceof HTMLElement)) return false;
    if (n.hasAttribute("data-autojob")) return true;
    const s = (typeof n.className === "string" ? n.className : "") + " " + (n.id || "");
    return NOISE_CLASS.test(s);
  }

  function pruneNoise(root) {
    const clone = root.cloneNode(true);
    clone.querySelectorAll(NOISE_SEL).forEach((n) => n.remove());
    clone.querySelectorAll("[class], [id]").forEach((n) => {
      if (isNoiseNode(n)) n.remove();
    });
    return clone;
  }

  function cleanText(el) {
    const t = (pruneNoise(el).innerText || "").replace(/\s+/g, " ").trim();
    return t;
  }

  function countHits(text) {
    return (text.match(KEYWORDS) || []).length;
  }

  const scoreCache = new WeakMap();
  function scoreInfo(el) {
    if (scoreCache.has(el)) return scoreCache.get(el);
    const raw = el.innerText || "";
    const words = (raw.match(/\S+/g) || []).length;
    let info = { len: 0, hits: 0, density: 0, noise: false, cleanLen: 0, cleanHits: 0 };
    if (raw.length >= 400) {
      const hits = countHits(raw);
      const noise = !!el.querySelector(
        'nav, header, footer, aside, [role="navigation"], [role="banner"], ' +
          '[role="contentinfo"], [role="complementary"]'
      );
      const cleaned = cleanText(el);
      info = {
        len: raw.length,
        hits,
        density: hits / Math.max(1, words),
        noise,
        cleanLen: cleaned.length,
        cleanHits: countHits(cleaned),
      };
    }
    scoreCache.set(el, info);
    return info;
  }

  function composite(info) {
    return Math.min(info.len, 20000) + info.hits * 800 - (info.noise ? 4000 : 0);
  }

  function pushUnique(list, seen, el) {
    if (el instanceof HTMLElement && !seen.has(el)) {
      seen.add(el);
      list.push(el);
    }
  }

  function collectCandidates() {
    const list = [];
    const seen = new Set();
    // 1. Raízes específicas do ATS (barra mais baixa: precisão alta).
    for (const site of SITE_ROOTS) {
      if (!site.host.test(HOST)) continue;
      for (const sel of site.sels) {
        const el = document.querySelector(sel);
        if (el instanceof HTMLElement && cleanText(el).length >= 150) {
          pushUnique(list, seen, el);
        }
      }
    }
    // 2. Heurística genérica.
    const sel =
      'article, main, [role="main"], section, div[class*="job"], div[class*="description"], ' +
      'div[class*="apply"], div[class*="content"], div[id*="Description"], div[id*="job-details"], ' +
      'div[id*="jobDetails"], div[id*="job-body"]';
    for (const el of document.querySelectorAll(sel)) {
      if (scoreInfo(el).len > 0) pushUnique(list, seen, el);
    }
    if (!list.length && document.body) {
      for (const el of document.body.children) {
        if (el instanceof HTMLElement && scoreInfo(el).len > 0) pushUnique(list, seen, el);
      }
    }
    list.sort((a, b) => composite(scoreInfo(b)) - composite(scoreInfo(a)));
    return list.slice(0, 40);
  }

  // Menor candidato contendo o ponto cujo texto limpo seja substancial,
  // expandido para cima a fim de incluir cabeçalhos (h1/h2) irmãos —
  // sem ultrapassar 1.6x do tamanho base (anti-balão).
  function expandToHeaded(el) {
    const baseLen = Math.max(1, scoreInfo(el).cleanLen);
    let cur = el;
    let p = el.parentElement;
    while (p && p !== document.body && p instanceof HTMLElement) {
      const h = p.querySelector(":scope > h1, :scope > h2");
      if (h && h.textContent.trim().length <= 150) {
        const info = scoreInfo(p);
        if (info.cleanLen >= 150 && info.cleanLen <= baseLen * 1.6) {
          cur = p;
        }
      }
      p = p.parentElement;
    }
    return cur;
  }

  function refineToPanel(cands, scope) {
    let best = null;
    let bestScore = -1;
    for (const el of cands) {
      if (!scope.contains(el)) continue;
      const info = scoreInfo(el);
      if (info.cleanLen < 150) continue;
      const s = info.cleanHits * 1000 + Math.min(info.cleanLen, 20000) - el.querySelectorAll("*").length;
      if (s > bestScore) {
        bestScore = s;
        best = el;
      }
    }
    if (!best) return null;
    return expandToHeaded(best);
  }

  function bestOf(cands) {
    const top = cands[0] || null;
    if (!top) return null;
    return refineToPanel(cands, top) || top;
  }

  function fmtCount(n) {
    return n >= 1000 ? (n / 1000).toFixed(1).replace(".", ",").replace(",0", "") + "k" : String(n);
  }

  let state = null;

  function labelFor(el) {
    const info = el ? scoreInfo(el) : null;
    const n = info ? info.cleanLen : 0;
    const h = info ? info.cleanHits : 0;
    return "PAINEL DA VAGA · ~" + fmtCount(n) + " chars · " + h + " termos — CLIQUE PARA PRÉVIA";
  }

  function positionOverlay() {
    const { hovered, overlay, label } = state;
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
    label.textContent = labelFor(hovered);
  }

  function loop() {
    if (!state || state.mode !== "select") return;
    positionOverlay();
    state.raf = requestAnimationFrame(loop);
  }

  function onMouseMove(e) {
    if (!state || state.mode !== "select") return;
    const el = document.elementFromPoint(e.clientX, e.clientY);
    if (!el) return;
    let cur = el;
    while (cur && !state.set.has(cur)) cur = cur.parentElement;
    if (!cur) return;
    const refined = refineToPanel(state.cands, cur) || cur;
    if (refined !== state.hovered) {
      state.hovered = refined;
      positionOverlay();
    }
  }

  function showToast(target) {
    const info = scoreInfo(target);
    const text = cleanText(target);
    const lines = text
      .split(/(?<=[.!?])\s+|\n+/)
      .map((l) => l.trim())
      .filter(Boolean)
      .slice(0, 6);
    const preview = lines.join("\n").slice(0, 600);

    const toast = document.createElement("div");
    toast.setAttribute("data-autojob", "toast");
    toast.style.cssText =
      "position:fixed;z-index:2147483647;left:50%;transform:translateX(-50%);bottom:16px;" +
      "max-width:min(640px,92vw);background:#ffff00;color:#000;border:2px solid #000;" +
      "box-shadow:6px 6px 0px 0px #000000;pointer-events:none;" +
      'font-family:"Space Mono",monospace;';
    const head = document.createElement("div");
    head.style.cssText =
      "display:flex;align-items:center;gap:8px;padding:6px 10px;border-bottom:2px solid #000;" +
      "font-size:11px;font-weight:bold;text-transform:uppercase;letter-spacing:0.05em;";
    const tag = document.createElement("span");
    tag.textContent = "PRÉVIA DA CAPTURA";
    tag.style.cssText = "background:#000;color:#ffff00;padding:2px 8px;font-size:10px;";
    const meta = document.createElement("span");
    meta.textContent =
      "· ~" + fmtCount(text.length) + " chars · " + info.cleanHits + " termos";
    const spacer = document.createElement("span");
    spacer.style.cssText = "flex:1;";
    const btnCapture = document.createElement("button");
    btnCapture.textContent = "CAPTURAR";
    btnCapture.style.cssText =
      "background:#000;color:#ffff00;border:2px solid #000;font:bold 11px monospace;" +
      "padding:4px 12px;cursor:pointer;pointer-events:auto;";
    const btnOther = document.createElement("button");
    btnOther.textContent = "ESCOLHER OUTRO";
    btnOther.style.cssText =
      "background:#fff;color:#000;border:2px solid #000;font:bold 11px monospace;" +
      "padding:4px 12px;cursor:pointer;pointer-events:auto;";
    const pre = document.createElement("pre");
    pre.textContent = preview;
    pre.style.cssText =
      "margin:0;padding:8px 10px;font-size:11px;line-height:1.5;white-space:pre-wrap;" +
      "max-height:150px;overflow:hidden;";
    head.append(tag, meta, spacer, btnOther, btnCapture);
    toast.append(head, pre);
    document.documentElement.appendChild(toast);

    btnCapture.addEventListener("click", (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
      finish(target, text);
    });
    btnOther.addEventListener("click", (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
      backToSelection();
    });
    state.toast = toast;
    state.pending = { el: target, text };
  }

  function hideToast() {
    if (state && state.toast) {
      state.toast.remove();
      state.toast = null;
      state.pending = null;
    }
  }

  function backToSelection() {
    if (!state) return;
    hideToast();
    state.mode = "select";
    document.documentElement.style.cursor = "crosshair";
    loop();
  }

  function onClick(e) {
    if (!state || state.mode !== "select") return;
    e.preventDefault();
    e.stopPropagation();
    const target = state.hovered;
    if (!target) {
      cancel("Nenhum painel sob o cursor.");
      return;
    }
    state.mode = "confirm";
    document.documentElement.style.cursor = "";
    showToast(target);
  }

  function onKey(e) {
    if (!state) return;
    if (e.key === "Escape") {
      e.preventDefault();
      e.stopPropagation();
      if (state.mode === "confirm") backToSelection();
      else cancel(null);
    } else if (e.key === "Enter" && state.mode === "confirm" && state.pending) {
      e.preventDefault();
      e.stopPropagation();
      finish(state.pending.el, state.pending.text);
    }
  }

  function cleanup() {
    if (!state) return;
    cancelAnimationFrame(state.raf);
    document.removeEventListener("mousemove", onMouseMove, true);
    document.removeEventListener("click", onClick, true);
    document.removeEventListener("keydown", onKey, true);
    state.overlay.remove();
    if (state.toast) state.toast.remove();
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

  async function finish(el, text) {
    const body = text !== undefined ? text : cleanText(el);
    cleanup();
    if (body.trim().length < 80) {
      report({ ok: false, error: "O painel selecionado tem pouco texto para extrair." });
      return;
    }
    try {
      const res = await fetch(BACKEND + "/api/adapt-text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_text: body.slice(0, 30000),
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
    overlay.setAttribute("data-autojob", "overlay");
    overlay.style.cssText =
      "position:fixed;z-index:2147483646;left:0;top:0;border:3px solid #ffff00;" +
      "box-shadow:0 0 0 9999px rgba(0,0,0,0.35);pointer-events:none;display:none;";
    const label = document.createElement("div");
    label.style.cssText =
      'position:absolute;top:-26px;left:0;background:#ffff00;color:#000;border:1px solid #000;' +
      'font:bold 11px/1.4 "Space Mono",monospace;padding:2px 8px;letter-spacing:0.05em;white-space:nowrap;';
    overlay.appendChild(label);
    document.documentElement.appendChild(overlay);

    const prevCursor = document.documentElement.style.cursor;
    document.documentElement.style.cursor = "crosshair";

    state = {
      mode: "select",
      cands,
      set: new Set(cands),
      hovered: bestOf(cands),
      overlay,
      label,
      toast: null,
      pending: null,
      prevCursor,
      raf: 0,
    };
    document.addEventListener("mousemove", onMouseMove, true);
    document.addEventListener("click", onClick, true);
    document.addEventListener("keydown", onKey, true);
    loop();
  }
window.__start = startSelection;
})();
