import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type BaseProps = {
  children: ReactNode;
  variant?: "primary" | "dark" | "danger" | "secondary";
  className?: string;
};

type LinkButtonProps = BaseProps & {
  href: string;
};

type NativeButtonProps = BaseProps & ButtonHTMLAttributes<HTMLButtonElement> & {
  href?: never;
};

const variants = {
  primary: "bg-yellow text-ink hover:bg-panel",
  dark: "bg-ink text-white hover:bg-blue",
  danger: "bg-red text-white hover:bg-ink",
  secondary: "bg-panel text-ink hover:bg-yellow",
};

export function Button(props: LinkButtonProps | NativeButtonProps) {
  const variant = props.variant ?? "primary";
  const className = `brutal-border-thin brutal-shadow-sm inline-flex items-center justify-center gap-2 px-4 py-2 font-headline text-sm font-black uppercase tracking-widest transition-colors focus-visible:brutal-focus ${variants[variant]} ${props.className ?? ""}`;

  if ("href" in props && props.href) {
    return (
      <Link href={props.href} className={className}>
        {props.children}
      </Link>
    );
  }

  const { children, className: originalClassName, variant: originalVariant, ...buttonProps } = props;
  void originalClassName;
  void originalVariant;
  return (
    <button {...buttonProps} className={className}>
      {children}
    </button>
  );
}
