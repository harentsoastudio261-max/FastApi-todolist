import { useEffect, useMemo, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import {
  ArrowRight,
  CheckCircle2,
  CirclePlus,
  Edit3,
  Eye,
  EyeOff,
  FileText,
  LayoutDashboard,
  ListTodo,
  LogIn,
  LogOut,
  RefreshCw,
  Save,
  ShieldCheck,
  Sparkles,
  Trash2,
} from "lucide-react";
import { Link, NavLink, Navigate, Route, Routes } from "react-router-dom";
import { api, ApiError, Priority, Task, TaskCreationType, TaskPayload } from "./lib/api";

type AuthMode = "login" | "register";
type TaskFormState = {
  name: string;
  description: string;
  start_date: string;
  end_date: string;
  priority: Priority;
};

const emptyTaskForm: TaskFormState = {
  name: "",
  description: "",
  start_date: "",
  end_date: "",
  priority: "medium",
};

function formatDate(value: string | null) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#fff7ed_0%,#fffbeb_42%,#eff6ff_100%)] text-slate-950">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <div className="flex items-center gap-2 font-semibold">
          <CheckCircle2 className="h-5 w-5 text-amber-600" />
          FastAPI TodoList
        </div>
        <nav className="flex items-center gap-4 text-sm text-slate-600">
          <NavLink to="/summary" className={({ isActive }) => (isActive ? "font-medium text-slate-950" : "")}>Summary</NavLink>
          <NavLink to="/tasks" className={({ isActive }) => (isActive ? "font-medium text-slate-950" : "")}>Tasks</NavLink>
        </nav>
      </header>
      <main className="mx-auto max-w-6xl px-6 pb-12 pt-4">{children}</main>
    </div>
  );
}

