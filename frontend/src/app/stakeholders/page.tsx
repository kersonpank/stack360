"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { ListFilter, RotateCcw, Search, SlidersHorizontal, X } from "lucide-react";
import { StakeholderResults } from "@/components/stakeholders/StakeholderResults";
import { Button } from "@/components/ui/Button";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { listStakeholders, type StakeholderListParams } from "@/lib/api";
import type { UiStakeholderListResponse } from "@/lib/types";

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];
const TYPE_OPTIONS = ["unknown", "motorista", "cliente", "grupo", "lead"];
const STATUS_OPTIONS = ["active", "inactive", "pending", "blocked"];
const TAG_OPTIONS = ["whatsapp", "Motorista", "Cliente", "Lead", "Grupo", "Operacao", "Embarcador"];
const SORT_OPTIONS: Array<{ value: NonNullable<StakeholderListParams["sort"]>; label: string }> = [
  { value: "last_interaction", label: "Ultimo contato" },
  { value: "messages", label: "Mais mensagens" },
  { value: "opportunity", label: "Oportunidade" },
  { value: "risk", label: "Risco" },
  { value: "name", label: "Nome" },
  { value: "created", label: "Criacao" },
];

const emptyResponse: UiStakeholderListResponse = {
  total: 0,
  page: 1,
  pageSize: 25,
  items: [],
};

