import { useState, useEffect } from "react";
import { Lightbulb, Fan, Zap, User } from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { Card } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { useWebSocket } from "@/hooks/use-websocket";

export default function IoT() {
  const [auto, setAuto] = useState(true);
  const [activity, setActivity] = useState<Array<{ time: string; event: string }>>([]);

  // WebSocket for real-time IoT state
  const { data: wsData, connected } = useWebSocket(true);

  const iotState = wsData.iot;
  const personDetected = iotState.personDetected;
  const effectiveLights = auto ? personDetected : iotState.lights;
  const effectiveFans = auto ? personDetected : iotState.fans;

  // Fetch initial IoT status and activity log
  useEffect(() => {
    fetch("/api/iot/status")
      .then((r) => r.json())
      .then((d) => {
        setAuto(d.autoMode ?? true);
        setActivity(d.recentActivity || []);
      })
      .catch(() => {});
  }, []);

  // Refresh activity log periodically
  useEffect(() => {
    const interval = setInterval(() => {
      fetch("/api/iot/status")
        .then((r) => r.json())
        .then((d) => setActivity(d.recentActivity || []))
        .catch(() => {});
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const toggleAutoMode = async (enabled: boolean) => {
    setAuto(enabled);
    try {
      await fetch("/api/iot/auto-mode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      });
      toast.success(`Auto mode ${enabled ? "enabled" : "disabled"}`);
    } catch {
      toast.error("Failed to update auto mode");
    }
  };

  const toggle = async (device: string, val: boolean) => {
    if (auto) {
      toast.error("Disable Auto Mode to control manually");
      return;
    }
    try {
      const res = await fetch("/api/iot/control", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ device, state: val ? "ON" : "OFF" }),
      });
      if (res.ok) {
        toast.success(`${device === "lights" ? "Lights" : "Fans"} turned ${val ? "ON" : "OFF"}`);
      } else {
        const d = await res.json();
        toast.error(d.error || "Failed");
      }
    } catch {
      toast.error("Failed to control device");
    }
  };

  return (
    <AppLayout title="IoT Control" description="Manage classroom lights and fans">
      <Card className="p-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-soft text-primary">
              <Zap className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-semibold">Auto Mode</p>
              <p className="text-xs text-muted-foreground">
                Automatically toggles devices based on person detection
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant="outline" className={`gap-1.5 ${personDetected ? "border-green-500 text-green-600" : "border-red-400 text-red-500"}`}>
              <User className="h-3 w-3" />
              {personDetected ? "Person Detected" : "No Person"}
            </Badge>
            <Switch checked={auto} onCheckedChange={toggleAutoMode} />
          </div>
        </div>
      </Card>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card className="p-5">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className={`flex h-12 w-12 items-center justify-center rounded-lg ${effectiveLights ? "bg-warning-soft text-warning" : "bg-muted text-muted-foreground"}`}>
                <Lightbulb className="h-6 w-6" />
              </div>
              <div>
                <p className="font-semibold">Classroom Lights</p>
                <p className="text-xs text-muted-foreground">Ceiling lights × 4</p>
              </div>
            </div>
            <Badge className={effectiveLights ? "bg-success text-success-foreground" : "bg-muted text-muted-foreground"}>
              {effectiveLights ? "ON" : "OFF"}
            </Badge>
          </div>
          <div className="mt-5 flex items-center justify-between rounded-md border bg-muted/30 p-3">
            <Label htmlFor="lights-switch" className="text-sm">Manual Control</Label>
            <Switch
              id="lights-switch"
              checked={effectiveLights}
              disabled={auto}
              onCheckedChange={(v) => toggle("lights", v)}
            />
          </div>
        </Card>

        <Card className="p-5">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className={`flex h-12 w-12 items-center justify-center rounded-lg ${effectiveFans ? "bg-info/10 text-info" : "bg-muted text-muted-foreground"}`}>
                <Fan className={`h-6 w-6 ${effectiveFans ? "animate-spin" : ""}`} style={{ animationDuration: "3s" }} />
              </div>
              <div>
                <p className="font-semibold">Classroom Fans</p>
                <p className="text-xs text-muted-foreground">Ceiling fans × 2</p>
              </div>
            </div>
            <Badge className={effectiveFans ? "bg-success text-success-foreground" : "bg-muted text-muted-foreground"}>
              {effectiveFans ? "ON" : "OFF"}
            </Badge>
          </div>
          <div className="mt-5 flex items-center justify-between rounded-md border bg-muted/30 p-3">
            <Label htmlFor="fans-switch" className="text-sm">Manual Control</Label>
            <Switch
              id="fans-switch"
              checked={effectiveFans}
              disabled={auto}
              onCheckedChange={(v) => toggle("fans", v)}
            />
          </div>
        </Card>
      </div>

      <Card className="mt-4 p-5">
        <h3 className="text-sm font-semibold">Recent Activity</h3>
        <div className="mt-3 space-y-2 text-sm">
          {activity.length === 0 ? (
            <p className="py-4 text-center text-sm text-muted-foreground">No activity logged yet</p>
          ) : (
            activity.map((a, i) => (
              <div key={i} className="flex items-center gap-3 rounded-md border bg-card px-3 py-2">
                <span className="font-mono text-xs text-muted-foreground">{a.time}</span>
                <span>{a.event}</span>
              </div>
            ))
          )}
        </div>
      </Card>
    </AppLayout>
  );
}
