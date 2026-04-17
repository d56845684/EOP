import type { TokenPair } from '@/api/auth';

const ACCESS_TOKEN_KEY = 'eop_access_token';

export const getAccessToken = () => {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
};

export const setAuthTokens = (tokens?: Partial<TokenPair> | null) => {
  if (!tokens?.access_token) return;
  localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
};

export const clearAuthTokens = () => {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
};
