var chrome = { runtime: { sendMessage: function(m){ window.__reports.push(m.payload); return Promise.resolve(); } } };
window.fetch = function(url, opts) { window.__posts.push(JSON.parse(opts.body)); return Promise.resolve({ ok: true, json: async function(){ return { fake: true }; } }); };
(() => {
  const BACKEND = "http://127.0.0.1:8322";

  function fmtCount(n) {
    return n >= 1000 ? (n / 1000).toFixed(1).replace(".", ",").replace(",0", "") + "k" : String(n);
  }

  function isOurs(el) {
    return el instanceof HTMLElement && el.hasAttribute("data-resume");
  }

  // Breadcrumb real do elemento: body > main > article.job-posting
  function describe(el) {
    const parts = [];
    let cur = el;
    while (cur && cur !== document.documentElement && parts.length < 5) {
      if (cur instanceof HTMLElement && cur !== document.body) {
        let s = cur.tagName.toLowerCase();
        if (cur.id) s += "#" + cur.id;
        else if (typeof cur.className === "string" && cur.className.trim()) {
          s += "." + cur.className.trim().split(/\s+/)[0];
        }
        parts.unshift(s);
      }
      cur = cur.parentElement;
    }
    return "body > " + parts.join(" > ");
  }

  function textOf(el) {
    return ((el && el.innerText) || "").trim();
  }

  // Maior bloco de texto visível na viewport — ponto de partida dinâmico,
  // sem listas hardcoded. Só roda uma vez na entrada do modo.
  function largestVisibleBlock() {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
    let best = null;
    let bestLen = 0;
    let seen = 0;
    let node = walker.nextNode();
    while (node && seen < 2000) {
      seen++;
      if (!isOurs(node)) {
        const r = node.getBoundingClientRect();
        if (r.width > 40 && r.height > 40 && r.bottom > 0 && r.top < window.innerHeight) {
          const len = textOf(node).length;
          if (len > bestLen) {
            bestLen = len;
            best = node;
          }
        }
      }
      node = walker.nextNode();
    }
    return bestLen >= 80 ? best : null;
  }

  let state = null;

  function labelFor(el) {
    if (!el) return "SELECIONE O PAINEL · MOUSE DESTACA · ↑/↓ NAVEGA";
    return describe(el) + " · ~" + fmtCount(textOf(el).length) + " chars — CLIQUE P/ PRÉVIA";
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

  function pickTarget(x, y) {
    let el = document.elementFromPoint(x, y);
    while (el && (isOurs(el) || !(el instanceof HTMLElement))) {
      el = el.parentElement;
    }
    if (el === document.documentElement || el === document.body.parentElement) return null;
    return el;
  }

  function setCurrent(el) {
    if (!el || el === state.current) return;
    state.current = el;
    state.stack.push(el);
    state.hovered = el;
    positionOverlay();
  }

  function onMouseMove(e) {
    if (!state || state.mode !== "select") return;
    setCurrent(pickTarget(e.clientX, e.clientY));
  }

  function stepUp() {
    if (!state || !state.current) return;
    let p = state.current.parentElement;
    while (p && (isOurs(p) || !(p instanceof HTMLElement))) p = p.parentElement;
    if (p && p !== document.documentElement) setCurrent(p);
  }

  function stepDown() {
    if (!state || state.stack.length < 2) return;
    state.stack.pop();
    const el = state.stack[state.stack.length - 1];
    state.current = el;
    state.hovered = el;
    positionOverlay();
  }

  function showToast(target) {
    const text = textOf(target);

    const toast = document.createElement("div");
    toast.setAttribute("data-resume", "toast");
    toast.style.cssText =
      "position:fixed;z-index:2147483647;left:50%;transform:translateX(-50%);bottom:16px;" +
      "max-width:min(640px,92vw);background:#ffff00;color:#000;border:2px solid #000;" +
      "box-shadow:6px 6px 0px 0px #000000;pointer-events:none;" +
      "font-family:ui-sans-serif,system-ui,'Segoe UI',Helvetica,Arial,sans-serif;";
    const head = document.createElement("div");
    head.style.cssText =
      "display:flex;align-items:center;gap:8px;padding:6px 10px;border-bottom:2px solid #000;" +
      "font-size:11px;font-weight:bold;text-transform:uppercase;letter-spacing:0.05em;";
    const tag = document.createElement("span");
    tag.textContent = "PRÉVIA DA CAPTURA";
    tag.style.cssText = "background:#000;color:#ffff00;padding:2px 8px;font-size:10px;";
    const meta = document.createElement("span");
    meta.textContent = "· " + describe(target) + " · ~" + fmtCount(text.length) + " chars";
    const spacer = document.createElement("span");
    spacer.style.cssText = "flex:1;";
    const btnCapture = document.createElement("button");
    btnCapture.textContent = "CAPTURAR";
    btnCapture.style.cssText =
      "background:#000;color:#ffff00;border:2px solid #000;font:bold 11px ui-sans-serif,system-ui,'Segoe UI',Helvetica,Arial,sans-serif;" +
      "padding:4px 12px;cursor:pointer;pointer-events:auto;";
    const btnOther = document.createElement("button");
    btnOther.textContent = "ESCOLHER OUTRO";
    btnOther.style.cssText =
      "background:#fff;color:#000;border:2px solid #000;font:bold 11px ui-sans-serif,system-ui,'Segoe UI',Helvetica,Arial,sans-serif;" +
      "padding:4px 12px;cursor:pointer;pointer-events:auto;";
    const caption = document.createElement("div");
    caption.textContent = "EDITE O TEXTO SE PRECISAR · ENTER CAPTURA · ESC SAI";
    caption.style.cssText =
      "padding:4px 10px;font:bold 9px/1.4 ui-sans-serif,system-ui,'Segoe UI',Helvetica,Arial,sans-serif;" +
      "letter-spacing:0.06em;border-bottom:1px solid #000;";
    const ta = document.createElement("textarea");
    ta.value = text.slice(0, 4000);
    ta.spellcheck = false;
    ta.style.cssText =
      "display:block;width:100%;box-sizing:border-box;margin:0;border:0;" +
      "font:12px/1.5 ui-sans-serif,system-ui,'Segoe UI',Helvetica,Arial,sans-serif;" +
      "padding:8px 10px;max-height:160px;min-height:60px;resize:vertical;outline:none;" +
      "color:#000;background:#ffff00;";
    head.append(tag, meta, spacer, btnOther, btnCapture);
    toast.append(head, caption, ta);
    document.documentElement.appendChild(toast);

    btnCapture.addEventListener("click", (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
      finish(target, ta.value);
    });
    btnOther.addEventListener("click", (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
      backToSelection();
    });
    ta.addEventListener("keydown", (ev) => {
      // Dentro do textarea: Enter captura, Esc sai de tudo — sem engolir digitação.
      if (ev.key === "Enter" && !ev.shiftKey) {
        ev.preventDefault();
        ev.stopPropagation();
        finish(target, ta.value);
      } else if (ev.key === "Escape") {
        ev.preventDefault();
        ev.stopPropagation();
        cancel(null);
      }
    });
    state.toast = toast;
    state.pending = { el: target, get text() { return ta.value; } };
  }

  function hideToast() {
    if (state && state.toast) {
      state.toast.remove();
      state.toast = null;
      state.pending = null;
    }
  }

  function showHint() {
    const hint = document.createElement("div");
    hint.setAttribute("data-resume", "hint");
    hint.textContent = "MOUSE DESTACA · ↑/↓ NAVEGA · CLIQUE OU ENTER = PRÉVIA · ESC SAI DA CAPTURA";
    hint.style.cssText =
      "position:fixed;z-index:2147483647;top:12px;left:50%;transform:translateX(-50%);" +
      "background:#000;color:#ffff00;border:2px solid #ffff00;" +
      "font:bold 11px/1.4 ui-sans-serif,system-ui,'Segoe UI',Helvetica,Arial,sans-serif;padding:6px 12px;letter-spacing:0.05em;" +
      "white-space:nowrap;pointer-events:none;";
    document.documentElement.appendChild(hint);
    state.hint = hint;
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
    if (!target || !document.contains(target)) {
      cancel("Nenhum elemento sob o cursor.");
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
      // Um ESC sai da captura inteira, esteja em select ou confirm (spec resuMe 1.0).
      cancel(null);
    } else if (e.key === "Enter" && state.mode === "select" && state.hovered) {
      e.preventDefault();
      e.stopPropagation();
      state.mode = "confirm";
      document.documentElement.style.cursor = "";
      showToast(state.hovered);
    } else if (e.key === "Enter" && state.mode === "confirm" && state.pending) {
      e.preventDefault();
      e.stopPropagation();
      finish(state.pending.el, state.pending.text);
    } else if (e.key === "ArrowUp" && state.mode === "select") {
      e.preventDefault();
      e.stopPropagation();
      stepUp();
    } else if (e.key === "ArrowDown" && state.mode === "select") {
      e.preventDefault();
      e.stopPropagation();
      stepDown();
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
    if (state.hint) state.hint.remove();
    document.documentElement.style.cursor = state.prevCursor;
    state = null;
  }

  function cancel(errMsg) {
    cleanup();
    report(errMsg ? { ok: false, error: errMsg } : { ok: false, cancelled: true });
  }

  function report(payload) {
    try {
      chrome.runtime.sendMessage({ type: "resume-capture-result", payload }).catch(() => {});
    } catch {}
  }

  async function finish(el, text) {
    const body = (text !== undefined ? text : textOf(el)).trim();
    cleanup();
    if (body.length < 80) {
      report({ ok: false, error: "O texto editado tem pouco conteúdo para extrair." });
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
      report({ ok: false, error: "Backend offline. Execute o motor local do resuMe." });
    }
  }

  function startSelection(sendResponse) {
    if (state) {
      sendResponse({ ok: false, error: "Seleção já em andamento nesta página." });
      return;
    }
    sendResponse({ ok: true, mode: "selecting" });

    const overlay = document.createElement("div");
    overlay.setAttribute("data-resume", "overlay");
    overlay.style.cssText =
      "position:fixed;z-index:2147483646;left:0;top:0;border:3px solid #ffff00;" +
      "box-shadow:0 0 0 9999px rgba(0,0,0,0.35);pointer-events:none;display:none;";
    const label = document.createElement("div");
    label.style.cssText =
      'position:absolute;top:-26px;left:0;background:#ffff00;color:#000;border:1px solid #000;' +
      "font:bold 11px/1.4 ui-sans-serif,system-ui,'Segoe UI',Helvetica,Arial,sans-serif;padding:2px 8px;letter-spacing:0.05em;white-space:nowrap;";
    overlay.appendChild(label);
    document.documentElement.appendChild(overlay);

    const prevCursor = document.documentElement.style.cursor;
    document.documentElement.style.cursor = "crosshair";

    state = {
      mode: "select",
      current: null,
      stack: [],
      hovered: null,
      overlay,
      label,
      toast: null,
      hint: null,
      pending: null,
      prevCursor,
      raf: 0,
    };
    showHint();
    document.addEventListener("mousemove", onMouseMove, true);
    document.addEventListener("click", onClick, true);
    document.addEventListener("keydown", onKey, true);
    const first = largestVisibleBlock();
    if (first) setCurrent(first);
    loop();
  }

  function setCurrent(el) {
    if (!el || el === state.current) return;
    state.current = el;
    state.stack.push(el);
    state.hovered = el;
    positionOverlay();
  }
window.__start = startSelection;
})();
