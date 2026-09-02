"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Building2,
  Gauge,
  Lightbulb,
  MessageSquareText,
  Settings,
  Truck,
  Users,
} from "lucide-react";

const navItems = [
  { href: "/", label: "Overview", icon: Gauge },
  { href: "/stakeholders", label: "Stakeholders", icon: Users },
  { href: "/conversations", label: "Conversations", icon: MessageSquareText },
  { href: "/opportunities", label: "Opportunities", icon: Lightbulb },
  { href: "/drivers", label: "Drivers", icon: Truck },
  { href: "/companies", label: "Companies", icon: Building2 },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 hidden h-screen w-72 flex-col border-r-[4px] border-ink bg-ink p-5 text-paper md:flex">
      <Link href="/" className="mb-8 block">
        <div className="font-headline text-3xl font-black uppercase tracking-tight text-yellow">
          Intel-System
        </div>
        <div className="mt-1 font-headline text-xs font-bold uppercase tracking-[0.25em] text-paper/70">
          Stakeholder 360
        </div>
      </Link>

      <Link
        href="/stakeholders"
        className="brutal-border-thin brutal-shadow-sm mb-7 flex items-center justify-center gap-2 bg-yellow px-4 py-3 font-headline text-sm font-black uppercase tracking-widest text-ink transition-colors hover:bg-red hover:text-white focus-visible:brutal-focus"
      >
        <Users className="h-4 w-4" />
        New analysis
      </Link>

      <nav className="flex flex-1 flex-col gap-2">
        {navItems.map((item) => {
          const active =
            item.href === "/" ? pathname === "/" : pathname === item.href || pathname.startsWith(`${item.href}/`);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 border-2 px-4 py-3 font-headline text-sm font-black uppercase tracking-widest transition-colors focus-visible:brutal-focus ${
                active
                  ? "border-ink bg-yellow text-ink"
                  : "border-transparent text-paper hover:border-paper hover:bg-red hover:text-white"
              }`}
            >
              <Icon className="h-5 w-5" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t-2 border-paper/30 pt-4">
        <Link
          href="/settings"
          className={`flex items-center gap-3 border-2 px-4 py-3 font-headline text-sm font-black uppercase tracking-widest transition-colors focus-visible:brutal-focus ${
            pathname === "/settings"
              ? "border-ink bg-yellow text-ink"
              : "border-transparent text-paper hover:border-paper hover:bg-red hover:text-white"
          }`}
        >
          <Settings className="h-5 w-5" />
          Settings
        </Link>
      </div>
    </aside>
  );
}
