import { create } from 'zustand';
import type { CurrentUser, LoginResponseData } from '../services/auth';

const TOKEN_KEY = 'esg_access_token';
const REFRESH_TOKEN_KEY = 'esg_refresh_token';

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  currentUser: CurrentUser | null;
  setSession: (session: LoginResponseData) => void;
  setCurrentUser: (user: CurrentUser) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: window.localStorage.getItem(TOKEN_KEY),
  refreshToken: window.localStorage.getItem(REFRESH_TOKEN_KEY),
  currentUser: null,
  setSession: (session) => {
    window.localStorage.setItem(TOKEN_KEY, session.access_token);
    window.localStorage.setItem(REFRESH_TOKEN_KEY, session.refresh_token);
    set({ accessToken: session.access_token, refreshToken: session.refresh_token });
  },
  setCurrentUser: (user) => set({ currentUser: user }),
  logout: () => {
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(REFRESH_TOKEN_KEY);
    set({ accessToken: null, refreshToken: null, currentUser: null });
  },
}));
