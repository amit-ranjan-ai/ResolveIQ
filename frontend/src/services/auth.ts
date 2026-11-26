import { api } from "./api";

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface CurrentUser {
  id: string;
  full_name: string;
  email: string;
  is_active: boolean;
  email_verified_at: string | null;
  created_at: string;
  updated_at: string;
}

const TOKEN_KEY = "resolveiq_access_token";

export async function login(
  credentials: LoginCredentials,
): Promise<TokenResponse> {
  const response = await api.post<TokenResponse>("/auth/login", credentials);

  sessionStorage.setItem(TOKEN_KEY, response.data.access_token);

  return response.data;
}

export async function getCurrentUser(): Promise<CurrentUser> {
  const response = await api.get<CurrentUser>("/users/me");
  return response.data;
}

export function logout(): void {
  sessionStorage.removeItem(TOKEN_KEY);
}

export function getAccessToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}
