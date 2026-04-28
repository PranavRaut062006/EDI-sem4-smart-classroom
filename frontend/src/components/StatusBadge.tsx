import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type Status = "present" | "late" | "absent" | "active" | "ended";

const styles: Record<Status, string> = {
  present: "bg-success-soft text-success border-success/20 hover:bg-success-soft",
  late: "bg-warning-soft text-warning border-warning/20 hover:bg-warning-soft",
  absent: "bg-destructive-soft text-destructive border-destructive/20 hover:bg-destructive-soft",
  active: "bg-primary-soft text-primary border-primary/20 hover:bg-primary-soft",
  ended: "bg-muted text-muted-foreground border-border hover:bg-muted",
};

const labels: Record<Status, string> = {
  present: "Present",
  late: "Late",
  absent: "Absent",
  active: "Active",
  ended: "Ended",
};

export function StatusBadge({ status, className }: { status: Status; className?: string }) {
  return (
    <Badge variant="outline" className={cn("font-medium", styles[status], className)}>
      {labels[status]}
    </Badge>
  );
}
