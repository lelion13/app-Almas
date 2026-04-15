import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { apiFetch, setToken } from "@/services/api";

type Me = { id: string; email: string; role: string };

type AuthState = {
  token: string | null;
  me: Me | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTok] = useState<string | null>(() => localStorage.getItem("almas_token"));
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(!!token);

  const loadMe = useCallback(async (t: string) => {
    setLoading(true);
    try {
      const m = await apiFetch<Me>("/api/v1/auth/me", {
        auth: false,
        headers: { Authorization: `Bearer ${t}` },
      });
      setMe(m);
    } catch {
      setToken(null);
      setTok(null);
      setMe(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (token) loadMe(token);
    else {
      setMe(null);
      setLoading(false);
    }
  }, [token, loadMe]);

  const login = useCallback(async (email: string, password: string) => {
    const res = await apiFetch<{ access_token: string }>("/api/v1/auth/login", {
      auth: false,
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    setToken(res.access_token);
    setTok(res.access_token);
    await loadMe(res.access_token);
  }, [loadMe]);

  const logout = useCallback(() => {
    setToken(null);
    setTok(null);
    setMe(null);
    void apiFetch("/api/v1/auth/logout", { method: "POST" }).catch(() => {});
  }, []);

  const value = useMemo(
    () => ({ token, me, loading, login, logout }),
    [token, me, loading, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside provider");
  return ctx;
}
