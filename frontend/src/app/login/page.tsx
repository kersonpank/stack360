"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Lock } from "lucide-react";
import { BrutalCard } from "@/components/ui/BrutalCard";
import { Button } from "@/components/ui/Button";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!response.ok) {
        const data = (await response.json().catch(() => null)) as { error?: { message?: string } } | null;
        setError(data?.error?.message ?? "Falha no login.");
        return;
      }
      const next = new URLSearchParams(window.location.search).get("next") || "/";
      router.replace(next);
      router.refresh();
    } catch {
      setError("Erro de rede ao tentar logar.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-ink p-5">
      <BrutalCard className="w-full max-w-sm">
        <div className="mb-6 flex items-center gap-2">
          <Lock className="h-6 w-6" />
          <h1 className="font-headline text-2xl font-black uppercase tracking-tight">Stack360</h1>
        </div>

        <form onSubmit={onSubmit} className="flex flex-col gap-4">
          <div>
            <label className="mb-1 block font-headline text-xs font-black uppercase tracking-widest text-ink/70">
              Usuário
            </label>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
              className="brutal-border-thin w-full border-ink bg-panel px-4 py-3 font-semibold outline-none focus-visible:brutal-focus"
            />
          </div>
          <div>
            <label className="mb-1 block font-headline text-xs font-black uppercase tracking-widest text-ink/70">
              Senha
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="brutal-border-thin w-full border-ink bg-panel px-4 py-3 font-semibold outline-none focus-visible:brutal-focus"
            />
          </div>

          {error ? (
            <div className="border-2 border-red bg-red/10 p-3 text-sm font-bold text-red">{error}</div>
          ) : null}

          <Button type="submit" disabled={loading} className="mt-2 w-full">
            {loading ? "Entrando..." : "Entrar"}
          </Button>
        </form>
      </BrutalCard>
    </div>
  );
}
