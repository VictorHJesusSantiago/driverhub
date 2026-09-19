/* driverhub: components/spinner */
"use strict";

import { h } from "../dom.js";

export function spinner(label = "") {
  const s = h("div", { class: "spinner" });
  if (!label) return s;
  return h("div", { style: { display: "flex", flexDirection: "column", alignItems: "center", gap: "12px", padding: "20px 0" } }, [
    s,
    h("span", { class: "hint", text: String(label) }),
  ]);
}

export function show(el) {
  if (el) el.classList.remove("hidden");
  return el;
}

export function hide(el) {
  if (el) el.classList.add("hidden");
  return el;
}

export async function withSpinner(fn) {
  const overlay = h("div", { class: "busy" }, [
    h("div", { class: "spinner" }),
    h("span", { text: "Processando..." }),
  ]);
  document.body.appendChild(overlay);
  try {
    return await fn();
  } finally {
    overlay.remove();
  }
}

export default { spinner, show, hide, withSpinner };