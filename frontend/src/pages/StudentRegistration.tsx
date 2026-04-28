import { useState, useRef, useEffect } from "react";
import { Camera, Upload, Pencil, Trash2, RotateCcw, Check, User, CameraOff, X } from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { useWebSocket } from "@/hooks/use-websocket";

interface Student {
  id: string;
  name: string;
  roll: string;
  folder?: string;
  createdAt?: string;
}

export default function StudentRegistration() {
  const [name, setName] = useState("");
  const [roll, setRoll] = useState("");
  const [cameraActive, setCameraActive] = useState(false);
  
  const { data } = useWebSocket(cameraActive);
  const frame = data.frame;

  const [capturedUrl, setCapturedUrl] = useState<string | null>(null);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const [students, setStudents] = useState<Student[]>([]);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Fetch students on mount ────────────────────────────────────────────────
  useEffect(() => {
    fetchStudents();
  }, []);

  const fetchStudents = async () => {
    try {
      const res = await fetch("/api/students");
      const data = await res.json();
      setStudents(data.students || []);
    } catch (err) {
      console.error("Failed to fetch students:", err);
    }
  };

  // ── Start webcam ──────────────────────────────────────────────────────────
  const startCamera = async () => {
    setCameraError(null);
    setCapturedUrl(null);
    setCameraActive(true);
    try {
      await fetch("/api/camera/start", { method: "POST" });
    } catch (e) {
      console.error("Failed to start backend camera", e);
    }
  };

  // ── Stop webcam ───────────────────────────────────────────────────────────
  const stopCamera = () => {
    setCameraActive(false);
  };

  // ── Capture frame from live video ─────────────────────────────────────────
  const capturePhoto = () => {
    if (frame) {
      setCapturedUrl(`data:image/jpeg;base64,${frame}`);
      stopCamera();
      toast.success("Photo captured!");
    } else {
      toast.error("No camera frame available yet. Please wait a second.");
    }
  };

  // ── Upload photo from device ──────────────────────────────────────────────
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      toast.error("Please select an image file");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      setCapturedUrl(reader.result as string);
      stopCamera();
      toast.success("Photo uploaded!");
    };
    reader.readAsDataURL(file);
  };

  // ── Register student — POST to backend ─────────────────────────────────────
  const handleRegister = async () => {
    if (!name || !roll) {
      toast.error("Please fill all fields");
      return;
    }
    if (!capturedUrl) {
      toast.error("Please capture or upload a photo");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch("/api/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, roll, image: capturedUrl }),
      });
      const data = await res.json();

      if (res.ok) {
        toast.success(data.message || `${name} registered successfully`);
        setName("");
        setRoll("");
        setCapturedUrl(null);
        fetchStudents(); // Refresh list
      } else {
        toast.error(data.error || "Registration failed");
      }
    } catch (err) {
      toast.error("Failed to connect to server");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      const res = await fetch(`/api/students/${id}`, { method: "DELETE" });
      if (res.ok) {
        toast.success("Student removed");
        fetchStudents();
      } else {
        toast.error("Failed to delete student");
      }
    } catch {
      toast.error("Failed to connect to server");
    }
  };

  const handleRetry = () => {
    setCapturedUrl(null);
    startCamera();
  };

  // Stop camera if component unmounts
  useEffect(() => () => stopCamera(), []);

  // ── Camera preview area content ───────────────────────────────────────────
  const renderCameraArea = () => {
    if (cameraError) {
      return (
        <div className="flex flex-col items-center gap-2 text-destructive">
          <CameraOff className="h-10 w-10" />
          <p className="text-sm font-medium">Camera unavailable</p>
          <p className="max-w-[220px] text-center text-xs text-muted-foreground">{cameraError}</p>
          <Button size="sm" variant="outline" className="mt-1" onClick={startCamera}>
            Try again
          </Button>
        </div>
      );
    }

    if (capturedUrl) {
      return (
        <div className="relative h-full w-full">
          <img
            src={capturedUrl}
            alt="Captured"
            className="h-full w-full rounded-lg object-cover"
          />
          <div className="absolute bottom-2 left-1/2 -translate-x-1/2 rounded-full bg-success/90 px-3 py-1 text-xs font-semibold text-white flex items-center gap-1">
            <Check className="h-3 w-3" /> Ready to register
          </div>
        </div>
      );
    }

    if (cameraActive) {
      if (frame) {
        return (
          <img
            src={`data:image/jpeg;base64,${frame}`}
            alt="Live feed"
            className="h-full w-full rounded-lg object-cover"
          />
        );
      } else {
        return (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-2">
            <span className="animate-pulse font-medium">Connecting to camera...</span>
          </div>
        );
      }
    }

    return (
      <div className="flex flex-col items-center gap-2 text-muted-foreground">
        <Camera className="h-10 w-10 opacity-50" />
        <p className="text-sm font-medium">Camera preview</p>
        <p className="text-xs">Click "Start Camera" or upload a photo</p>
      </div>
    );
  };

  return (
    <AppLayout title="Student Registration" description="Add and manage registered students">

      {/* Hidden file input for uploads */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleFileUpload}
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* ── Left: Form ── */}
        <Card className="p-5">
          <h3 className="text-sm font-semibold">Student Details</h3>
          <div className="mt-4 space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="name">Student Name</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Aarav Sharma"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="roll">Roll Number</Label>
              <Input
                id="roll"
                value={roll}
                onChange={(e) => setRoll(e.target.value)}
                placeholder="e.g. CS-042"
              />
            </div>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                className="flex-1 gap-2"
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload className="h-4 w-4" /> Upload Photo
              </Button>

              {!cameraActive && !capturedUrl && (
                <Button onClick={startCamera} className="flex-1 gap-2">
                  <Camera className="h-4 w-4" /> Start Camera
                </Button>
              )}
              {cameraActive && (
                <Button onClick={capturePhoto} className="flex-1 gap-2 bg-green-600 hover:bg-green-700">
                  <Check className="h-4 w-4" /> Capture
                </Button>
              )}
              {capturedUrl && (
                <Button onClick={handleRetry} variant="outline" className="flex-1 gap-2">
                  <RotateCcw className="h-4 w-4" /> Retake
                </Button>
              )}
            </div>
            <Button onClick={handleRegister} className="w-full" disabled={loading}>
              {loading ? "Registering..." : "Register Student"}
            </Button>
          </div>
        </Card>

        {/* ── Right: Camera Preview ── */}
        <Card className="p-5">
          <h3 className="text-sm font-semibold">Camera Preview</h3>
          <div className="relative mt-4 flex aspect-video items-center justify-center overflow-hidden rounded-lg border-2 border-dashed bg-muted/40">
            {renderCameraArea()}
          </div>
          <div className="mt-3 flex items-center gap-2">
            {cameraActive && (
              <Button variant="outline" size="sm" onClick={stopCamera} className="gap-2 text-destructive">
                <X className="h-3.5 w-3.5" /> Stop Camera
              </Button>
            )}
            <p className="ml-auto self-center text-xs text-muted-foreground">
              {cameraActive ? "🔴 Live • 640×480" : capturedUrl ? "✓ Photo ready" : "No camera active"}
            </p>
          </div>
        </Card>
      </div>

      {/* ── Registered Students List ── */}
      <Card className="mt-4 overflow-hidden">
        <div className="flex items-center justify-between border-b p-4">
          <h3 className="text-sm font-semibold">Registered Students ({students.length})</h3>
        </div>
        <div className="divide-y">
          {students.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-10 text-muted-foreground">
              <User className="h-10 w-10 opacity-30" />
              <p className="text-sm font-medium">No students registered yet</p>
              <p className="text-xs">Register a student using the form above</p>
            </div>
          ) : (
            students.map((s) => (
              <div key={s.id} className="flex items-center gap-3 px-4 py-3 hover:bg-muted/40">
                <div className="flex h-10 w-10 items-center justify-center overflow-hidden rounded-full bg-primary-soft text-primary">
                  <User className="h-5 w-5" />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium">{s.name}</p>
                  <p className="text-xs text-muted-foreground">{s.roll}</p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-destructive hover:text-destructive"
                  onClick={() => handleDelete(s.id)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))
          )}
        </div>
      </Card>
    </AppLayout>
  );
}
