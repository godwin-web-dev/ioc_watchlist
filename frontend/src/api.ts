import type { IOC, IOCType, NewIOC } from "./types";

/** Error carrying the backend's structured detail (code, message, existing entry). */
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
    public existing?: IOC,
  ) {
    super(message);
  }
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, init);
  } catch {
    throw new ApiError("Cannot reach the server. Is the backend running?", 0);
  }
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const d = body?.detail;
    throw new ApiError(
      typeof d === "string" ? d : (d?.message ?? `Request failed (${res.status})`),
      res.status,
      d?.code,
      d?.existing,
    );
  }
  return body as T;
}

export const api = {
  list(filters: { tag?: string; type?: IOCType | "" }): Promise<IOC[]> {
    const params = new URLSearchParams();
    if (filters.tag) params.set("tag", filters.tag);
    if (filters.type) params.set("type", filters.type);
    const qs = params.toString();
    return request(`/api/iocs${qs ? `?${qs}` : ""}`);
  },
  tags(): Promise<string[]> {
    return request("/api/tags");
  },
  create(ioc: NewIOC): Promise<IOC> {
    return request("/api/iocs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(ioc),
    });
  },
  remove(id: number): Promise<void> {
    return request(`/api/iocs/${id}`, { method: "DELETE" });
  },
};
