const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const csrfHeaderName = import.meta.env.VITE_CSRF_HEADER_NAME ?? "X-CSRF-Token";

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
const unsafeMethods = new Set<HttpMethod>(["POST", "PUT", "PATCH", "DELETE"]);

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

// CSRF state stays in memory; the matching browser cookie remains HttpOnly.
let csrfToken: string | null = null;
let csrfTokenPromise: Promise<string> | null = null;


function readCsrfToken(payload: unknown): string | null {
  if (typeof payload !== "object" || payload === null) return null;
  const token = (payload as { csrf_token?: unknown }).csrf_token;
  return typeof token === "string" && token.length > 0 ? token : null;
}


async function loadCsrfToken(): Promise<string> {
  const response = await fetch(`${baseUrl}/auth/csrf`, { credentials: "include" });
  const payload = await response.json().catch(() => null);
  const token = readCsrfToken(payload);

  if (!response.ok || token === null) {
    throw new ApiError("Unable to initialize CSRF protection", response.status);
  }

  csrfToken = token;
  return token;
}


async function getCsrfToken(forceRefresh = false): Promise<string> {
  if (!forceRefresh && csrfToken !== null) return csrfToken;

  if (csrfTokenPromise === null) {
    csrfTokenPromise = loadCsrfToken().finally(() => {
      csrfTokenPromise = null;
    });
  }

  return csrfTokenPromise;
}


function isCsrfFailure(payload: unknown): boolean {
  if (typeof payload !== "object" || payload === null) return false;
  const error = (payload as { error?: { code?: unknown } }).error;
  return error?.code === "csrf_validation_failed";
}


// Every browser write first obtains a matching token, then sends it in the custom CSRF header.
async function request<T>(
  path: string,
  options: { method?: HttpMethod; body?: unknown } = {},
  retryCsrf = true,
): Promise<T> {
  const method = options.method ?? "GET";
  const needsCsrf = unsafeMethods.has(method);
  const token = needsCsrf ? await getCsrfToken() : null;
  const response = await fetch(`${baseUrl}${path}`, {
    method,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(token === null ? {} : { [csrfHeaderName]: token }),
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  const isJson = response.headers.get("content-type")?.includes("application/json");
  const payload = isJson ? await response.json().catch(() => null) : null;
  const rotatedCsrfToken = readCsrfToken(payload);
  if (rotatedCsrfToken !== null) csrfToken = rotatedCsrfToken;

  if (!response.ok) {
    if (needsCsrf && retryCsrf && response.status === 403 && isCsrfFailure(payload)) {
      csrfToken = null;
      await getCsrfToken(true);
      return request<T>(path, options, false);
    }
    const message = payload?.detail || payload?.error?.message || `Request failed (${response.status})`;
    throw new ApiError(message, response.status);
  }

  if (path === "/auth/logout") csrfToken = null;

  return payload as T;
}

export type Priority = "low" | "medium" | "high";

export type Task = {
  id: number;
  user_id: number;
  name: string;
  description: string | null;
  start_date: string | null;
  end_date: string | null;
  priority: Priority;
  created_at: string;
  updated_at: string;
};

export type TaskPayload = {
  name: string;
  description: string | null;
  start_date: string | null;
  end_date: string | null;
  priority: Priority;
};

export type TaskCreationType = "hobbies" | "work";

export type SummaryTask = {
  id: number;
  all_task: string;
};

export type AuthResponse = {
  message: string;
  csrf_token: string;
};

let refreshPromise: Promise<AuthResponse> | null = null;

function refreshSession(): Promise<AuthResponse> {
  if (refreshPromise === null) {
    refreshPromise = request<AuthResponse>("/auth/refresh", { method: "POST" }).finally(() => {
      refreshPromise = null;
    });
  }

  return refreshPromise;
}

export type UserRead = {
  id: number;
  email: string;
  full_name: string | null;
  created_at: string;
};

export type LogoutRequest = {
  logout_all?: boolean;
};

export const api = {
  health() {
    return request<{ status: string; app: string }>("/health");
  },
  register(body: { email: string; password: string; full_name: string | null }) {
    return request<UserRead>("/auth/register", { method: "POST", body });
  },
  login(body: { email: string; password: string }) {
    return request<AuthResponse>("/auth/login", { method: "POST", body });
  },
  refresh() {
    return refreshSession();
  },
  logout(body: LogoutRequest) {
    return request<void>("/auth/logout", { method: "POST", body });
  },
  listTasks() {
    return request<Task[]>("/tasks");
  },
  createTask(body: TaskPayload) {
    return request<Task>("/tasks", { method: "POST", body });
  },
  createTaskFromAI(body: { type: TaskCreationType }) {
    return request<Task>("/task_creation", { method: "POST", body });
  },
  createSummaryTask(body: { summary: string }) {
    return request<SummaryTask>("/tasks/summary", { method: "POST", body });
  },
  updateTask(id: number, body: Partial<TaskPayload>) {
    return request<Task>(`/tasks/${id}`, { method: "PUT", body });
  },
  deleteTask(id: number) {
    return request<void>(`/tasks/${id}`, { method: "DELETE" });
  },
};
