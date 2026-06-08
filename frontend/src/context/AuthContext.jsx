import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api, clearTokens, getToken, saveTokens } from "../lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [subscription, setSubscription] = useState(null);
  const [loading, setLoading] = useState(Boolean(getToken()));

  async function refreshUser() {
    if (!getToken()) {
      setUser(null);
      setSubscription(null);
      setLoading(false);
      return;
    }

    try {
      const [profile, status] = await Promise.all([
        api("/api/v1/auth/me"),
        api("/api/v1/users/me/subscription")
      ]);
      setUser(profile);
      setSubscription(status);
    } catch {
      clearTokens();
      setUser(null);
      setSubscription(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refreshUser();
  }, []);

  async function login(credentials) {
    const tokens = await api("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(credentials)
    });
    saveTokens(tokens);
    await refreshUser();
  }

  async function register(payload) {
    await api("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    await login({ email: payload.email, password: payload.password });
  }

  function logout() {
    clearTokens();
    setUser(null);
    setSubscription(null);
  }

  const value = useMemo(
    () => ({
      user,
      subscription,
      loading,
      login,
      register,
      logout,
      refreshUser
    }),
    [user, subscription, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
