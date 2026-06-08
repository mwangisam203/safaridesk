const TOKEN_KEY = "safaridesk_access_token";
const REFRESH_KEY = "safaridesk_refresh_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function saveTokens(payload) {
  localStorage.setItem(TOKEN_KEY, payload.access_token);
  localStorage.setItem(REFRESH_KEY, payload.refresh_token);
}

export function clearTokens() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export async function api(path, options = {}) {
  const token = getToken();
  const headers = new Headers(options.headers || {});

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(path, { credentials: "include", ...options, headers });
  const data = response.status === 204 ? null : await response.json().catch(() => null);

  if (!response.ok) {
    const error = new Error(
      typeof data?.detail === "string"
        ? data.detail
        : data?.detail?.message || "Something went wrong."
    );
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return data;
}
