const TOKEN_KEY = "safaridesk_access_token";
const REFRESH_KEY = "safaridesk_refresh_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY);
}

export function saveTokens(payload) {
  localStorage.setItem(TOKEN_KEY, payload.access_token);
  localStorage.setItem(REFRESH_KEY, payload.refresh_token);
}

export function clearTokens() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

let refreshPromise = null;

async function refreshAccessToken() {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  if (!refreshPromise) {
    refreshPromise = fetch("/api/v1/auth/refresh", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken })
    })
      .then(async (response) => {
        if (!response.ok) return false;
        const tokens = await response.json();
        saveTokens(tokens);
        return true;
      })
      .catch(() => false)
      .finally(() => {
        refreshPromise = null;
      });
  }

  return refreshPromise;
}

async function request(path, options = {}) {
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

  return { response, data };
}

export async function api(path, options = {}) {
  let { response, data } = await request(path, options);

  const mayRefresh =
    response.status === 401 &&
    path !== "/api/v1/auth/login" &&
    path !== "/api/v1/auth/token" &&
    path !== "/api/v1/auth/refresh" &&
    !options.skipAuthRefresh;

  if (mayRefresh && (await refreshAccessToken())) {
    ({ response, data } = await request(path, options));
  }

  if (!response.ok) {
    if (response.status === 401) clearTokens();
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
