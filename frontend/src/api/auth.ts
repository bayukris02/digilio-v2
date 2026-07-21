import api from './client';

export interface LoginPayload {
  username: string;
  password: string;
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export const authApi = {
  login: (payload: LoginPayload) =>
    api.post<AuthTokens>('/auth/login/', payload).then((r) => r.data),
  refresh: (refresh: string) =>
    api.post<{ access: string }>('/auth/refresh/', { refresh }).then((r) => r.data),
};
