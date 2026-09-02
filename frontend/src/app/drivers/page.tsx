import { Truck } from "lucide-react";
import { EmptyState } from "@/components/ui/States";

export default function DriversPage() {
  return (
    <EmptyState
      title="Drivers em preparação"
      message="Use a busca de stakeholders para localizar motoristas identificados. Esta área fica reservada para a visão operacional dedicada."
      action={<Truck className="h-8 w-8 text-blue" />}
    />
  );
}
