import { create } from 'zustand';
import type { CurrentUser, LoginResponseData, RefreshTokenResponseData } from '../services/auth';

const TOKEN_KEY = 'esg_access_token';
const REFRESH_TOKEN_KEY = 'esg_refresh_token';

function readStorage(key: string): string | null {
  if (typeof window === 'undefined') return null;
  return window.localStorage.getItem(key);
}

function writeStorage(key: string, value: string): void {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(key, value);
}

function removeStorage(key: string): void {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem(key);
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  currentUser: CurrentUser | null;
  setSession: (session: LoginResponseData) => void;
  setTokens: (tokens: RefreshTokenResponseData) => void;
  setCurrentUser: (user: CurrentUser) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: readStorage(TOKEN_KEY),
  refreshToken: readStorage(REFRESH_TOKEN_KEY),
  currentUser: null,
  setSession: (session) => {
    writeStorage(TOKEN_KEY, session.access_token);
    writeStorage(REFRESH_TOKEN_KEY, session.refresh_token);
    set({ accessToken: session.access_token, refreshToken: session.refresh_token, currentUser: null });
  },
  setTokens: (tokens) => {
    writeStorage(TOKEN_KEY, tokens.access_token);
    writeStorage(REFRESH_TOKEN_KEY, tokens.refresh_token);
    set({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token });
  },
  setCurrentUser: (user) => set({ currentUser: user }),
  logout: () => {
    removeStorage(TOKEN_KEY);
    removeStorage(REFRESH_TOKEN_KEY);
    set({ accessToken: null, refreshToken: null, currentUser: null });
  },
}));
