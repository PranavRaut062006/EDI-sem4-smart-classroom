import { useState, useEffect, useCallback } from "react";
import { Camera, Download, Search, CameraOff, Play, Square } from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import { useWebSocket } from "@/hooks/use-websocket";

type Status = "present" | "late" | "absent";

export default function Attendance() {
  const [q, setQ] = useState("");
  const [wsActive, setWsActive] = useState(false);

  const { data: wsData, connected, connect, disconnect } = useWebSocket(wsActive);

  const startMonitoring = async () => {
    try {
      await fetch("/api/camera/start", { method: "POST" });
      setWsActive(true);
      connect();
      toast.success("Camera started — monitoring attendance");
    } catch {
      toast.error("Failed to start camera");
    }
  };

  const stopMonitoring = () => {
    setWsActive(false);
    disconnect();
    fetch("/api/camera/stop", { method: "POST" }).catch(() => {});
  };

  useEffect(() => () => { disconnect(); }, [disconnect]);

  // Attendance roster from WebSocket
  const roster = wsData.vision.roster || [];

  const updateStatus = async (recordId: string, status: Status) => {
    try {
      await fetch(`/api/attendance/${recordId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      toast.success("Attendance updated");
    } catch {
      toast.error("Failed to update");
    }
  };

  const exportCsv = () => {
    const header = "Name,Roll,Time,Status,Attention,Phones\n";
    const body = roster.map((r: any) =>
      `${r.name},${r.roll},${r.entryTime},${r.status},${r.attentionPct}%,${r.phoneCount}`
    ).join("\n");
    const blob = new Blob([header + body], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `attendance_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Attendance exported");
  };

  const filtered = roster.filter(
    (r: any) =>
      r.name.toLowerCase().includes(q.toLowerCase()) ||
      r.roll.toLowerCase().includes(q.toLowerCase())
  );

  return (
    <AppLayout title="Attendance" description="Real-time face detection and attendance tracking">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* ── Live Camera Feed ── */}
        <Card className="p-5 lg:col-span-2">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold">Live Camera Feed</h3>
            <StatusBadge status={connected ? "active" : "ended"} />
          </div>

          {/* Camera viewport — shows backend-annotated frames */}
          <div className="relative mt-4 flex aspect-video items-center justify-center overflow-hidden rounded-lg bg-zinc-950">
            {wsData.frame ? (
              <img
                src={`data:image/jpeg;base64,${wsData.frame}`}
                alt="Live feed"
                className="h-full w-full object-contain"
              />
            ) : (
              <div className="flex flex-col items-center gap-3 text-zinc-400">
                {!connected ? (
                  <>
                    <Camera className="h-12 w-12 opacity-40" />
                    <p className="text-sm">Camera is off</p>
                    <p className="text-xs text-zinc-500">Click "Start Camera" to begin monitoring</p>
                  </>
                ) : (
                  <>
                    <CameraOff className="h-12 w-12" />
                    <p className="text-sm">Waiting for frames...</p>
                  </>
                )}
              </div>
            )}

            {/* REC badge */}
            {connected && wsData.frame && (
              <>
                <div className="absolute left-3 top-3 flex items-center gap-1.5 rounded-md bg-red-600/90 px-2 py-1 text-xs font-semibold text-white">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-white" />
                  REC
                </div>
                <div className="absolute bottom-3 left-3 rounded-md bg-black/60 px-2 py-1 text-xs text-green-400 backdrop-blur">
                  {wsData.vision.num_persons} person{wsData.vision.num_persons !== 1 ? "s" : ""} detected
                  {wsData.vision.num_phones > 0 && (
                    <span className="ml-2 text-red-400">
                      • {wsData.vision.num_phones} phone{wsData.vision.num_phones !== 1 ? "s" : ""}
                    </span>
                  )}
                </div>
                <div className="absolute bottom-3 right-3 rounded-md bg-black/60 px-2 py-1 text-xs text-cyan-400 backdrop-blur">
                  Engagement: {wsData.vision.average_engagement}%
                </div>
              </>
            )}
          </div>

          {/* Camera controls */}
          <div className="mt-3 flex items-center gap-2">
            {!connected ? (
              <Button size="sm" onClick={startMonitoring} className="gap-2">
                <Play className="h-3.5 w-3.5" /> Start Camera
              </Button>
            ) : (
              <Button size="sm" variant="destructive" onClick={stopMonitoring} className="gap-2">
                <Square className="h-3.5 w-3.5" /> Stop Camera
              </Button>
            )}
            <p className="ml-auto text-xs text-muted-foreground">
              {connected
                ? "🟢 Camera active — face recognition running"
                : "Camera stopped"}
            </p>
          </div>
        </Card>

        {/* ── Session Summary ── */}
        <Card className="p-5">
          <h3 className="text-sm font-semibold">Session Summary</h3>
          <div className="mt-4 space-y-3">
            {[
              { label: "Present", value: roster.filter((r: any) => r.status === "present").length, c: "text-success", b: "bg-success" },
              { label: "Late", value: roster.filter((r: any) => r.status === "late").length, c: "text-warning", b: "bg-warning" },
              { label: "Absent", value: roster.filter((r: any) => r.status === "absent").length, c: "text-destructive", b: "bg-destructive" },
            ].map((s) => {
              const pct = roster.length > 0 ? (s.value / roster.length) * 100 : 0;
              return (
                <div key={s.label}>
                  <div className="mb-1 flex items-center justify-between text-xs">
                    <span className={`font-medium ${s.c}`}>{s.label}</span>
                    <span className="text-muted-foreground">{s.value} / {roster.length}</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-muted">
                    <div className={`h-full ${s.b} transition-all`} style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>

          {/* Timer */}
          {wsData.timer.running && (
            <div className="mt-5 rounded-lg border bg-muted/30 p-3 text-center">
              <p className="text-xs text-muted-foreground">Session Time Remaining</p>
              <p className="mt-1 font-mono text-2xl font-semibold">
                {String(Math.floor(wsData.timer.remaining / 60)).padStart(2, "0")}:
                {String(wsData.timer.remaining % 60).padStart(2, "0")}
              </p>
            </div>
          )}
        </Card>
      </div>

      {/* ── Attendance Log Table ── */}
      <Card className="mt-4 overflow-hidden">
        <div className="flex flex-wrap items-center gap-2 border-b p-4">
          <h3 className="text-sm font-semibold">Attendance Log</h3>
          <div className="ml-auto flex flex-wrap items-center gap-2">
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search..."
                value={q}
                onChange={(e) => setQ(e.target.value)}
                className="h-9 w-48 pl-8"
              />
            </div>
            <Button variant="outline" size="sm" className="gap-2" onClick={exportCsv}>
              <Download className="h-4 w-4" /> Export CSV
            </Button>
          </div>
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Roll No.</TableHead>
              <TableHead>Entry Time</TableHead>
              <TableHead>Attention</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Override</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center text-sm text-muted-foreground">
                  {roster.length === 0
                    ? "No attendance records yet. Start a class session to begin tracking."
                    : "No matching records found."}
                </TableCell>
              </TableRow>
            ) : (
              filtered.map((r: any) => (
                <TableRow key={r.recordId}>
                  <TableCell className="font-medium">{r.name}</TableCell>
                  <TableCell className="text-muted-foreground">{r.roll}</TableCell>
                  <TableCell className="font-mono text-sm">{r.entryTime}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-muted">
                        <div
                          className={`h-full transition-all ${
                            r.attentionPct >= 70 ? "bg-success" : r.attentionPct >= 40 ? "bg-warning" : "bg-destructive"
                          }`}
                          style={{ width: `${r.attentionPct}%` }}
                        />
                      </div>
                      <span className="text-xs tabular-nums">{r.attentionPct}%</span>
                      {r.phoneCount > 0 && (
                        <span className="text-xs text-red-500">📱{r.phoneCount}</span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell><StatusBadge status={r.status as any} /></TableCell>
                  <TableCell className="text-right">
                    <Select value={r.status} onValueChange={(v) => updateStatus(r.recordId, v as Status)}>
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
