import { createContext, useContext, useState, ReactNode } from "react";
import { jwtDecode } from "jwt-decode";
import { components } from "../api/schema";

type User = components["schemas"]["UserResponse"];

interface AuthContextType {
  token: string | null;
  user: User | null;
  isLoading: boolean;
  login: (token: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => {
    const storedToken = localStorage.getItem("auth_token");
    if (!storedToken) return null;
    try {
      const decoded = jwtDecode<{ exp: number }>(storedToken);
      if (decoded.exp * 1000 < Date.now()) {
        localStorage.removeItem("auth_token");
        return null;
      }
      return storedToken;
    } catch {
      localStorage.removeItem("auth_token");
      return null;
    }
  });

  const [user, setUser] = useState<User | null>(() => {
    const storedToken = localStorage.getItem("auth_token");
    if (!storedToken) return null;
    try {
      const decoded = jwtDecode<{ sub: string; role: components["schemas"]["Role"]; exp: number }>(storedToken);
      if (decoded.exp * 1000 < Date.now()) return null;
      return {
        email: decoded.sub,
        role: decoded.role,
        id: "00000000-0000-0000-0000-000000000000",
        is_active: true,
      };
    } catch {
      return null;
    }
  });

  const isLoading = false; // Synchronous initialization in useState doesn't need loading state

  const login = (newToken: string) => {
    localStorage.setItem("auth_token", newToken);
    setToken(newToken);
    const decoded = jwtDecode<{ sub: string; role: components["schemas"]["Role"] }>(newToken);
    setUser({
      email: decoded.sub,
      role: decoded.role,
      id: "00000000-0000-0000-0000-000000000000",
      is_active: true,
    });
  };

  const logout = () => {
    localStorage.removeItem("auth_token");
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ token, user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
