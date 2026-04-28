import { useState, useEffect } from "react";
import { Calendar, Clock, ChevronRight, ArrowLeft, Pencil, Download } from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/StatusBadge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { toast } from "sonner";

interface Session {
  id: string;
  date: string;
  startTime: string;
  endTime: string | null;
  durationMin: number;
  windowMin: number;
  status: string;
  // Computed after fetch
  present?: number;
  late?: number;
  absent?: number;
  avgAttention?: number;
}

interface Record {
  id: string;
  studentId: string;
  name: string;
  roll: string;
  entryTime: string | null;
  status: string;
}

export default function HistoryPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selected, setSelected] = useState<Session | null>(null);
  const [records, setRecords] = useState<Record[]>([]);
  const [loading, setLoading] = useState(false);

  // Fetch sessions on mount
  useEffect(() => {
    fetchSessions();
  }, []);

  const fetchSessions = async () => {
    try {
      const res = await fetch("/api/sessions");
      const data = await res.json();
      const sessionList = data.sessions || [];

      // Fetch summary for each session
      const enriched = await Promise.all(
        sessionList.map(async (s: Session) => {
          try {
            const sumRes = await fetch(`/api/sessions/${s.id}/summary`);
            const sum = await sumRes.json();
            const anaRes = await fetch(`/api/analytics/${s.id}`);
            const ana = await anaRes.json();
            return {
              ...s,
              present: sum.present || 0,
              late: sum.late || 0,
              absent: sum.absent || 0,
              avgAttention: ana.summary?.avgAttention || 0,
            };
          } catch {
            return { ...s, present: 0, late: 0, absent: 0, avgAttention: 0 };
          }
        })
      );

      setSessions(enriched);
    } catch {
      toast.error("Failed to load sessions");
    }
  };

  const selectSession = async (s: Session) => {
    setSelected(s);
    setLoading(true);
    try {
      const res = await fetch(`/api/sessions/${s.id}/records`);
      const data = await res.json();
      setRecords(data.records || []);
    } catch {
      toast.error("Failed to load records");
    } finally {
      setLoading(false);
    }
  };

  const updateRecord = async (recordId: string, status: string) => {
    try {
      await fetch(`/api/attendance/${recordId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      toast.success("Record updated");
      // Refresh
      if (selected) selectSession(selected);
    } catch {
      toast.error("Failed to update");
    }
  };

  const exportCsv = () => {
    if (!records.length) return;
    const header = "Name,Roll,Entry Time,Status\n";
    const body = records.map((r) => `${r.name},${r.roll},${r.entryTime || "N/A"},${r.status}`).join("\n");
    const blob = new Blob([header + body], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `session_${selected?.date}_${selected?.startTime}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Records exported");
  };

  if (selected) {
    return (
      <AppLayout title="Session Details" description={`${selected.date} • ${selected.startTime} – ${selected.endTime || "ongoing"}`}>
        <Button variant="ghost" size="sm" className="mb-4 gap-2" onClick={() => { setSelected(null); setRecords([]); }}>
          <ArrowLeft className="h-4 w-4" /> Back to history
        </Button>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { label: "Present", value: selected.present ?? 0, c: "text-success" },
            { label: "Late", value: selected.late ?? 0, c: "text-warning" },
            { label: "Absent", value: selected.absent ?? 0, c: "text-destructive" },
            { label: "Avg Attention", value: `${selected.avgAttention ?? 0}%`, c: "text-primary" },
          ].map((s) => (
            <Card key={s.label} className="p-4">
              <p className="text-xs text-muted-foreground">{s.label}</p>
              <p className={`mt-1 text-2xl font-semibold ${s.c}`}>{s.value}</p>
            </Card>
          ))}
        </div>

        <Card className="mt-4 overflow-hidden">
          <div className="flex items-center justify-between border-b p-4">
            <h3 className="text-sm font-semibold">Attendance Records</h3>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" className="gap-2" onClick={exportCsv}>
                <Download className="h-4 w-4" /> Export
              </Button>
            </div>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Roll No.</TableHead>
                <TableHead>Entry Time</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Override</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={5} className="py-10 text-center text-sm text-muted-foreground">
                    Loading records...
                  </TableCell>
                </TableRow>
              ) : records.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="py-10 text-center text-sm text-muted-foreground">
                    No attendance records available for this session.
                  </TableCell>
                </TableRow>
              ) : (
                records.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell className="font-medium">{r.name}</TableCell>
                    <TableCell className="text-muted-foreground">{r.roll}</TableCell>
                    <TableCell className="font-mono text-sm">{r.entryTime || "N/A"}</TableCell>
                    <TableCell><StatusBadge status={r.status as any} /></TableCell>
                    <TableCell className="text-right">
                      <Select value={r.status} onValueChange={(v) => updateRecord(r.id, v)}>
                        <SelectTrigger className="ml-auto h-8 w-32">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="present">Present</SelectItem>
                          <SelectItem value="late">Late</SelectItem>
                          <SelectItem value="absent">Absent</SelectItem>
                        </SelectContent>
                      </Select>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </Card>
      </AppLayout>
    );
  }

  return (
    <AppLayout title="History & Reports" description="Past class sessions and reports">
      <Card className="overflow-hidden">
        <div className="border-b p-4">
          <h3 className="text-sm font-semibold">Past Sessions ({sessions.length})</h3>
        </div>
        <div className="divide-y">
          {sessions.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-12 text-muted-foreground">
              <Calendar className="h-10 w-10 opacity-30" />
              <p className="text-sm font-medium">No past sessions yet</p>
              <p className="text-xs">Completed class sessions will appear here</p>
            </div>
          ) : (
            sessions.map((s) => (
              <button
                key={s.id}
                onClick={() => selectSession(s)}
                className="flex w-full items-center gap-4 px-4 py-3 text-left hover:bg-muted/40"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-soft text-primary">
                  <Calendar className="h-5 w-5" />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium">{s.date}</p>
                  <div className="mt-0.5 flex items-center gap-1 text-xs text-muted-foreground">
                    <Clock className="h-3 w-3" /> {s.startTime} – {s.endTime || "ongoing"} • {s.durationMin} min
                  </div>
                </div>
                <div className="hidden gap-3 sm:flex">
                  <div className="text-center">
                    <p className="text-xs text-muted-foreground">Present</p>
                    <p className="text-sm font-semibold text-success">{s.present}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-muted-foreground">Late</p>
                    <p className="text-sm font-semibold text-warning">{s.late}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-muted-foreground">Absent</p>
                    <p className="text-sm font-semibold text-destructive">{s.absent}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-muted-foreground">Attention</p>
                    <p className="text-sm font-semibold text-primary">{s.avgAttention}%</p>
                  </div>
                </div>
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              </button>
            ))
          )}
        </div>
      </Card>
    </AppLayout>
  );
}
