import { createContext, useContext, useEffect, useState } from "react";

import { api } from "../api/client.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const normalizeUser = (rawUser) => {
    if (!rawUser) return null;

    const permissions = Array.isArray(rawUser.permissions)
      ? rawUser.permissions
      : typeof rawUser.permission_list === "string"
      ? rawUser.permission_list
          .split(",")
          .map((p) => p.trim())
          .filter(Boolean)
      : [];

    return {
      ...rawUser,
      permissions,
    };
  };

  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem("indcool_user");
    if (!raw) return null;
    try {
      const parsed = JSON.parse(raw);
      return normalizeUser(parsed);
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("indcool_token");
    if (token) {
       api.get("/api/auth/me")
         .then((r) => {
           const normalized = normalizeUser(r.data);
           setUser(normalized);
           localStorage.setItem("indcool_user", JSON.stringify(normalized));
        })
        .catch(() => {
          localStorage.removeItem("indcool_token");
          localStorage.removeItem("indcool_user");
          setUser(null);
        });
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function login(email, password) {
    setLoading(true);
    try {
       const { data } = await api.post("/api/auth/login", { email, password });

       const normalizedUser = normalizeUser(data.user);

      localStorage.setItem("indcool_token", data.access_token);
      localStorage.setItem("indcool_user", JSON.stringify(normalizedUser));
      setUser(normalizedUser);
      return normalizedUser;
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    localStorage.removeItem("indcool_token");
    localStorage.removeItem("indcool_user");
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
