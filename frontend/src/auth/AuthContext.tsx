import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { apiGet, apiPost, clearToken, getToken, setToken } from "../api/client";
import type { UserPublic } from "../types";

interface AuthState {
  user: UserPublic | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserPublic | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 起動時: トークンがあれば /api/me で検証してユーザーを復元
    const token = getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    apiGet<UserPublic>("/api/me")
      .then(setUser)
      .catch(() => clearToken())
      .finally(() => setLoading(false));
  }, []);

  const login = async (username: string, password: string) => {
    const res = await apiPost<{ token: string; user: UserPublic }>("/api/login", {
      username,
      password,
    });
    setToken(res.token);
    setUser(res.user);
  };

  const logout = async () => {
    try {
      await apiPost("/api/logout");
    } catch {
      /* ignore */
    }
    clearToken();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
