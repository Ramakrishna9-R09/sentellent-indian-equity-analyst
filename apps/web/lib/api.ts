import type { ChatReply, Follow, IngestionJob, Profile, Stock, User } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api";

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(API_BASE + path, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init.headers || {})
    }
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "Request failed (" + response.status + ")");
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  me: () => request<User>("/auth/me"),
  follows: () => request<Follow[]>("/follows"),
  searchStocks: (query: string) => request<Stock[]>("/stocks/search?q=" + encodeURIComponent(query)),
  follow: (symbol: string, exchange = "NSE", company_name?: string) =>
    request<Follow>("/follows", {
      method: "POST",
      body: JSON.stringify({ symbol, exchange, company_name })
    }),
  refresh: (symbol: string) =>
    request<IngestionJob>("/stocks/" + symbol + "/refresh", { method: "POST" }),
  createThread: () => request<{ id: string }>("/chat/threads", { method: "POST", body: "{}" }),
  sendMessage: (threadId: string, question: string) =>
    request<ChatReply>("/chat/threads/" + threadId + "/messages", {
      method: "POST",
      body: JSON.stringify({ question })
    }),
  profile: () => request<Profile>("/profile"),
  patchProfile: (patch: Record<string, unknown>) =>
    request<Profile>("/profile", { method: "PATCH", body: JSON.stringify(patch) }),
  logout: () => request<void>("/auth/logout", { method: "POST" })
};

export function apiLoginUrl(): string {
  return API_BASE + "/auth/google/login";
}
