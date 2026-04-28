import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Users, Activity, CheckCircle2, Clock, XCircle, UserPlus, PlayCircle, AlertTriangle, Smartphone } from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { StatCard } from "@/components/StatCard";
import { StatusBadge } from "@/components/StatusBadge";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useWebSocket } from "@/hooks/use-websocket";

export default function Dashboard() {
  const navigate = useNavigate();
  const [totalStudents, setTotalStudents] = useState(0);

  // Connect WebSocket for live data
  const { data: wsData, connected } = useWebSocket(true);

  useEffect(() => {
    fetch("/api/students")
      .then((r) => r.json())
      .then((d) => setTotalStudents((d.students || []).length))
      .catch(() => {});
  }, []);

  const timer = wsData.timer;
  const counts = wsData.vision.counts || { present: 0, late: 0, absent: 0, total: 0 };
  const roster = wsData.vision.roster || [];
  const sessionActive = timer.running;

  // Phone alerts from current detection
  const phoneAlerts = (wsData.vision.students || []).filter((s: any) => s.phone);

  return (
    <AppLayout title="Dashboard" description="Overview of today's classroom activity">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total Students" value={totalStudents} icon={Users} tone="info" hint="Registered" />
        <StatCard
          label="Session Status"
          value={sessionActive ? "Active" : "Idle"}
          icon={Activity}
          tone={sessionActive ? "success" : "default"}
          hint={sessionActive ? `${Math.floor(timer.remaining / 60)}m remaining` : "No active session"}
        />
        <StatCard label="Present" value={counts.present} icon={CheckCircle2} tone="success" />
        <StatCard label="Late" value={counts.late} icon={Clock} tone="warning" />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Absent" value={counts.absent} icon={XCircle} tone="destructive" />
        <Card className="p-5 sm:col-span-2 lg:col-span-3">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold">Quick Actions</h3>
              <p className="text-xs text-muted-foreground">Get started with common tasks</p>
            </div>
            {connected && (
              <span className="text-xs text-green-600">🟢 Backend Connected</span>
            )}
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button onClick={() => navigate("/students")} className="gap-2">
              <UserPlus className="h-4 w-4" /> Register Student
            </Button>
            <Button onClick={() => navigate("/start-class")} variant="secondary" className="gap-2">
              <PlayCircle className="h-4 w-4" /> Start New Class
            </Button>
            {sessionActive && (
              <Button onClick={() => navigate("/attendance")} variant="outline" className="gap-2">
                <CheckCircle2 className="h-4 w-4" /> View Attendance
              </Button>
            )}
          </div>
        </Card>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="p-5 lg:col-span-2">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold">Live Attendance</h3>
            <Button variant="ghost" size="sm" onClick={() => navigate("/attendance")}>
              View all
            </Button>
          </div>
          <div className="mt-4 space-y-2">
            {roster.length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-6 text-muted-foreground">
                <CheckCircle2 className="h-8 w-8 opacity-30" />
                <p className="text-sm">No attendance records yet</p>
                <p className="text-xs">Start a class session to track attendance</p>
              </div>
            ) : (
              roster.slice(0, 6).map((r: any) => (
                <div key={r.recordId} className="flex items-center justify-between rounded-md border px-3 py-2">
                  <div className="flex items-center gap-2">
                    <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary-soft text-primary text-xs font-medium">
                      {r.name.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <p className="text-sm font-medium">{r.name}</p>
                      <p className="text-xs text-muted-foreground">{r.roll} • {r.entryTime}</p>
                    </div>
                  </div>
                  <StatusBadge status={r.status as any} />
                </div>
              ))
            )}
          </div>
        </Card>

        <Card className="p-5">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-warning" />
            <h3 className="text-sm font-semibold">Phone Detection Alerts</h3>
          </div>
          <div className="mt-4 space-y-2">
            {phoneAlerts.length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-6 text-muted-foreground">
                <Smartphone className="h-8 w-8 opacity-30" />
                <p className="text-sm">No phone alerts</p>
              </div>
            ) : (
              phoneAlerts.map((a: any, i: number) => (
                <div key={i} className="flex items-center gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm dark:border-red-900 dark:bg-red-950">
                  <Smartphone className="h-4 w-4 text-red-500" />
                  <span className="font-medium text-red-700 dark:text-red-300">{a.name}</span>
                  <span className="text-xs text-red-500">Phone detected</span>
                </div>
              ))
            )}
            <p className="pt-1 text-xs text-muted-foreground">
              {phoneAlerts.length} alert{phoneAlerts.length !== 1 ? "s" : ""} right now
            </p>
          </div>
        </Card>
      </div>

      {/* IoT Status Preview */}
      <Card className="mt-4 p-5">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold">IoT Status</h3>
          <Button variant="ghost" size="sm" onClick={() => navigate("/iot")}>
            Manage
          </Button>
        </div>
        <div className="mt-3 grid grid-cols-3 gap-3">
          <div className="rounded-lg border p-3 text-center">
            <p className="text-xs text-muted-foreground">Person</p>
            <p className={`mt-1 text-lg font-semibold ${wsData.iot.personDetected ? "text-green-600" : "text-red-500"}`}>
              {wsData.iot.personDetected ? "Yes" : "No"}
            </p>
          </div>
          <div className="rounded-lg border p-3 text-center">
            <p className="text-xs text-muted-foreground">Lights</p>
            <p className={`mt-1 text-lg font-semibold ${wsData.iot.lights ? "text-yellow-500" : "text-gray-400"}`}>
              {wsData.iot.lights ? "ON" : "OFF"}
            </p>
          </div>
          <div className="rounded-lg border p-3 text-center">
            <p className="text-xs text-muted-foreground">Fans</p>
            <p className={`mt-1 text-lg font-semibold ${wsData.iot.fans ? "text-blue-500" : "text-gray-400"}`}>
              {wsData.iot.fans ? "ON" : "OFF"}
            </p>
          </div>
        </div>
      </Card>
    </AppLayout>
  );
}
