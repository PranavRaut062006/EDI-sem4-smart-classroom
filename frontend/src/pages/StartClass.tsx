import { useState, useEffect } from "react";
import { PlayCircle, StopCircle, Timer, Users } from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { StatusBadge } from "@/components/StatusBadge";
import { toast } from "sonner";
import { useWebSocket } from "@/hooks/use-websocket";

export default function StartClass() {
  const [duration, setDuration] = useState(60);
  const [windowMin, setWindowMin] = useState(10);
  const [active, setActive] = useState(false);
  const [loading, setLoading] = useState(false);

  // Connect WebSocket when session is active
  const { data: wsData, connected } = useWebSocket(active);

  // Sync active state from WebSocket timer
  useEffect(() => {
    if (wsData.timer.running && !active) {
      setActive(true);
    } else if (!wsData.timer.running && active && wsData.timer.remaining <= 0) {
      setActive(false);
      toast("Session ended");
    }
  }, [wsData.timer.running, wsData.timer.remaining]);

  const secondsLeft = active ? wsData.timer.remaining : 0;
  const mm = String(Math.floor(secondsLeft / 60)).padStart(2, "0");
  const ss = String(secondsLeft % 60).padStart(2, "0");

  const start = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/sessions/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ durationMin: duration, windowMin: windowMin }),
      });
      const data = await res.json();
      if (res.ok) {
        setActive(true);
        toast.success("Class session started");
      } else {
        toast.error(data.error || "Failed to start session");
      }
    } catch {
      toast.error("Failed to connect to server");
    } finally {
      setLoading(false);
    }
  };

  const stop = async () => {
    setLoading(true);
    try {
      await fetch("/api/sessions/stop", { method: "POST" });
      setActive(false);
      toast("Session ended manually");
    } catch {
      toast.error("Failed to stop session");
    } finally {
      setLoading(false);
    }
  };

  const counts = wsData.vision.counts || { present: 0, late: 0, absent: 0, total: 0 };

  return (
    <AppLayout title="Start Class" description="Configure and launch a new class session">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="p-5 lg:col-span-2">
          <h3 className="text-sm font-semibold">Session Configuration</h3>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="duration">Class Duration (minutes)</Label>
              <Input
                id="duration"
                type="number"
                min={1}
                value={duration}
                onChange={(e) => setDuration(Number(e.target.value))}
                disabled={active}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="window">Attendance Window (minutes)</Label>
              <Input
                id="window"
                type="number"
                min={1}
                value={windowMin}
                onChange={(e) => setWindowMin(Number(e.target.value))}
                disabled={active}
              />
              <p className="text-xs text-muted-foreground">Students arriving after this are marked late</p>
            </div>
          </div>
          <div className="mt-5 flex gap-2">
            {!active ? (
              <Button onClick={start} size="lg" className="gap-2" disabled={loading}>
                <PlayCircle className="h-5 w-5" /> {loading ? "Starting..." : "Start Session"}
              </Button>
            ) : (
              <Button onClick={stop} variant="destructive" size="lg" className="gap-2" disabled={loading}>
                <StopCircle className="h-5 w-5" /> End Session
              </Button>
            )}
          </div>
          {active && connected && (
            <p className="mt-3 text-xs text-muted-foreground">
              🟢 Connected to camera — monitoring attendance in real-time
            </p>
          )}
        </Card>

        <Card className="flex flex-col items-center justify-center p-5">
          <div className="flex items-center gap-2">
            <Timer className="h-4 w-4 text-muted-foreground" />
            <span className="text-xs font-medium text-muted-foreground">Time Remaining</span>
          </div>
          <p className="mt-3 font-mono text-5xl font-semibold tabular-nums tracking-tight">
            {mm}:{ss}
          </p>
          <div className="mt-3">
            <StatusBadge status={active ? "active" : "ended"} />
          </div>
        </Card>
      </div>

      <Card className="mt-4 p-5">
        <div className="flex items-center gap-2">
          <Users className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-sm font-semibold">Live Counters</h3>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { label: "Detected", value: active ? wsData.vision.num_persons : 0, color: "text-primary" },
            { label: "Present", value: active ? counts.present : 0, color: "text-success" },
            { label: "Late", value: active ? counts.late : 0, color: "text-warning" },
            { label: "Absent", value: active ? counts.absent : 0, color: "text-destructive" },
          ].map((c) => (
            <div key={c.label} className="rounded-lg border bg-card p-4">
              <p className="text-xs text-muted-foreground">{c.label}</p>
              <p className={`mt-1 text-2xl font-semibold ${c.color}`}>{c.value}</p>
            </div>
          ))}
        </div>
      </Card>
    </AppLayout>
  );
}