function SummaryPage() {
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authBusy, setAuthBusy] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [summary, setSummary] = useState("");
  const [lastSaved, setLastSaved] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  function clearSession() {
    setIsAuthenticated(false);
  }

  function withSession<T>(action: () => Promise<T>): Promise<T> {
    return action().catch(async (err) => {
      if (!(err instanceof ApiError) || err.status !== 401) {
        throw err;
      }
      await api.refresh();
      setIsAuthenticated(true);
      return action();
    });
  }

  useEffect(() => {
    async function restoreSession() {
      try {
        await api.refresh();
        setIsAuthenticated(true);
      } catch {
        clearSession();
      }
    }

    void restoreSession();
  }, []);

  async function handleAuthSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setMessage("");
    setAuthBusy(true);
    try {
      if (authMode === "register") {
        await api.register({ email, password, full_name: fullName || null });
        setMessage("Account created. You can login now.");
        setAuthMode("login");
      } else {
        await api.login({ email, password });
        setIsAuthenticated(true);
        setMessage("Logged in successfully.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setAuthBusy(false);
    }
  }

  async function handleSummarySubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const trimmed = summary.trim();
    if (!trimmed) {
      return;
    }
    setError("");
    setMessage("");
    setSubmitting(true);
    try {
      const saved = await api.createSummaryTask({ summary: trimmed });
      setLastSaved(saved.all_task);
      setSummary("");
      setMessage("Summary saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save summary");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleLogout(logoutAll = false) {
    if (!isAuthenticated) return;
    setError("");
    setMessage("");
    try {
      await api.logout({ logout_all: logoutAll });
      clearSession();
      setLastSaved("");
      setMessage(logoutAll ? "Logged out from all sessions." : "Logged out from this session.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Logout failed");
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[360px,1fr]">
      <aside className="space-y-6">
        <section className="rounded-3xl border border-amber-200 bg-white/90 p-5 shadow-soft backdrop-blur">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-600">
            <LogIn className="h-4 w-4" />
            Authentication
          </div>
          <div className="mt-4 flex rounded-xl border border-slate-200 bg-slate-50 p-1 text-sm">
            <button className={`flex-1 rounded-lg px-3 py-2 ${authMode === "login" ? "bg-white shadow-sm" : "text-slate-500"}`} onClick={() => setAuthMode("login")} type="button">Login</button>
            <button className={`flex-1 rounded-lg px-3 py-2 ${authMode === "register" ? "bg-white shadow-sm" : "text-slate-500"}`} onClick={() => setAuthMode("register")} type="button">Register</button>
          </div>
          <form className="mt-4 space-y-3" onSubmit={handleAuthSubmit}>
            <input className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-amber-400" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
            {authMode === "register" && (
              <input className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-amber-400" placeholder="Full name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
            )}
            <div className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2">
              <input className="flex-1 border-0 bg-transparent text-sm outline-none" type={showPassword ? "text" : "password"} placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} />
              <button type="button" className="text-slate-500" onClick={() => setShowPassword((value) => !value)}>
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            <button className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 py-2 text-sm font-medium text-white disabled:opacity-60" type="submit" disabled={authBusy}>
              {authMode === "login" ? <LogIn className="h-4 w-4" /> : <CirclePlus className="h-4 w-4" />}
              {authBusy ? "Working..." : authMode === "login" ? "Login" : "Create account"}
            </button>
          </form>
        </section>

        <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-600">
            <LayoutDashboard className="h-4 w-4" />
            Session
          </div>
          <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs leading-5 text-slate-600 break-all">
            {isAuthenticated ? "Session active" : "No active session"}
          </div>
          <div className="mt-3 flex gap-2">
            <button className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 disabled:opacity-60" type="button" onClick={() => void api.refresh().then(() => setIsAuthenticated(true)).catch(() => clearSession())}>
              <RefreshCw className="h-4 w-4" />
              Refresh
            </button>
            <button className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 disabled:opacity-60" type="button" onClick={() => void handleLogout(false)} disabled={!isAuthenticated}>
              <LogOut className="h-4 w-4" />
              Logout
            </button>
          </div>
          <button className="mt-2 inline-flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 disabled:opacity-60" type="button" onClick={() => void handleLogout(true)} disabled={!isAuthenticated}>
            <LogOut className="h-4 w-4" />
            Logout all sessions
          </button>
        </section>
      </aside>

      <section className="space-y-6">
        <div className="rounded-[28px] border border-amber-200 bg-[linear-gradient(135deg,#fff7ed_0%,#ffffff_45%,#eff6ff_100%)] p-6 shadow-soft">
          <div className="flex items-center gap-3 text-sm font-medium text-amber-700">
            <FileText className="h-4 w-4" />
            Summary workspace
          </div>
          <h1 className="mt-4 max-w-2xl text-3xl font-semibold tracking-tight text-slate-950">Write one line, press Enter, and store it as a summary task.</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
            The text you type is sent to `POST /tasks/summary`. This route is public, the backend stores it in the `all_task` column, then the input resets.
          </p>

          <form className="mt-6" onSubmit={handleSummarySubmit}>
            <input
              className="w-full rounded-2xl border border-amber-200 bg-white px-4 py-4 text-base outline-none transition focus:border-amber-400"
              placeholder="Type your summary and press Enter"
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              disabled={submitting}
            />
          </form>

        </div>

        {(error || message) && (
          <div className={`rounded-2xl border p-4 text-sm ${error ? "border-rose-200 bg-rose-50 text-rose-700" : "border-emerald-200 bg-emerald-50 text-emerald-700"}`}>
            {error || message}
          </div>
        )}

        <div className="grid gap-4 md:grid-cols-2">
          <article className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm font-medium text-slate-600">Last saved summary</div>
            <p className="mt-3 min-h-24 text-sm leading-6 text-slate-800">{lastSaved || "Nothing saved yet."}</p>
          </article>
          <article className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm font-medium text-slate-600">Endpoint</div>
            <p className="mt-3 text-sm leading-6 text-slate-800"><code>/tasks/summary</code> with body <code>{"{"}"summary": "..."{"}"}</code></p>
          </article>
        </div>
      </section>
    </div>
  );
}

function Tasks() {
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(false);
  const [authBusy, setAuthBusy] = useState(false);
  const [aiTaskType, setAiTaskType] = useState<TaskCreationType>("work");
  const [aiBusy, setAiBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<TaskFormState>(emptyTaskForm);

  function clearSession() {
    setIsAuthenticated(false);
  }

  function withSession<T>(action: () => Promise<T>): Promise<T> {
    return action().catch(async (err) => {
      if (!(err instanceof ApiError) || err.status !== 401) {
        throw err;
      }
      await api.refresh();
      setIsAuthenticated(true);
      return action();
    });
  }

  async function loadTasks() {
    if (!isAuthenticated) return;
    setLoading(true);
    setError("");
    try {
      const data = await withSession(() => api.listTasks());
      setTasks(data);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        clearSession();
        setTasks([]);
        setError("Session expired. Please login again.");
      } else {
        setError(err instanceof Error ? err.message : "Failed to load tasks");
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    async function restoreSession() {
      try {
        await api.refresh();
        setIsAuthenticated(true);
        const data = await api.listTasks();
        setTasks(data);
      } catch {
        clearSession();
        setTasks([]);
      }
    }

    void restoreSession();
  }, []);

  function resetForm() {
    setEditingId(null);
    setForm(emptyTaskForm);
  }

  function startEdit(task: Task) {
    setEditingId(task.id);
    setForm({
      name: task.name,
      description: task.description ?? "",
      start_date: task.start_date ? task.start_date.slice(0, 16) : "",
      end_date: task.end_date ? task.end_date.slice(0, 16) : "",
      priority: task.priority,
    });
  }

  async function handleAuthSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setMessage("");
    setAuthBusy(true);
    try {
      if (authMode === "register") {
        await api.register({ email, password, full_name: fullName || null });
        setMessage("Account created. You can login now.");
        setAuthMode("login");
      } else {
        await api.login({ email, password });
        setIsAuthenticated(true);
        setMessage("Logged in successfully.");
        const data = await api.listTasks();
        setTasks(data);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setAuthBusy(false);
    }
  }

  async function handleSaveTask(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!isAuthenticated) {
      setError("You need to login first.");
      return;
    }
    setError("");
    setMessage("");

    const payload: TaskPayload = {
      name: form.name.trim(),
      description: form.description.trim() || null,
      start_date: form.start_date ? new Date(form.start_date).toISOString() : null,
      end_date: form.end_date ? new Date(form.end_date).toISOString() : null,
      priority: form.priority,
    };

    try {
      if (editingId) {
        await withSession(() => api.updateTask(editingId, payload));
        setMessage("Task updated.");
      } else {
        await withSession(() => api.createTask(payload));
        setMessage("Task created.");
      }
      resetForm();
      await loadTasks();
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        clearSession();
        setTasks([]);
        setError("Session expired. Please login again.");
      } else {
        setError(err instanceof Error ? err.message : "Failed to save task");
      }
    }
  }

  async function handleCreateAITask() {
    if (!isAuthenticated) {
      setError("You need to login first.");
      return;
    }
    setError("");
    setMessage("");
    setAiBusy(true);
    try {
      await withSession(() => api.createTaskFromAI({ type: aiTaskType }));
      setMessage(`AI ${aiTaskType} task generated.`);
      resetForm();
      await loadTasks();
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        clearSession();
        setTasks([]);
        setError("Session expired. Please login again.");
      } else {
        setError(err instanceof Error ? err.message : "Failed to generate AI task");
      }
    } finally {
      setAiBusy(false);
    }
  }

  async function handleDelete(id: number) {
    if (!isAuthenticated) return;
    setError("");
    setMessage("");
    try {
      await withSession(() => api.deleteTask(id));
      setTasks((current) => current.filter((task) => task.id !== id));
      setMessage("Task deleted.");
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        clearSession();
        setTasks([]);
        setError("Session expired. Please login again.");
      } else {
        setError(err instanceof Error ? err.message : "Failed to delete task");
      }
    }
  }

  function handleLogoutLocal() {
    clearSession();
    setTasks([]);
    resetForm();
    setMessage("Logged out locally.");
  }

  async function handleLogoutServer(logoutAll = false) {
    if (!isAuthenticated) return;
    setError("");
    setMessage("");
    try {
      await api.logout({ logout_all: logoutAll });
      handleLogoutLocal();
      setMessage(logoutAll ? "Logged out from all sessions." : "Logged out from this session.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Logout failed");
    }
  }

  const title = useMemo(() => (editingId ? "Edit task" : "Create task"), [editingId]);

  return (
    <div className="grid gap-6 lg:grid-cols-[360px,1fr]">
      <aside className="space-y-6">
        <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-600">
            <LogIn className="h-4 w-4" />
            Authentication
          </div>
          <div className="mt-4 flex rounded-xl border border-slate-200 bg-slate-50 p-1 text-sm">
            <button className={`flex-1 rounded-lg px-3 py-2 ${authMode === "login" ? "bg-white shadow-sm" : "text-slate-500"}`} onClick={() => setAuthMode("login")} type="button">Login</button>
            <button className={`flex-1 rounded-lg px-3 py-2 ${authMode === "register" ? "bg-white shadow-sm" : "text-slate-500"}`} onClick={() => setAuthMode("register")} type="button">Register</button>
          </div>
          <form className="mt-4 space-y-3" onSubmit={handleAuthSubmit}>
            <input className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-slate-400" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
            {authMode === "register" && (
              <input className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-slate-400" placeholder="Full name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
            )}
            <div className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2">
              <input className="flex-1 border-0 bg-transparent text-sm outline-none" type={showPassword ? "text" : "password"} placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} />
              <button type="button" className="text-slate-500" onClick={() => setShowPassword((value) => !value)}>
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            <button className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 py-2 text-sm font-medium text-white disabled:opacity-60" type="submit" disabled={authBusy}>
              {authMode === "login" ? <LogIn className="h-4 w-4" /> : <CirclePlus className="h-4 w-4" />}
              {authBusy ? "Working..." : authMode === "login" ? "Login" : "Create account"}
            </button>
          </form>
        </section>

        <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-600">
            <LayoutDashboard className="h-4 w-4" />
            Session
          </div>
          <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs leading-5 text-slate-600 break-all">
            {isAuthenticated ? "Session active" : "No active session"}
          </div>
          <div className="mt-3 flex gap-2">
            <button className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 disabled:opacity-60" type="button" onClick={() => void loadTasks()} disabled={!isAuthenticated || loading}>
              <RefreshCw className="h-4 w-4" />
              Refresh
            </button>
            <button className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 disabled:opacity-60" type="button" onClick={() => void handleLogoutServer(false)} disabled={!isAuthenticated}>
              <LogOut className="h-4 w-4" />
              Logout
            </button>
          </div>
          <button className="mt-2 inline-flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 disabled:opacity-60" type="button" onClick={() => void handleLogoutServer(true)} disabled={!isAuthenticated}>
            <LogOut className="h-4 w-4" />
            Logout all sessions
          </button>
          <p className="mt-3 text-xs leading-5 text-slate-500">The browser sends secure HttpOnly cookies automatically.</p>
        </section>
      </aside>

      <section className="space-y-6">
        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-sm font-medium text-slate-600">Task workspace</div>
              <h2 className="text-2xl font-semibold tracking-tight text-slate-950">{title}</h2>
            </div>
            <div className="flex items-center gap-2">
              <button className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 disabled:opacity-60" type="button" onClick={() => void loadTasks()} disabled={!isAuthenticated || loading}>
                <RefreshCw className="h-4 w-4" />
                {loading ? "Loading..." : "Reload"}
              </button>
              <button className="inline-flex items-center gap-2 rounded-xl bg-slate-950 px-4 py-2 text-sm font-medium text-white" type="button" onClick={resetForm}>
                <ArrowRight className="h-4 w-4" />
                New task
              </button>
            </div>
          </div>

          <form className="mt-5 grid gap-3 md:grid-cols-2" onSubmit={handleSaveTask}>
            <input className="rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-slate-400 md:col-span-2" placeholder="Task name" value={form.name} onChange={(e) => setForm((current) => ({ ...current, name: e.target.value }))} />
            <textarea className="min-h-24 rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-slate-400 md:col-span-2" placeholder="Description" value={form.description} onChange={(e) => setForm((current) => ({ ...current, description: e.target.value }))} />
            <input className="rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-slate-400" type="datetime-local" value={form.start_date} onChange={(e) => setForm((current) => ({ ...current, start_date: e.target.value }))} />
            <input className="rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-slate-400" type="datetime-local" value={form.end_date} onChange={(e) => setForm((current) => ({ ...current, end_date: e.target.value }))} />
            <select className="rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-slate-400" value={form.priority} onChange={(e) => setForm((current) => ({ ...current, priority: e.target.value as Priority }))}>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
            <button className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 py-2 text-sm font-medium text-white md:col-span-2" type="submit" disabled={!isAuthenticated}>
              <Save className="h-4 w-4" />
              {editingId ? "Update task" : "Create task"}
            </button>
          </form>

          <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50/70 p-4">
            <div className="flex flex-wrap items-end gap-3">
              <div className="min-w-44 flex-1">
                <label className="text-xs font-medium uppercase tracking-wide text-amber-700" htmlFor="ai-task-type">AI task type</label>
                <select
                  id="ai-task-type"
                  className="mt-2 w-full rounded-xl border border-amber-200 bg-white px-3 py-2 text-sm outline-none focus:border-amber-400"
                  value={aiTaskType}
                  onChange={(e) => setAiTaskType(e.target.value as TaskCreationType)}
                  disabled={!isAuthenticated || aiBusy}
                >
                  <option value="work">Work</option>
                  <option value="hobbies">Hobbies</option>
                </select>
              </div>
              <button
                className="inline-flex min-w-44 items-center justify-center gap-2 rounded-xl bg-amber-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
                type="button"
                onClick={() => void handleCreateAITask()}
                disabled={!isAuthenticated || aiBusy}
              >
                <Sparkles className="h-4 w-4" />
                {aiBusy ? "Generating..." : "Generate with AI"}
              </button>
            </div>
          </div>
        </div>

        {(error || message) && (
          <div className={`rounded-2xl border p-4 text-sm ${error ? "border-rose-200 bg-rose-50 text-rose-700" : "border-emerald-200 bg-emerald-50 text-emerald-700"}`}>
            {error || message}
          </div>
        )}

        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-sm font-medium text-slate-600">Tasks</div>
              <div className="text-lg font-semibold text-slate-950">{tasks.length} items</div>
            </div>
            <button className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 disabled:opacity-60" type="button" onClick={() => void loadTasks()} disabled={!isAuthenticated || loading}>
              <RefreshCw className="h-4 w-4" />
              {loading ? "Loading..." : "Reload"}
            </button>
          </div>

          {!isAuthenticated && <div className="mt-5 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-600">Login to load tasks.</div>}

          {isAuthenticated && tasks.length === 0 && !loading && (
            <div className="mt-5 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-600">No tasks yet. Create your first one above.</div>
          )}

          <div className="mt-5 grid gap-4">
            {tasks.map((task) => (
              <article key={task.id} className="rounded-2xl border border-slate-200 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-slate-500">
                      <span className="rounded-full bg-slate-100 px-2 py-1">{task.priority}</span>
                      <span>#{task.id}</span>
                    </div>
                    <h3 className="mt-2 text-lg font-semibold text-slate-950">{task.name}</h3>
                    <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">{task.description || "No description"}</p>
                  </div>
                  <div className="flex gap-2">
                    <button className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700" type="button" onClick={() => startEdit(task)}>
                      <Edit3 className="h-4 w-4" />
                      Edit
                    </button>
                    <button className="inline-flex items-center gap-2 rounded-xl border border-rose-200 px-3 py-2 text-sm font-medium text-rose-700" type="button" onClick={() => void handleDelete(task.id)}>
                      <Trash2 className="h-4 w-4" />
                      Delete
                    </button>
                  </div>
                </div>
                <div className="mt-4 grid gap-2 text-xs text-slate-500 md:grid-cols-2">
                  <div>Start: {formatDate(task.start_date)}</div>
                  <div>End: {formatDate(task.end_date)}</div>
                  <div>Created: {formatDate(task.created_at)}</div>
                  <div>Updated: {formatDate(task.updated_at)}</div>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Navigate to="/summary" replace />} />
        <Route path="/summary" element={<SummaryPage />} />
        <Route path="/tasks" element={<Tasks />} />
      </Routes>
    </AppShell>
  );
}
