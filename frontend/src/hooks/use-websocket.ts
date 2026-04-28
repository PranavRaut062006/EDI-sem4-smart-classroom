import { useState, useEffect, useRef, useCallback } from "react";

interface VisionData {
  num_persons: number;
  num_phones: number;
  average_engagement: number;
  students: Array<{
    name: string;
    phone: boolean;
    attention: number;
    recognized: boolean;
  }>;
  roster: Array<{
    name: string;
    roll: string;
    status: string;
    entryTime: string;
    attentionPct: number;
    phoneCount: number;
    recordId: string;
    studentId: string;
  }>;
  counts: {
    present: number;
    late: number;
    absent: number;
    total: number;
  };
}

interface TimerData {
  running: boolean;
  duration: number;
  remaining: number;
  sessionId: string | null;
}

interface IoTData {
  lights: boolean;
  fans: boolean;
  autoMode: boolean;
  personDetected: boolean;
}

export interface WSPayload {
  frame: string | null;
  vision: VisionData;
  timer: TimerData;
  iot: IoTData;
}

const defaultPayload: WSPayload = {
  frame: null,
  vision: {
    num_persons: 0,
    num_phones: 0,
    average_engagement: 0,
    students: [],
    roster: [],
    counts: { present: 0, late: 0, absent: 0, total: 0 },
  },
  timer: { running: false, duration: 0, remaining: 0, sessionId: null },
  iot: { lights: false, fans: false, autoMode: true, personDetected: false },
};

export function useWebSocket(autoConnect: boolean = false) {
  const [data, setData] = useState<WSPayload>(defaultPayload);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      console.log("WebSocket connected");
    };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as WSPayload;
        setData(payload);
      } catch (e) {
        console.error("WS parse error:", e);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      console.log("WebSocket disconnected");
      // Auto-reconnect after 2s
      reconnectTimerRef.current = setTimeout(() => {
        if (autoConnect) connect();
      }, 2000);
    };

    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
      ws.close();
    };
  }, [autoConnect]);

  const disconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnected(false);
    setData(defaultPayload);
  }, []);

  useEffect(() => {
    if (autoConnect) {
      connect();
    }
    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  return { data, connected, connect, disconnect };
}
