import { ReactNode } from "react";

type BrutalCardProps = {
  children: ReactNode;
  className?: string;
};

export function BrutalCard({ children, className = "" }: BrutalCardProps) {
  return <section className={`brutal-border brutal-shadow bg-panel p-5 ${className}`}>{children}</section>;
}
