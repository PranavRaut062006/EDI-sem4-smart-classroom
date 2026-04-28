/**
 * Smart Classroom AI — Central API Client
 *
 * All backend communication goes through this file.
 * Set VITE_API_URL in your .env to point at the Flask backend.
 * Default: http://localhost:5000 (Flask dev server)
 */

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:5000";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err?.error ?? `API error ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ── Health ─────────────────────────────────────────────────────────────────────
export const checkHealth = () => apiFetch<{ status: string }>("/api/health");

// ── Students ──────────────────────────────────────────────────────────────────
export interface Student {
  id: string;
  name: string;
  roll: string;
  imagePath: string | null;
  createdAt: string;
}

export const fetchStudents = () =>
  apiFetch<{ students: Student[] }>("/api/students/");

export const deleteStudent = (id: string) =>
  apiFetch<{ message: string }>(`/api/students/${id}`, { method: "DELETE" });

export const updateStudent = (id: string, data: { name?: string; roll?: string }) =>
  apiFetch<{ message: string; student: Student }>(`/api/students/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });

// ── Sessions ──────────────────────────────────────────────────────────────────
export interface Session {
  id: string;
  date: string;
  startTime: string;
  endTime: string | null;
  durationMin: number;
  windowMin: number;
  status: "active" | "ended";
}

export const fetchSessions = () =>
  apiFetch<{ sessions: Session[] }>("/api/attendance/sessions");

export const fetchActiveSession = () =>
  apiFetch<{ session: Session | null }>("/api/attendance/sessions/active");

export const startSession = (durationMin: number, windowMin: number) =>
  apiFetch<{ message: string; sessionId: string }>("/api/attendance/sessions", {
    method: "POST",
    body: JSON.stringify({ durationMin, windowMin }),
  });

export const endSession = (sessionId: string) =>
  apiFetch<{ message: string }>(`/api/attendance/sessions/${sessionId}/end`, {
    method: "PUT",
  });

// ── Attendance Records ────────────────────────────────────────────────────────
export interface AttendanceRecord {
  id: string;
  studentId: string;
  name: string;
  roll: string;
  entryTime: string | null;
  status: "present" | "late" | "absent";
}

export const fetchAttendanceRecords = (sessionId: string) =>
  apiFetch<{ records: AttendanceRecord[] }>(
    `/api/attendance/sessions/${sessionId}/records`
  );

export const updateAttendanceRecord = (
  recordId: string,
  status: "present" | "late" | "absent"
) =>
  apiFetch<{ message: string }>(`/api/attendance/records/${recordId}`, {
    method: "PUT",
    body: JSON.stringify({ status }),
  });

export const fetchSessionSummary = (sessionId: string) =>
  apiFetch<{ present: number; late: number; absent: number; total: number }>(
    `/api/attendance/sessions/${sessionId}/summary`
  );

// ── Analytics ─────────────────────────────────────────────────────────────────
export interface AnalyticsEntry {
  studentId: string;
  name: string;
  roll: string;
  attentionPct: number;
  phoneCount: number;
}

export interface AnalyticsSummary {
  avgAttention: number;
  totalPhoneEvents: number;
  lowAttentionCount: number;
  trackedCount: number;
}

export const fetchAnalytics = (sessionId: string) =>
  apiFetch<{ analytics: AnalyticsEntry[]; summary: AnalyticsSummary }>(
    `/api/analytics/sessions/${sessionId}`
  );

// ── IoT ───────────────────────────────────────────────────────────────────────
export interface IoTStatus {
  lights: boolean;
  fans: boolean;
  personDetected: boolean;
  autoMode: boolean;
  gpioEnabled: boolean;
  recentActivity: { time: string; event: string }[];
}

export const fetchIoTStatus = () =>
  apiFetch<IoTStatus>("/api/iot/status");

export const controlDevice = (device: "lights" | "fans", state: "ON" | "OFF") =>
  apiFetch<{ message: string }>("/api/iot/control", {
    method: "POST",
    body: JSON.stringify({ device, state }),
  });
