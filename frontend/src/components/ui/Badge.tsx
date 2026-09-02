import type { ReactNode } from "react";

type BadgeProps = {
  children: ReactNode;
  tone?: "default" | "yellow" | "red" | "blue" | "dark";
};

const tones = {
  default: "bg-muted text-ink",
  yellow: "bg-yellow text-ink",
  red: "bg-red text-white",
  blue: "bg-blue text-white",
  dark: "bg-ink text-white",
};

export function Badge({ children, tone = "default" }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center border-2 border-ink px-2 py-1 font-headline text-[11px] font-black uppercase tracking-widest ${tones[tone]}`}
    >
      {children}
    </span>
  );
}
