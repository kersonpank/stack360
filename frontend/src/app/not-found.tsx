import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/States";

export default function NotFound() {
  return (
    <EmptyState
      title="Tela não encontrada"
      message="A rota solicitada não existe neste MVP."
      action={<Button href="/">Voltar ao overview</Button>}
    />
  );
}
