"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Copy, KeyRound, Plus, ShieldAlert } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { BrutalCard } from "@/components/ui/BrutalCard";
import { Button } from "@/components/ui/Button";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatDateTime } from "@/components/ui/format";
import {
  createApiKey,
  createSource,
  createWorkspace,
  listApiKeys,
  listSources,
  listWorkspaces,
  revokeApiKey,
} from "@/lib/stack360/adminApi";
import type { AdminApiKey, AdminSource, AdminWorkspace, CreatedApiKey } from "@/lib/stack360/types";

const SCOPE_OPTIONS = ["read", "ingest", "mcp", "admin"] as const;

export default function ApiKeysPage() {
  const [workspaces, setWorkspaces] = useState<AdminWorkspace[] | null>(null);
  const [workspaceId, setWorkspaceId] = useState<string>("");
  const [sources, setSources] = useState<AdminSource[]>([]);
  const [apiKeys, setApiKeys] = useState<AdminApiKey[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [createdKey, setCreatedKey] = useState<CreatedApiKey | null>(null);

  async function loadWorkspaces() {
    setLoading(true);
    setError(null);
    try {
      const items = await listWorkspaces();
      setWorkspaces(items);
      if (items.length > 0 && !workspaceId) setWorkspaceId(items[0].id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar workspaces.");
    } finally {
      setLoading(false);
    }
  }

  async function loadWorkspaceData(id: string) {
    if (!id) return;
    try {
      const [sourcesData, keysData] = await Promise.all([listSources(id), listApiKeys(id)]);
      setSources(sourcesData);
      setApiKeys(keysData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar dados do workspace.");
    }
  }

  useEffect(() => {
    void loadWorkspaces();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (workspaceId) void loadWorkspaceData(workspaceId);
  }, [workspaceId]);

  async function onCreateWorkspace(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const slug = String(form.get("slug") ?? "").trim();
    const name = String(form.get("name") ?? "").trim();
    if (!slug || !name) return;
    try {
      const w = await createWorkspace(slug, name);
      setWorkspaces((prev) => [...(prev ?? []), w]);
      setWorkspaceId(w.id);
      e.currentTarget.reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao criar workspace.");
    }
  }

  async function onCreateSource(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const key = String(form.get("key") ?? "").trim();
    const name = String(form.get("name") ?? "").trim();
    const sourceType = String(form.get("source_type") ?? "").trim();
    if (!key || !name || !sourceType) return;
    try {
      await createSource(workspaceId, key, name, sourceType);
      await loadWorkspaceData(workspaceId);
      e.currentTarget.reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao criar source.");
    }
  }

  async function onCreateApiKey(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const name = String(form.get("name") ?? "").trim();
    const sourceId = String(form.get("source_id") ?? "") || undefined;
    const scopes = SCOPE_OPTIONS.filter((s) => form.get(`scope_${s}`) === "on");
    if (!name || scopes.length === 0) return;
    try {
      const created = await createApiKey({ workspaceId, sourceId, name, scopes });
      setCreatedKey(created);
      await loadWorkspaceData(workspaceId);
      e.currentTarget.reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao criar API key.");
    }
  }

  async function onRevoke(id: string) {
    try {
      await revokeApiKey(id);
      await loadWorkspaceData(workspaceId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao revogar API key.");
    }
  }

  if (loading) return <LoadingState label="Carregando workspaces..." />;
  if (error && !workspaces) return <ErrorState message={error} onRetry={loadWorkspaces} />;

  return (
    <div>
      <div className="mb-6 border-b-[4px] border-ink pb-4">
        <p className="flex items-center gap-2 font-headline text-sm font-black uppercase tracking-[0.25em] text-blue">
          <KeyRound className="h-4 w-4" /> Gestão
        </p>
        <h1 className="mt-2 font-headline text-5xl font-black uppercase tracking-tight sm:text-6xl">API Keys</h1>
      </div>

      {error ? (
        <div className="mb-5 border-2 border-red bg-red/10 p-3 text-sm font-bold text-red">{error}</div>
      ) : null}

      {createdKey ? (
        <BrutalCard className="mb-6 border-yellow bg-yellow/20">
          <div className="flex items-start gap-3">
            <ShieldAlert className="h-6 w-6 flex-none text-red" />
            <div className="flex-1">
              <h3 className="font-headline text-sm font-black uppercase tracking-widest">
                Guarde esta chave agora — ela não será exibida de novo
              </h3>
              <div className="mt-2 flex items-center gap-2">
                <code className="brutal-border-thin flex-1 overflow-x-auto border-ink bg-panel p-2 text-sm font-bold">
                  {createdKey.plaintext}
                </code>
                <Button
                  type="button"
                  variant="dark"
                  onClick={() => navigator.clipboard.writeText(createdKey.plaintext)}
                >
                  <Copy className="h-4 w-4" /> Copiar
                </Button>
              </div>
              <Button type="button" variant="secondary" className="mt-3" onClick={() => setCreatedKey(null)}>
                Entendi, fechar
              </Button>
            </div>
          </div>
        </BrutalCard>
      ) : null}

      <section className="mb-7">
        <h2 className="mb-3 font-headline text-xl font-black uppercase">Workspace</h2>
        <BrutalCard>
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <select
              value={workspaceId}
              onChange={(e) => setWorkspaceId(e.target.value)}
              className="brutal-border-thin border-ink bg-panel px-3 py-2 font-semibold"
            >
              {(workspaces ?? []).map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name} ({w.slug})
                </option>
              ))}
            </select>
          </div>
          <form onSubmit={onCreateWorkspace} className="flex flex-wrap items-end gap-3">
            <div>
              <label className="mb-1 block text-xs font-bold uppercase text-ink/60">Slug</label>
              <input
                name="slug"
                required
                className="brutal-border-thin border-ink bg-panel px-3 py-2 font-semibold"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-bold uppercase text-ink/60">Nome</label>
              <input
                name="name"
                required
                className="brutal-border-thin border-ink bg-panel px-3 py-2 font-semibold"
              />
            </div>
            <Button type="submit" variant="secondary">
              <Plus className="h-4 w-4" /> Novo workspace
            </Button>
          </form>
        </BrutalCard>
      </section>

      {workspaceId ? (
        <>
          <section className="mb-7">
            <h2 className="mb-3 font-headline text-xl font-black uppercase">Sources</h2>
            <BrutalCard>
              <div className="mb-4 flex flex-col divide-y-2 divide-ink/10">
                {sources.length === 0 ? (
                  <p className="py-2 text-sm font-semibold text-ink/60">Nenhuma source neste workspace.</p>
                ) : (
                  sources.map((s) => (
                    <div key={s.id} className="flex items-center justify-between gap-2 py-2">
                      <div>
                        <span className="font-headline text-sm font-black uppercase">{s.name}</span>
                        <span className="ml-2 text-xs font-semibold text-ink/50">{s.key}</span>
                      </div>
                      <Badge tone="default">{s.source_type}</Badge>
                    </div>
                  ))
                )}
              </div>
              <form onSubmit={onCreateSource} className="flex flex-wrap items-end gap-3">
                <div>
                  <label className="mb-1 block text-xs font-bold uppercase text-ink/60">Key</label>
                  <input name="key" required className="brutal-border-thin border-ink bg-panel px-3 py-2 font-semibold" />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-bold uppercase text-ink/60">Nome</label>
                  <input name="name" required className="brutal-border-thin border-ink bg-panel px-3 py-2 font-semibold" />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-bold uppercase text-ink/60">Tipo</label>
                  <input
                    name="source_type"
                    required
                    placeholder="passthrough"
                    className="brutal-border-thin border-ink bg-panel px-3 py-2 font-semibold"
                  />
                </div>
                <Button type="submit" variant="secondary">
                  <Plus className="h-4 w-4" /> Nova source
                </Button>
              </form>
            </BrutalCard>
          </section>

          <section>
            <h2 className="mb-3 font-headline text-xl font-black uppercase">API Keys</h2>
            <BrutalCard>
              <div className="mb-5 flex flex-col divide-y-2 divide-ink/10">
                {apiKeys.length === 0 ? (
                  <p className="py-2 text-sm font-semibold text-ink/60">Nenhuma API key neste workspace.</p>
                ) : (
                  apiKeys.map((k) => (
                    <div key={k.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                      <div>
                        <span className="font-headline text-sm font-black uppercase">{k.name}</span>
                        <span className="ml-2 font-mono text-xs text-ink/50">{k.key_prefix}…</span>
                        <div className="mt-1 flex flex-wrap gap-1">
                          {k.scopes.map((s) => (
                            <Badge key={s} tone={s === "admin" ? "red" : "default"}>
                              {s}
                            </Badge>
                          ))}
                          {k.source_key ? <Badge tone="blue">{k.source_key}</Badge> : null}
                        </div>
                        <p className="mt-1 text-[11px] font-bold uppercase text-ink/50">
                          Criada em {formatDateTime(k.created_at)}
                          {k.last_used_at ? ` · Usada em ${formatDateTime(k.last_used_at)}` : " · Nunca usada"}
                        </p>
                      </div>
                      {k.status === "revoked" ? (
                        <Badge tone="red">Revogada</Badge>
                      ) : (
                        <Button type="button" variant="danger" onClick={() => onRevoke(k.id)}>
                          Revogar
                        </Button>
                      )}
                    </div>
                  ))
                )}
              </div>

              <form onSubmit={onCreateApiKey} className="flex flex-col gap-3">
                <div className="flex flex-wrap items-end gap-3">
                  <div>
                    <label className="mb-1 block text-xs font-bold uppercase text-ink/60">Nome</label>
                    <input name="name" required className="brutal-border-thin border-ink bg-panel px-3 py-2 font-semibold" />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-bold uppercase text-ink/60">
                      Source (obrigatório pra scope ingest)
                    </label>
                    <select name="source_id" className="brutal-border-thin border-ink bg-panel px-3 py-2 font-semibold">
                      <option value="">— nenhuma —</option>
                      {sources.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="flex flex-wrap gap-4">
                  {SCOPE_OPTIONS.map((scope) => (
                    <label key={scope} className="flex items-center gap-2 text-sm font-bold uppercase">
                      <input type="checkbox" name={`scope_${scope}`} />
                      {scope}
                    </label>
                  ))}
                </div>
                <Button type="submit" className="w-fit">
                  <Plus className="h-4 w-4" /> Gerar API key
                </Button>
              </form>
            </BrutalCard>
          </section>
        </>
      ) : null}
    </div>
  );
}
