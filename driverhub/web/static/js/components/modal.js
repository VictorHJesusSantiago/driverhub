/* driverhub: components/modal */
"use strict";

import { h, append, clear } from "../dom.js";

let backdrop = null;
let box = null;
let onKey = null;

function ensure() {
  if (backdrop) return;
  backdrop = h("div", { class: "modal" });
  box = h("div", { class: "modal-box" });
  append(backdrop, box);
  document.body.appendChild(backdrop);
  backdrop.addEventListener("click", (e) => { if (e.target === backdrop) closeModal(); });
  onKey = (e) => { if (e.key === "Escape") closeModal(); };
  document.addEventListener("keydown", onKey);
}

export function openModal(opts = {}) {
  const { title = "Ação", body = "", actions = [] } = opts || {};
  ensure();
  clear(box);
  append(box, h("h3", { text: String(title) }));
  if (typeof body === "string") {
    append(box, h("p", { class: "pre", text: body }));
  } else if (body) {
    append(box, body);
  }
  const row = h("div", { class: "modal-actions" });
  const list = Array.isArray(actions) && actions.length ? actions : [{ label: "Fechar", class: "btn" }];
  list.forEach((a) => {
    const btn = h("button", { class: a.class || "btn", text: a.label || "OK" });
    btn.addEventListener("click", async () => {
      if (typeof a.onClick === "function") {
        btn.disabled = true;
        try {
          const result = await a.onClick();
          if (result === false) { btn.disabled = false; return; }
          closeModal();
        } catch (err) {
          console.error("modal action", err);
          btn.disabled = false;
        }
      } else {
        closeModal();
      }
    });
    append(row, btn);
  });
  append(box, row);
  return { close: closeModal, el: backdrop };
}

export function closeModal() {
  if (backdrop) {
    clear(backdrop);
    backdrop.remove();
  }
  backdrop = null;
  box = null;
  if (onKey) {
    document.removeEventListener("keydown", onKey);
    onKey = null;
  }
}

export const Modal = { openModal, closeModal };

export default Modal;