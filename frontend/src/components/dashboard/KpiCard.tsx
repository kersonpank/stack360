import type { LucideIcon } from "lucide-react";
import { formatNumber } from "@/components/ui/format";

type KpiCardProps = {
  label: string;
  value: number;
  icon: LucideIcon;
  tone?: "paper" | "yellow" | "red" | "dark";
  footer: string;
};

const tones = {
  paper: "bg-panel text-ink",
  yellow: "bg-yellow text-ink",
  red: "bg-red text-white",
  dark: "bg-ink text-white",
};

export function KpiCard({ label, value, icon: Icon, tone = "paper", footer }: KpiCardProps) {
  const borderTone = tone === "red" || tone === "dark" ? "border-white/80" : "border-ink";

  return (
    <article className={`brutal-border brutal-shadow p-5 ${tones[tone]}`}>
      <div className="mb-5 flex items-start justify-between gap-4">
        <h3 className="whitespace-pre-line font-headline text-sm font-black uppercase tracking-widest">
          {label}
        </h3>
        <Icon className="h-7 w-7 flex-none" />
      </div>
      <div className="font-headline text-5xl font-black tracking-tight sm:text-6xl">{formatNumber(value)}</div>
      <div className={`mt-5 border-t-2 pt-3 font-headline text-xs font-black uppercase tracking-widest ${borderTone}`}>
        {footer}
      </div>
    </article>
  );
}
