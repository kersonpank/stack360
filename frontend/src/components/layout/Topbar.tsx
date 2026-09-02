"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Menu, RefreshCcw, Search, Settings, Users } from "lucide-react";

export function Topbar() {
  const router = useRouter();
  const [query, setQuery] = useState("");

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedQuery = query.trim();
    router.push(trimmedQuery ? `/stakeholders?q=${encodeURIComponent(trimmedQuery)}` : "/stakeholders");
  }

  return (
    <header className="sticky top-0 z-30 border-b-[4px] border-ink bg-paper px-4 py-4 shadow-[0_4px_0_0_#1a1a1a] sm:px-6 lg:px-8">
      <div className="flex items-center gap-3">
        <Link
          href="/"
          className="brutal-border-thin flex h-11 w-11 items-center justify-center bg-ink text-yellow md:hidden"
          aria-label="Abrir overview"
        >
          <Menu className="h-5 w-5" />
        </Link>

        <form onSubmit={submitSearch} className="relative max-w-3xl flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-ink" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="SEARCH PHONE, NAME, CONTACT_ID..."
            className="brutal-border-thin brutal-shadow-sm w-full bg-panel py-3 pl-11 pr-3 font-headline text-sm font-black uppercase tracking-widest placeholder:text-ink/45 focus-visible:brutal-focus"
          />
        </form>

        <Link
          href="/stakeholders"
          className="brutal-border-thin hidden h-11 w-11 items-center justify-center bg-panel transition-colors hover:bg-yellow focus-visible:brutal-focus sm:flex"
          aria-label="Stakeholders"
        >
          <Users className="h-5 w-5" />
        </Link>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="brutal-border-thin hidden h-11 w-11 items-center justify-center bg-panel transition-colors hover:bg-yellow focus-visible:brutal-focus sm:flex"
          aria-label="Recarregar"
        >
          <RefreshCcw className="h-5 w-5" />
        </button>
        <Link
          href="/settings"
          className="brutal-border-thin flex h-11 w-11 items-center justify-center bg-panel transition-colors hover:bg-yellow focus-visible:brutal-focus"
          aria-label="Settings"
        >
          <Settings className="h-5 w-5" />
        </Link>
      </div>
    </header>
  );
}
