import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

import api, { clearTokens, storeTokens } from "../api/client";

/** تحقق الجلسة عبر الكوكي — لا توكن في JS إطلاقاً. */
interface User {
  id: string;
  username: string;
  full_name: string;
  email: string;
  role: string | null;
  twofa_enabled: boolean;
  is_superuser: boolean;
}

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (username: string, password: string, twofaCode?: string) => Promise<void>;
  register: (data: RegisterPayload) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

interface RegisterPayload {
  full_name: string;
  email: string;
  username: string;
  password: string;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    // الجلسة تُتحقق عبر كوكي HttpOnly — أي 401 تعني غير مسجل
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = useCallback(
    async (username: string, password: string, twofaCode?: string) => {
      const { data } = await api.post("/auth/login", {
        username,
        password,
        twofa_code: twofaCode,
      });
      if (data.twofa_required) {
        throw new Error("2FA_REQUIRED");
      }
      // الكوكيز ضُبطت من الخادم عبر Set-Cookie — لا تخزين محلي
      storeTokens("", "");
      await refreshUser();
    },
    [refreshUser]
  );

  const register = useCallback(async (payload: RegisterPayload) => {
    await api.post("/auth/register", payload);
  }, []);

  const logout = useCallback(() => {
    // مسح الكوكيز من الخادم ثم تنظيف الحالة المحلية
    api.post("/auth/logout").catch(() => undefined).finally(() => {
      clearTokens();
      setUser(null);
    });
  }, []);

  const value: AuthContextValue = {
    user,
    loading,
    isAuthenticated: Boolean(user),
    login,
    register,
    logout,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (ctx === undefined) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
