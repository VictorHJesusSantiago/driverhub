/* driverhub: api */
"use strict";

const DEFAULT_TIMEOUT = 15000;

export async function request(path, opts = {}) {
  const o = opts || {};
  const method = o.method || "GET";
  const timeout = o.timeout || DEFAULT_TIMEOUT;
  const headers = Object.assign({}, o.headers || {});
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);

  let url = String(path || "");
  if (o.confirm) url += (url.includes("?") ? "&" : "?") + "confirm=1";

  const init = { method, signal: controller.signal, headers };
  const body = o.body;
  if (body !== undefined && body !== null) {
    if (body instanceof FormData) {
      init.body = body;
    } else if (typeof body === "string" || o.raw) {
      init.body = body;
    } else {
      headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(body);
    }
  }

  try {
    const res = await fetch(url, init);
    const data = o.raw ? await res.text() : await res.json().catch(() => ({}));
    if (!res.ok) {
      return {
        ok: false,
        status: res.status,
        error: data.error || data.detail || "erro HTTP " + res.status,
        data,
      };
    }
    return { ok: true, status: res.status, error: null, data };
  } catch (err) {
    if (err && err.name === "AbortError") {
      return { ok: false, error: "tempo limite excedido (" + timeout + "ms)", status: 0, data: null };
    }
    return { ok: false, error: (err && err.message) || "falha de rede", status: 0, data: null };
  } finally {
    clearTimeout(timer);
  }
}

export function get(path, opts = {}) {
  return request(path, Object.assign({}, opts, { method: "GET" }));
}

export function post(path, body = {}, confirm = true, opts = {}) {
  return request(path, Object.assign({}, opts, { method: "POST", body, confirm: confirm !== false }));
}

export function api(url) {
  const u = String(url || "");
  if (/^[a-z][a-z0-9+.-]*:\/\//i.test(u)) return u;
  return u.startsWith("/") ? u : "/api/" + u;
}

export default { request, get, post, api };