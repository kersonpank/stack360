import { Badge } from "@/components/ui/Badge";
import { formatDateTime } from "@/components/ui/format";
import type { UiMessage } from "@/lib/types";

export function MessageBubble({ message }: { message: UiMessage }) {
  const outbound = message.direction === "OUTBOUND";

  return (
    <article className={`flex ${outbound ? "justify-end" : "justify-start"}`}>
      <div
        className={`brutal-border-thin max-w-3xl p-4 ${
          outbound ? "bg-yellow text-ink" : "bg-panel text-ink"
        }`}
      >
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <Badge tone={outbound ? "dark" : "blue"}>{message.direction}</Badge>
          <Badge>{message.type}</Badge>
          {message.contactName ? <span className="text-xs font-bold uppercase">{message.contactName}</span> : null}
        </div>
        <p className="whitespace-pre-wrap break-words text-sm font-semibold leading-relaxed">{message.content}</p>
        <div className="mt-3 flex flex-wrap gap-3 border-t-2 border-ink pt-2 text-xs font-bold uppercase text-ink/65">
          <span>{formatDateTime(message.timestamp)}</span>
          {message.status ? <span>Status: {message.status}</span> : null}
          {message.source ? <span>Source: {message.source}</span> : null}
          {message.rawType ? <span>Raw: {message.rawType}</span> : null}
        </div>
      </div>
    </article>
  );
}
