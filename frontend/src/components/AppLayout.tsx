import { ReactNode, useState, useEffect } from "react";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "./AppSidebar";
import { Badge } from "@/components/ui/badge";
import { Wifi, WifiOff } from "lucide-react";

interface AppLayoutProps {
  children: ReactNode;
  title: string;
  description?: string;
  actions?: ReactNode;
}

export function AppLayout({ children, title, description, actions }: AppLayoutProps) {
  const [backendOnline, setBackendOnline] = useState(false);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch("/api/health");
        setBackendOnline(res.ok);
      } catch {
        setBackendOnline(false);
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full bg-background">
        <AppSidebar />
        <div className="flex flex-1 flex-col">
          <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b bg-card/80 px-4 backdrop-blur">
            <SidebarTrigger />
            <div className="h-5 w-px bg-border" />
            <div className="flex flex-1 items-center justify-between">
              <div>
                <h1 className="text-sm font-semibold">{title}</h1>
                {description && (
                  <p className="text-xs text-muted-foreground">{description}</p>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Badge
                  variant="outline"
                  className={`gap-1.5 text-xs font-normal ${backendOnline ? "" : "border-red-400 text-red-500"}`}
                >
                  <span className="relative flex h-1.5 w-1.5">
                    <span className={`absolute inline-flex h-full w-full rounded-full ${backendOnline ? "bg-success" : "bg-red-500"} opacity-75`} />
                    <span className={`relative inline-flex h-1.5 w-1.5 rounded-full ${backendOnline ? "bg-success" : "bg-red-500"}`} />
                  </span>
                  {backendOnline ? "Server Online" : "Server Offline"}
                </Badge>
                <Badge variant="outline" className="gap-1.5 text-xs font-normal">
                  {backendOnline ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
                  Camera
                </Badge>
              </div>
            </div>
            {actions}
          </header>
          <main className="flex-1 p-4 md:p-6">
            <div className="mx-auto w-full max-w-7xl">{children}</div>
          </main>
        </div>
      </div>
    </SidebarProvider>
  );
}
