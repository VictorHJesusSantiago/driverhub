/* driverhub: components/badge */
"use strict";

import { h } from "../dom.js";

const BADGE_CSS = [
  ".badge-ok,.badge-warn,.badge-error,.badge-info{display:inline-block;padding:3px 9px;border-radius:999px;font-size:11px;font-weight:700;}",
  ".badge-ok{background:rgba(47,208,132,.15);color:#2fd084;}",
  ".badge-warn{background:rgba(255,194,75,.15);color:#ffc24b;}",
  ".badge-error{background:rgba(255,92,108,.15);color:#ff5c6c;}",
  ".badge-info{background:rgba(63,155,255,.15);color:#6fc3ff;}",
].join("\n");

let injected = false;

function ensureCss() {
  if (injected) return;
  injected = true;
  document.head.appendChild(h("style", { id: "dh-badge-css", text: BADGE_CSS }));
}

export function badge(text, tone = "info") {
  ensureCss();
  const allowed = ["ok", "warn", "error", "info"];
  const t = allowed.includes(String(tone)) ? tone : "info";
  return h("span", {
    class: "badge-" + t,
    text: text === undefined || text === null ? "" : String(text),
  });
}

export default badge;