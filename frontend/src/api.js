const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function getToken() {
  return localStorage.getItem("token");
}

export function setToken(t) {
  if (t) {
    localStorage.setItem("token", t);
  } else {
    localStorage.removeItem("token");
  }
}

export function clearAuth() {
  localStorage.removeItem("token");
  localStorage.removeItem("session");
  localStorage.removeItem("org");
}

export function getStoredSession() {
  try {
    const s = localStorage.getItem("session");
    return s ? JSON.parse(s) : null;
  } catch {
    return null;
  }
}

export function setStoredSession(s) {
  if (s) {
    localStorage.setItem("session", JSON.stringify(s));
  } else {
    localStorage.removeItem("session");
  }
}

export function getStoredOrg() {
  try {
    const o = localStorage.getItem("org");
    return o ? JSON.parse(o) : null;
  } catch {
    return null;
  }
}

export function setStoredOrg(o) {
  if (o) {
    localStorage.setItem("org", JSON.stringify(o));
  } else {
    localStorage.removeItem("org");
  }
}

export async function api(path, options = {}) {
  const res = await fetch(BASE + path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}),
      ...(options.headers || {}),
    },
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Request failed");
  return data;
}
