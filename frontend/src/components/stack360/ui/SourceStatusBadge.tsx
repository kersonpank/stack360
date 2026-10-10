import { Badge } from "@/components/ui/Badge";

export function SourceStatusBadge({ status, feeding }: { status: string; feeding: boolean }) {
  if (feeding) return <Badge tone="yellow">Alimentando</Badge>;
  if (status === "active") return <Badge tone="blue">Ativa (parada)</Badge>;
  return <Badge tone="red">{status}</Badge>;
}
