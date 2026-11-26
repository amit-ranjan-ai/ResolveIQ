import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 15000,
});

// Automatically attach the login token to API requests.
api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem("resolveiq_access_token");

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

// Clear expired or invalid sessions.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      sessionStorage.removeItem("resolveiq_access_token");

      window.dispatchEvent(new Event("resolveiq:unauthorized"));
    }

    return Promise.reject(error);
  },
);
