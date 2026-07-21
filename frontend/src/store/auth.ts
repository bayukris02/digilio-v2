import { create } from 'zustand';
import { authApi, type AuthTokens } from '../api/auth';

interface AuthState {
  isAuthenticated: boolean;
  user: { username: string } | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const storedToken = localStorage.getItem('access_token');

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: !!storedToken,
  user: null,

  login: async (username: string, password: string) => {
    const tokens: AuthTokens = await authApi.login({ username, password });
    localStorage.setItem('access_token', tokens.access);
    localStorage.setItem('refresh_token', tokens.refresh);
    set({ isAuthenticated: true, user: { username } });
  },

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    set({ isAuthenticated: false, user: null });
  },
}));
