import { AlertTriangle, Inbox, Loader2 } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "./Button";

export function LoadingState({ label = "Carregando inteligência..." }: { label?: string }) {
  return (
    <div className="brutal-border brutal-shadow flex min-h-44 items-center justify-center gap-3 bg-panel p-6">
      <Loader2 className="h-6 w-6 animate-spin" />
      <span className="font-headline text-sm font-black uppercase tracking-widest">{label}</span>
    </div>
  );
}

export function ErrorState({
  title = "Falha ao carregar dados",
  message,
  onRetry,
}: {
  title?: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="brutal-border brutal-shadow bg-red p-5 text-white">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-1 h-6 w-6 flex-none" />
        <div>
          <h2 className="font-headline text-xl font-black uppercase">{title}</h2>
          <p className="mt-2 max-w-3xl text-sm font-bold leading-relaxed">{message}</p>
          {onRetry ? (
            <Button type="button" onClick={onRetry} variant="dark" className="mt-4">
              Tentar novamente
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export function EmptyState({
  title,
  message,
  action,
}: {
  title: string;
  message: string;
  action?: ReactNode;
}) {
  return (
    <div className="brutal-border brutal-shadow flex min-h-44 flex-col items-start justify-center bg-panel p-6">
      <Inbox className="mb-3 h-7 w-7" />
      <h2 className="font-headline text-xl font-black uppercase">{title}</h2>
      <p className="mt-2 max-w-2xl text-sm font-semibold text-ink/75">{message}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}
