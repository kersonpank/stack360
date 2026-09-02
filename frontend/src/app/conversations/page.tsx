import { MessageSquareText } from "lucide-react";
import { EmptyState } from "@/components/ui/States";

export default function ConversationsPage() {
  return (
    <EmptyState
      title="Abra uma conversa pelo Stakeholder 360"
      message="A API atual expõe mensagens por conversation_id. Use a tela de stakeholder para selecionar uma conversa real."
      action={<MessageSquareText className="h-8 w-8 text-blue" />}
    />
  );
}
