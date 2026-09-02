import { Lightbulb } from "lucide-react";
import { EmptyState } from "@/components/ui/States";

export default function OpportunitiesPage() {
  return (
    <EmptyState
      title="Oportunidades globais ainda não disponíveis"
      message="O MVP já mostra oportunidades dentro do Stakeholder 360. A listagem global será ligada quando houver endpoint dedicado."
      action={<Lightbulb className="h-8 w-8 text-blue" />}
    />
  );
}
