"""Builds content_shim.js next to each fixture in fixtures/.

The shim is the real extension/content.js with test seams:
- a chrome stub recording runtime messages (no real extension context),
- a fetch stub recording POST bodies instead of calling the backend,
- window.__start exposed (the file's own chrome-listener is skipped).

Usage:
    python extension/test/build_shim.py

Then open a fixture in Chromium/Orca and drive it from devtools, e.g.:
    __reports=[];__posts=[];__ack=null;
    __start(r=>__ack=r)
    // mousemove/click, toast buttons, Enter/Escape
"""
from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTENT = HERE.parent / "content.js"
FIXTURES = HERE / "fixtures"

STUB = (
    "var chrome = { runtime: { sendMessage: function(m){ window.__reports.push(m.payload);"
    " return Promise.resolve(); } } };\n"
    "window.fetch = function(url, opts) { window.__posts.push(JSON.parse(opts.body));"
    " return Promise.resolve({ ok: true, json: async function(){ return { fake: true }; } }); };\n"
)

TAIL_MARKER = "if (typeof chrome"


def build() -> Path:
    src = CONTENT.read_text(encoding="utf-8")
    tail_idx = src.index(TAIL_MARKER)
    body = src[:tail_idx].rstrip()
    assert body.endswith("}"), "unexpected content.js tail"
    shim = STUB + body + "\nwindow.__start = startSelection;\n})();\n"
    out = FIXTURES / "content_shim.js"
    out.write_text(shim, encoding="utf-8")
    return out


if __name__ == "__main__":
    print("shim ->", build())
