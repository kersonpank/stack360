import { Building2 } from "lucide-react";
import { EmptyState } from "@/components/ui/States";

export default function CompaniesPage() {
  return (
    <EmptyState
      title="Companies em preparação"
      message="Empresas aparecem como dados pendentes e tags no Stakeholder 360 até existir endpoint de listagem global."
      action={<Building2 className="h-8 w-8 text-blue" />}
    />
  );
}
