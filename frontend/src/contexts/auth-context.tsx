import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import {
  getAccessToken,
  getCurrentUser,
  login as loginUser,
  logout as logoutUser,
  type CurrentUser,
  type LoginCredentials,
} from "@/services/auth";

interface AuthContextType {
  user: CurrentUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const logout = useCallback(() => {
    logoutUser();
    setUser(null);
  }, []);

  const login = useCallback(async (credentials: LoginCredentials) => {
    await loginUser(credentials);

    try {
      const currentUser = await getCurrentUser();
      setUser(currentUser);
    } catch (error) {
      logoutUser();
      throw error;
    }
  }, []);

  useEffect(() => {
    let active = true;

    async function restoreSession() {
      if (!getAccessToken()) {
        if (active) setIsLoading(false);
        return;
      }

      try {
        const currentUser = await getCurrentUser();
        if (active) setUser(currentUser);
      } catch {
        logoutUser();
        if (active) setUser(null);
      } finally {
        if (active) setIsLoading(false);
      }
    }

    function handleUnauthorized() {
      if (active) setUser(null);
    }

    window.addEventListener("resolveiq:unauthorized", handleUnauthorized);

    void restoreSession();

    return () => {
      active = false;
      window.removeEventListener("resolveiq:unauthorized", handleUnauthorized);
    };
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: user !== null,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }

  return context;
}
