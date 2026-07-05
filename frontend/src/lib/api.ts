const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

type HttpMethod = "GET" | "POST" | "PUT" | "DELETE";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, options: { method?: HttpMethod; body?: unknown } = {}): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    method: options.method ?? "GET",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  const isJson = response.headers.get("content-type")?.includes("application/json");
  const payload = isJson ? await response.json().catch(() => null) : null;

  if (!response.ok) {
    const message = payload?.detail || payload?.error?.message || `Request failed (${response.status})`;
    throw new ApiError(message, response.status);
  }

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
