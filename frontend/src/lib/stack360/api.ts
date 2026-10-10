import type {
  CompanyContext,
  CompanyDetail,
  CompanyListResponse,
  PersonContext,
  PersonListResponse,
  PersonSummary,
  SourceHealth,
  SourceSummary,
  Stack360Error,
} from "./types";

export class Stack360ClientError extends Error {
  status: number;
  code: string;
  details: Record<string, unknown>;

  constructor(status: number, body: Stack360Error) {
    super(body.message);
    this.name = "Stack360ClientError";
    this.status = status;
    this.code = body.code;
    this.details = body.details ?? {};
  }
}

async function bffRequest<T>(path: string): Promise<T> {
  const response = await fetch(path, {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    let body: Stack360Error = { code: "UNKNOWN_ERROR", message: `Falha ao consultar ${path} (${response.status})` };
    try {
      const parsed = (await response.json()) as { error?: Stack360Error };
      if (parsed.error) body = parsed.error;
    } catch {
      // mantém o fallback
    }
    throw new Stack360ClientError(response.status, body);
  }

  return response.json() as Promise<T>;
}

export async function getSources(): Promise<SourceSummary[]> {
  const data = await bffRequest<{ items: SourceSummary[] }>("/api/stack360/sources");
  return data.items;
}

export async function getSourcesHealth(): Promise<SourceHealth[]> {
  const data = await bffRequest<{ items: SourceHealth[] }>("/api/stack360/sources/health");
  return data.items;
}

export async function listPeople(params: { query?: string } = {}): Promise<PersonSummary[]> {
  const search = new URLSearchParams();
  if (params.query?.trim()) search.set("query", params.query.trim());
  const qs = search.toString();
  const data = await bffRequest<PersonListResponse>(`/api/stack360/people${qs ? `?${qs}` : ""}`);
  return data.items;
}

export async function getPersonContext(personId: string): Promise<PersonContext> {
  const include = "identities,companies,recent_interactions,observations,experience_runs,results,scores";
  return bffRequest<PersonContext>(
    `/api/stack360/people/${encodeURIComponent(personId)}/context?include=${include}`,
  );
}

export async function listCompanies(params: { query?: string } = {}): Promise<
  CompanyListResponse["items"]
> {
  const search = new URLSearchParams();
  if (params.query?.trim()) search.set("query", params.query.trim());
  const qs = search.toString();
  const data = await bffRequest<CompanyListResponse>(`/api/stack360/companies${qs ? `?${qs}` : ""}`);
  return data.items;
}

export async function getCompany(companyId: string): Promise<CompanyDetail> {
  return bffRequest<CompanyDetail>(`/api/stack360/companies/${encodeURIComponent(companyId)}`);
}

export async function getCompanyContext(companyId: string): Promise<CompanyContext> {
  const include = "people,recent_interactions,observations,scores";
  return bffRequest<CompanyContext>(
    `/api/stack360/companies/${encodeURIComponent(companyId)}/context?include=${include}`,
  );
}
