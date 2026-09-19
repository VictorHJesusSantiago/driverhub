/* driverhub: components/table */
"use strict";

import { h, append, clear } from "../dom.js";

function cellFor(v, c) {
  const cls = (typeof c === "string" ? "" : c.cls) || "";
  if (v instanceof Node) {
    if (cls && v.classList) v.classList.add(cls);
    return v;
  }
  if (v && typeof v === "object") {
    if (v.html !== undefined) return h("td", { class: cls, html: v.html });
    const t = v.text === undefined || v.text === null ? "" : String(v.text);
    return h("td", { class: cls, text: t });
  }
  return h("td", { class: cls, text: v === undefined || v === null ? "" : String(v) });
}

export function dataTable(columns, rows = [], opts = {}) {
  const wrap = h("div", { class: "table-wrap" });
  const table = h("table");
  const thead = h("thead");
  const headRow = h("tr");
  columns.forEach((c, ci) => {
    const label = typeof c === "string" ? c : (c.label || c.key || "");
    const canSort = typeof c !== "string" && c.sort;
    const th = h("th", Object.assign(
      { text: label },
      canSort ? { "data-sort": "1", style: { cursor: "pointer" }, title: "Ordenar por " + label } : {}
    ));
    if (canSort) th._col = ci;
    append(headRow, th);
  });
  append(thead, headRow);
  const tbody = h("tbody");

  table._data = { columns: columns.slice(), rows: rows.slice(), opts: opts || {} };
  let emptyEl = null;

  function setTable(inWrap) {
    if (inWrap && table.parentNode !== wrap) wrap.insertBefore(table, wrap.firstChild);
    else if (!inWrap && table.parentNode === wrap) wrap.removeChild(table);
  }

  function redraw(src) {
    clear(tbody);
    if (emptyEl) { emptyEl.remove(); emptyEl = null; }
    const list = src && src.length ? src : [];
    if (!list.length) {
      setTable(false);
      emptyEl = h("div", { class: "empty", text: table._data.opts.empty || "Nenhum registro encontrado." });
      wrap.appendChild(emptyEl);
      return;
    }
    setTable(true);
    list.forEach((r, ri) => {
      const tr = h("tr");
      if (typeof table._data.opts.onRowClick === "function") {
        tr.style.cursor = "pointer";
        tr.addEventListener("click", () => {
          try { table._data.opts.onRowClick(r, ri); } catch (err) { console.error("row click", err); }
        });
      }
      for (let ci = 0; ci < columns.length; ci++) {
        const c = columns[ci];
        const v = Array.isArray(r) ? r[ci] : (typeof c === "string" ? r[c] : r[c.key || c.label]);
        append(tr, cellFor(v, c));
      }
      append(tbody, tr);
    });
  }

  table._redraw = redraw;
  append(table, thead, tbody);
  redraw(table._data.rows);
  if (thead.querySelector("[data-sort]")) sortable(thead);
  return wrap;
}

export function sortable(thead) {
  const table = thead.closest ? thead.closest("table") : null;
  if (!table || !table._redraw) return;

  function cellVal(row, index) {
    const c = table._data.columns[index];
    let v = Array.isArray(row)
      ? row[index]
      : row[typeof c === "string" ? c : (c ? c.key || c.label : index)];
    if (v && typeof v === "object") v = v.text !== undefined ? v.text : v.html;
    return v === undefined || v === null ? "" : String(v);
  }

  thead.querySelectorAll("th[data-sort]").forEach((th) => {
    let dir = 0;
    th.addEventListener("click", () => {
      dir = dir === 1 ? -1 : 1;
      const index = th._col;
      const rows = (table._data.rows || []).slice();
      rows.sort((a, b) => {
        const av = cellVal(a, index);
        const bv = cellVal(b, index);
        const an = Number(av);
        const bn = Number(bv);
        let cmp;
        if (Number.isFinite(an) && Number.isFinite(bn) && av.trim() !== "" && bv.trim() !== "") {
          cmp = an - bn;
        } else {
          cmp = String(av).localeCompare(String(bv), "pt-BR");
        }
        return cmp * dir;
      });
      table._redraw(rows);
    });
  });
}

export default { dataTable, sortable };