export default function StakeholdersPage() {
  const [query, setQuery] = useState("");
  const [searchText, setSearchText] = useState("");
  const [relationshipType, setRelationshipType] = useState("");
  const [status, setStatus] = useState("");
  const [tag, setTag] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [sort, setSort] = useState<NonNullable<StakeholderListParams["sort"]>>("last_interaction");
  const [order, setOrder] = useState<NonNullable<StakeholderListParams["order"]>>("desc");
  const [data, setData] = useState<UiStakeholderListResponse>(emptyResponse);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const params = useMemo<StakeholderListParams>(
    () => ({
      page,
      pageSize,
      q: query.trim() || undefined,
      relationshipType: relationshipType || undefined,
      status: status || undefined,
      tag: tag || undefined,
      sort,
      order,
    }),
    [order, page, pageSize, query, relationshipType, sort, status, tag],
  );

  const activeFilters = [
    query.trim() ? { key: "q", label: `Busca: ${query.trim()}` } : null,
    relationshipType ? { key: "relationshipType", label: `Tipo: ${relationshipType}` } : null,
    status ? { key: "status", label: `Status: ${status}` } : null,
    tag ? { key: "tag", label: `Tag: ${tag}` } : null,
  ].filter(Boolean) as Array<{ key: string; label: string }>;

  const sortLabel = SORT_OPTIONS.find((option) => option.value === sort)?.label ?? "Ultimo contato";

  const updateUrl = useCallback((next: StakeholderListParams) => {
    const searchParams = new URLSearchParams();
    if (next.q) searchParams.set("q", next.q);
    if (next.relationshipType) searchParams.set("type", next.relationshipType);
    if (next.status) searchParams.set("status", next.status);
    if (next.tag) searchParams.set("tag", next.tag);
    if (next.page && next.page > 1) searchParams.set("page", String(next.page));
    if (next.pageSize && next.pageSize !== 25) searchParams.set("pageSize", String(next.pageSize));
    if (next.sort && next.sort !== "last_interaction") searchParams.set("sort", next.sort);
    if (next.order && next.order !== "desc") searchParams.set("order", next.order);
    const suffix = searchParams.toString();
    window.history.replaceState(null, "", suffix ? `/stakeholders?${suffix}` : "/stakeholders");
  }, []);

  const loadStakeholders = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await listStakeholders(params);
      setData(response);
      updateUrl(params);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro desconhecido ao carregar stakeholders.");
      setData(emptyResponse);
    } finally {
      setLoading(false);
    }
  }, [params, updateUrl]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setQuery(searchText.trim());
    setPage(1);
  }

  function resetFilters() {
    setQuery("");
    setSearchText("");
    setRelationshipType("");
    setStatus("");
    setTag("");
    setPage(1);
    setPageSize(25);
    setSort("last_interaction");
    setOrder("desc");
  }

  function clearFilter(key: string) {
    if (key === "q") {
      setQuery("");
      setSearchText("");
    }
    if (key === "relationshipType") setRelationshipType("");
    if (key === "status") setStatus("");
    if (key === "tag") setTag("");
    setPage(1);
  }

  useEffect(() => {
    const searchParams = new URLSearchParams(window.location.search);
    const initialQuery = searchParams.get("q") ?? "";
    setQuery(initialQuery);
    setSearchText(initialQuery);
    setRelationshipType(searchParams.get("type") ?? "");
    setStatus(searchParams.get("status") ?? "");
    setTag(searchParams.get("tag") ?? "");
    setPage(Number(searchParams.get("page") ?? 1));
    setPageSize(Number(searchParams.get("pageSize") ?? 25));
    setSort((searchParams.get("sort") as NonNullable<StakeholderListParams["sort"]>) ?? "last_interaction");
    setOrder((searchParams.get("order") as NonNullable<StakeholderListParams["order"]>) ?? "desc");
  }, []);

  useEffect(() => {
    void loadStakeholders();
  }, [loadStakeholders]);

  return (
    <div className="grid grid-cols-1 gap-7 xl:grid-cols-[360px_1fr]">
      <aside>
        <div className="mb-6">
          <p className="font-headline text-sm font-black uppercase tracking-[0.25em] text-blue">
            Registry
          </p>
          <h1 className="mt-2 font-headline text-5xl font-black uppercase tracking-tight">
            Stakeholders
          </h1>
          <p className="mt-3 max-w-sm font-semibold text-ink/70">
            Veja todos, filtre por status, tipo e tags, ou encontre um contato especifico por nome,
            telefone ou contact_id.
          </p>
        </div>

        <div className="brutal-border brutal-shadow bg-panel p-5">
          <div className="flex items-center justify-between border-b-2 border-ink pb-3">
            <h2 className="font-headline text-2xl font-black uppercase">Filtros</h2>
            <SlidersHorizontal className="h-5 w-5" aria-hidden="true" />
          </div>

          <form onSubmit={submit} className="mt-5 space-y-4">
            <label className="block">
              <span className="font-headline text-xs font-black uppercase tracking-widest text-ink/60">
                Busca especifica
              </span>
              <span className="relative mt-2 block">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2" />
                <input
                  value={searchText}
                  onChange={(event) => setSearchText(event.target.value)}
                  placeholder="Nome, telefone ou ID"
                  className="brutal-border-thin w-full bg-white py-3 pl-11 pr-3 font-bold placeholder:text-ink/45 focus-visible:brutal-focus"
                />
              </span>
            </label>

            <FilterSelect
              label="Tipo"
              value={relationshipType}
              onChange={(value) => {
                setRelationshipType(value);
                setPage(1);
              }}
              options={TYPE_OPTIONS}
              emptyLabel="Todos os tipos"
            />

            <FilterSelect
              label="Status"
              value={status}
              onChange={(value) => {
                setStatus(value);
                setPage(1);
              }}
              options={STATUS_OPTIONS}
              emptyLabel="Todos os status"
            />

            <FilterSelect
              label="Tag"
              value={tag}
              onChange={(value) => {
                setTag(value);
                setPage(1);
              }}
              options={TAG_OPTIONS}
              emptyLabel="Todas as tags"
            />

            <div className="grid grid-cols-2 gap-3">
              <FilterSelect
                label="Por pagina"
                value={String(pageSize)}
                onChange={(value) => {
                  setPageSize(Number(value));
                  setPage(1);
                }}
                options={PAGE_SIZE_OPTIONS.map(String)}
              />
              <FilterSelect
                label="Ordem"
                value={order}
                onChange={(value) => {
                  setOrder(value as NonNullable<StakeholderListParams["order"]>);
                  setPage(1);
                }}
                options={["desc", "asc"]}
              />
            </div>

            <label className="block">
              <span className="font-headline text-xs font-black uppercase tracking-widest text-ink/60">
                Ordenar por
              </span>
              <select
                value={sort}
                onChange={(event) => {
                  setSort(event.target.value as NonNullable<StakeholderListParams["sort"]>);
                  setPage(1);
                }}
                className="brutal-border-thin mt-2 w-full bg-white px-3 py-3 font-headline text-sm font-black uppercase tracking-widest focus-visible:brutal-focus"
              >
                {SORT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <div className="grid grid-cols-1 gap-2">
              <Button type="submit" variant="dark">
                <Search className="h-4 w-4" aria-hidden="true" />
                Aplicar busca
              </Button>
              <Button type="button" variant="secondary" onClick={resetFilters}>
                <RotateCcw className="h-4 w-4" aria-hidden="true" />
                Resetar
              </Button>
            </div>
          </form>
        </div>
      </aside>

      <section className="min-w-0">
        <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="brutal-border-thin bg-yellow px-3 py-2 font-headline text-xs font-black uppercase tracking-widest">
            <ListFilter className="mr-2 inline h-4 w-4 align-text-bottom" aria-hidden="true" />
            {activeFilters.length > 0 ? `${activeFilters.length} filtros ativos` : "Sem filtros ativos"}
          </div>
          {activeFilters.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {activeFilters.map((filter) => (
                <button
                  key={filter.key}
                  type="button"
                  onClick={() => clearFilter(filter.key)}
                  className="brutal-border-thin inline-flex items-center gap-2 bg-panel px-3 py-2 font-headline text-xs font-black uppercase tracking-widest transition-colors hover:bg-red hover:text-white focus-visible:brutal-focus motion-reduce:transition-none"
                >
                  {filter.label}
                  <X className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              ))}
            </div>
          ) : null}
        </div>

        {loading ? <LoadingState label="Carregando stakeholders..." /> : null}
        {error ? <ErrorState message={error} onRetry={() => void loadStakeholders()} /> : null}
        {!loading && !error && data.items.length === 0 ? (
          <EmptyState
            title="Nenhum stakeholder encontrado"
            message="Ajuste filtros, remova a tag selecionada ou busque por outro telefone, nome ou contact_id."
            action={
              <Button type="button" variant="secondary" onClick={resetFilters}>
                Limpar filtros
              </Button>
            }
          />
        ) : null}
        {!loading && !error && data.items.length > 0 ? (
          <StakeholderResults
            stakeholders={data.items}
            total={data.total}
            page={data.page}
            pageSize={data.pageSize}
            sortLabel={sortLabel}
            onPageChange={setPage}
          />
        ) : null}
      </section>
    </div>
  );
}

function FilterSelect({
  label,
  value,
  options,
  emptyLabel,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  emptyLabel?: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="font-headline text-xs font-black uppercase tracking-widest text-ink/60">
        {label}
      </span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="brutal-border-thin mt-2 w-full bg-white px-3 py-3 font-headline text-sm font-black uppercase tracking-widest focus-visible:brutal-focus"
      >
        {emptyLabel ? <option value="">{emptyLabel}</option> : null}
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}
