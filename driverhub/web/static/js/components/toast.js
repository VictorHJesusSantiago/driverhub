/* driverhub: components/toast */
"use strict";

import { h, append } from "../dom.js";

const TOAST_CSS = [
  ".dh-toasts{position:fixed;top:16px;right:16px;z-index:400;display:flex;flex-direction:column;gap:10px;max-width:360px;}",
  ".dh-toast{background:#131e33;border:1px solid #3f9bff;color:#e7eefb;padding:12px 16px;border-radius:12px;box-shadow:0 8px 30px rgba(0,0,0,.35);font-size:14px;opacity:0;transform:translateY(-10px);transition:opacity .25s ease,transform .25s ease;cursor:pointer;}",
  ".dh-toast.show{opacity:1;transform:translateY(0);}",
  ".dh-toast.ok{border-color:#2fd084;}",
  ".dh-toast.warn{border-color:#ffc24b;}",
  ".dh-toast.error{border-color:#ff5c6c;}",
  ".dh-toast.info{border-color:#3f9bff;}",
].join("\n");

let container = null;
let styleInjected = false;

function ensure() {
  if (!styleInjected) {
    styleInjected = true;
    document.head.appendChild(h("style", { id: "dh-toast-css", text: TOAST_CSS }));
  }
  if (!container) {
    container = h("div", { class: "dh-toasts" });
    document.body.appendChild(container);
  }
  return container;
}

export function toast(msg, type = "ok") {
  const types = ["ok", "warn", "error", "info"];
  const t = types.includes(type) ? type : (type === "err" ? "error" : "info");
  const el = h("div", { class: "dh-toast " + t, text: String(msg === undefined || msg === null ? "" : msg) });
  el.addEventListener("click", () => dismiss(el));
  ensure().appendChild(el);
  requestAnimationFrame(() => el.classList.add("show"));
  setTimeout(() => dismiss(el), 6000);
  return el;
}

function dismiss(el) {
  if (!el || el.dataset.done) return;
  el.dataset.done = "1";
  el.classList.remove("show");
  setTimeout(() => el.remove(), 300);
}

export function dismissToasts() {
  if (!container) return;
  container.querySelectorAll(".dh-toast").forEach(dismiss);
}

export default { toast, dismissToasts };