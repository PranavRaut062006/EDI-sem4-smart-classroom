import { useState, useEffect } from "react";
import { Brain, AlertTriangle, Smartphone, TrendingDown } from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { Card } from "@/components/ui/card";
import { StatCard } from "@/components/StatCard";
import { Button } from "@/components/ui/button";
import { useWebSocket } from "@/hooks/use-websocket";

interface AnalyticsItem {
  studentId: string;
  name: string;
  roll: string;
  attentionPct: number;
  phoneCount: number;
}

interface AnalyticsSummary {
  avgAttention: number;
  totalPhoneEvents: number;
  lowAttentionCount: number;
  trackedCount: number;
}

const engagementOf = (a: number) => {
  if (a >= 75) return { label: "High", c: "text-success", b: "bg-success" };
  if (a >= 50) return { label: "Medium", c: "text-warning", b: "bg-warning" };
  return { label: "Low", c: "text-destructive", b: "bg-destructive" };
};

export default function Analytics() {
  const [data, setData] = useState<AnalyticsItem[]>([]);
  const [summary, setSummary] = useState<AnalyticsSummary>({
    avgAttention: 0, totalPhoneEvents: 0, lowAttentionCount: 0, trackedCount: 0,
  });
  const [sessions, setSessions] = useState<any[]>([]);
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const [liveMode, setLiveMode] = useState(true);

  // WebSocket for live data
  const { data: wsData, connected } = useWebSocket(liveMode);

  // Fetch past sessions for dropdown
  useEffect(() => {
    fetch("/api/sessions")
      .then((r) => r.json())
      .then((d) => setSessions(d.sessions || []))
      .catch(() => {});
  }, []);

  // Load analytics from a past session
  const loadSessionAnalytics = async (sessionId: string) => {
    setLiveMode(false);
    setSelectedSession(sessionId);
    try {
      const res = await fetch(`/api/analytics/${sessionId}`);
      const d = await res.json();
      setData(d.analytics || []);
      setSummary(d.summary || { avgAttention: 0, totalPhoneEvents: 0, lowAttentionCount: 0, trackedCount: 0 });
    } catch {
      setData([]);
    }
  };

  // Compute live analytics from WebSocket roster
  const liveRoster = wsData.vision.roster || [];
  const liveData: AnalyticsItem[] = liveRoster.map((r: any) => ({
    studentId: r.studentId,
    name: r.name,
    roll: r.roll,
    attentionPct: r.attentionPct,
    phoneCount: r.phoneCount,
  }));
  const liveSummary: AnalyticsSummary = {
    avgAttention: liveData.length > 0 ? Math.round(liveData.reduce((s, d) => s + d.attentionPct, 0) / liveData.length) : 0,
    totalPhoneEvents: liveData.reduce((s, d) => s + d.phoneCount, 0),
    lowAttentionCount: liveData.filter((d) => d.attentionPct < 50).length,
    trackedCount: liveData.length,
  };

  const displayData = liveMode ? liveData : data;
  const displaySummary = liveMode ? liveSummary : summary;
  const low = displayData.filter((d) => d.attentionPct < 50);

  return (
    <AppLayout title="Attention Analytics" description="Post-class engagement insights">
      {/* Mode Toggle */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Button
          variant={liveMode ? "default" : "outline"}
          size="sm"
          onClick={() => { setLiveMode(true); setSelectedSession(null); }}
        >
          🔴 Live
        </Button>
        {sessions.filter(s => s.status === "ended").map((s) => (
          <Button
            key={s.id}
            variant={selectedSession === s.id ? "default" : "outline"}
            size="sm"
            onClick={() => loadSessionAnalytics(s.id)}
          >
            {s.date} {s.startTime}
          </Button>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Avg Attention"
          value={`${displaySummary.avgAttention}%`}
          icon={Brain}
          tone="info"
        />
        <StatCard
          label="Low Attention"
          value={displaySummary.lowAttentionCount}
          icon={TrendingDown}
          tone="destructive"
        />
        <StatCard
          label="Phone Detections"
          value={displaySummary.totalPhoneEvents}
          icon={Smartphone}
          tone="warning"
        />
        <StatCard
          label="Total Tracked"
          value={displaySummary.trackedCount}
          icon={AlertTriangle}
          tone="default"
        />
      </div>

      <Card className="mt-4 p-5">
        <h3 className="text-sm font-semibold">Per-Student Attention</h3>
        <p className="text-xs text-muted-foreground">Attentive when facing forward; warning if phone detected</p>
        <div className="mt-5 space-y-4">
          {displayData.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-8 text-muted-foreground">
              <Brain className="h-10 w-10 opacity-30" />
              <p className="text-sm font-medium">No analytics data available</p>
              <p className="text-xs">
                {liveMode
                  ? "Start a class session to see live attention data"
                  : "No data for this session"}
              </p>
            </div>
          ) : (
            displayData.map((s) => {
              const e = engagementOf(s.attentionPct);
              return (
                <div key={s.studentId || s.roll}>
                  <div className="mb-1.5 flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{s.name}</span>
                      <span className="text-xs text-muted-foreground">{s.roll}</span>
                      {s.phoneCount > 0 && (
                        <span className="inline-flex items-center gap-1 rounded-md bg-warning-soft px-1.5 py-0.5 text-xs font-medium text-warning">
                          <Smartphone className="h-3 w-3" /> {s.phoneCount}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`text-xs font-medium ${e.c}`}>{e.label}</span>
                      <span className="font-mono text-sm tabular-nums">{s.attentionPct}%</span>
                    </div>
                  </div>
                  <div className="h-2.5 overflow-hidden rounded-full bg-muted">
                    <div className={`h-full ${e.b} transition-all`} style={{ width: `${s.attentionPct}%` }} />
                  </div>
                </div>
              );
            })
          )}
        </div>
      </Card>

      <Card className="mt-4 p-5">
        <div className="flex items-center gap-2">
          <TrendingDown className="h-4 w-4 text-destructive" />
          <h3 className="text-sm font-semibold">Low Attention Students</h3>
        </div>
        <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
          {low.length === 0 ? (
            <p className="text-sm text-muted-foreground">No low-attention students detected</p>
          ) : (
            low.map((s) => (
              <div key={s.studentId || s.roll} className="rounded-md border border-destructive/20 bg-destructive-soft p-3">
                <p className="text-sm font-medium text-destructive">{s.name}</p>
                <p className="text-xs text-destructive/80">{s.roll} • {s.attentionPct}% attention</p>
              </div>
            ))
          )}
        </div>
      </Card>
    </AppLayout>
  );
}
