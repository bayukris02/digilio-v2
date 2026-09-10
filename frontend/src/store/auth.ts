import { create } from 'zustand';
import { authApi, type AuthTokens } from '../api/auth';
import { accessApi, type MyAccess } from '../api/access';

interface AuthState {
  isAuthenticated: boolean;
  user: { username: string } | null;
  /** Hak akses user (role + menu yang diizinkan) — null selama belum dimuat */
  access: MyAccess | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  loadAccess: () => Promise<void>;
}

const storedToken = localStorage.getItem('access_token');

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: !!storedToken,
  user: null,
  access: null,

  login: async (username: string, password: string) => {
    const tokens: AuthTokens = await authApi.login({ username, password });
    localStorage.setItem('access_token', tokens.access);
    localStorage.setItem('refresh_token', tokens.refresh);
    set({ isAuthenticated: true, user: { username }, access: null });
  },

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    set({ isAuthenticated: false, user: null, access: null });
  },

  loadAccess: async () => {
    const access = await accessApi.getMe();
    set({ access });
  },
}));
