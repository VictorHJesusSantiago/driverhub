/* driverhub: dom */
"use strict";

export function h(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === undefined || v === null || v === false) continue;
    if (k === "class") node.className = v === true ? "" : String(v);
    else if (k === "text") node.textContent = v;
    else if (k === "html") node.innerHTML = v;
    else if (k === "style" && typeof v === "object") Object.assign(node.style, v);
    else if (k === "dataset" && typeof v === "object") Object.assign(node.dataset, v);
    else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2).toLowerCase(), v);
    else node.setAttribute(k, v === true ? "" : String(v));
  }
  if (children !== undefined && children !== null) append(node, children);
  return node;
}

export function el(id) {
  return document.getElementById(String(id || ""));
}

export function clear(node) {
  if (!node) return node;
  while (node.firstChild) node.removeChild(node.firstChild);
  return node;
}

export function append(parent, ...nodes) {
  if (!parent) return parent;
  for (const item of nodes) {
    if (item === undefined || item === null) continue;
    if (Array.isArray(item)) { append(parent, ...item); continue; }
    if (typeof item === "string" || typeof item === "number" || typeof item === "boolean") {
      parent.appendChild(document.createTextNode(String(item)));
    } else if (item instanceof Node) {
      parent.appendChild(item);
    } else if (typeof item === "object" && typeof item.html === "string") {
      parent.insertAdjacentHTML("beforeend", item.html);
    }
  }
  return parent;
}

export function on(el, ev, fn, opts) {
  if (el) el.addEventListener(ev, fn, opts);
  return el;
}

export default { h, el, clear, append, on };