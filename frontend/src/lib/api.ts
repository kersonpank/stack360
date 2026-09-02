import {
  mapApiConversationToUi,
  mapApiMessageListToUi,
  mapApiNormalizationStatusToUi,
  mapApiOpportunityToUi,
  mapApiStakeholderDetailToUi,
  mapApiStakeholderListToUi,
  mapApiStakeholderSearchToUi,
  mapApiTimelineToUi,
} from "./adapters";
import {
  mockConversations,
  mockMessageList,
  mockNormalizationStatus,
  mockOpportunities,
  mockStakeholderDetail,
  mockStakeholders,
  mockTimeline,
} from "./mockData";
import type {
  ApiConversation,
  ApiHealth,
  ApiMessageList,
  ApiNormalizationStatus,
  ApiOpportunity,
  ApiStakeholderDetail,
  ApiStakeholderListResponse,
  ApiStakeholderSearchResult,
  ApiTimelineEvent,
  UiConversation,
  UiMessageList,
  UiNormalizationStatus,
  UiOpportunity,
  UiStakeholderDetail,
  UiStakeholderListResponse,
  UiStakeholderSearchResult,
  UiTimelineEvent,
} from "./types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "http://localhost:8001";

export const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS === "true";

class ApiRequestError extends Error {
  status: number;
  path: string;

  constructor(status: number, path: string, detail: string) {
    super(`API request failed (${status}) ${path}${detail ? `: ${detail}` : ""}`);
    this.name = "ApiRequestError";
    this.status = status;
    this.path = path;
  }
}

let listEndpointAvailable = true;

type MessageParams = {
  limit?: number;
  offset?: number;
  order?: "asc" | "desc";
};

export type StakeholderListParams = {
  page?: number;
  pageSize?: number;
  q?: string;
  relationshipType?: string;
  status?: string;
  tag?: string;
  sort?: "name" | "last_interaction" | "messages" | "opportunity" | "risk" | "created";
  order?: "asc" | "desc";
};

async function request<T>(path: string): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const response = await fetch(url, {
    cache: "no-store",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    let detail = "";
    try {
      detail = JSON.stringify(await response.json());
    } catch {
      detail = await response.text();
    }

    throw new ApiRequestError(response.status, path, detail);
  }

  return response.json() as Promise<T>;
}

function sortStakeholders(
  items: UiStakeholderSearchResult[],
  sort: StakeholderListParams["sort"] = "last_interaction",
  order: StakeholderListParams["order"] = "desc",
) {
  const direction = order === "asc" ? 1 : -1;
  return [...items].sort((a, b) => {
    const valueA = getStakeholderSortValue(a, sort);
    const valueB = getStakeholderSortValue(b, sort);
    if (valueA < valueB) return -1 * direction;
    if (valueA > valueB) return 1 * direction;
    return a.id.localeCompare(b.id);
  });
}

function getPhoneSuffix(value: string | undefined) {
  const digits = value?.replace(/\D/g, "") ?? "";
  return digits.length >= 8 ? digits.slice(-8) : "";
}

function getStakeholderSortValue(
  stakeholder: UiStakeholderSearchResult,
  sort: StakeholderListParams["sort"],
) {
  if (sort === "name") return stakeholder.name.toLowerCase();
  if (sort === "messages") return stakeholder.totalMessages;
  if (sort === "opportunity") return stakeholder.score;
  if (sort === "risk") return stakeholder.riskScore;
  return stakeholder.lastInteraction ? Date.parse(stakeholder.lastInteraction) || 0 : 0;
}

function filterStakeholders(
  items: UiStakeholderSearchResult[],
  params: StakeholderListParams,
) {
  const q = params.q?.trim().toLowerCase();
  const phoneSuffix = getPhoneSuffix(q);
  const relationshipType = params.relationshipType?.toLowerCase();
  const status = params.status?.toLowerCase();
  const tag = params.tag?.toLowerCase();
  const hasTagData = items.some((stakeholder) => stakeholder.roles.length > 0);

  return items.filter((stakeholder) => {
    if (q) {
      const haystackParts = [
        stakeholder.id,
        stakeholder.name,
        stakeholder.phone,
        stakeholder.type,
        stakeholder.status,
        ...stakeholder.roles,
      ];
      const haystack = haystackParts.join(" ").toLowerCase();
      const digitHaystack = haystackParts.join(" ").replace(/\D/g, "");
      if (!haystack.includes(q) && (!phoneSuffix || !digitHaystack.includes(phoneSuffix))) {
        return false;
      }
    }
    if (relationshipType && stakeholder.type.toLowerCase() !== relationshipType) return false;
    if (status && stakeholder.status.toLowerCase() !== status) return false;
    if (
      tag &&
      hasTagData &&
      !stakeholder.roles.some((role) => role.toLowerCase() === tag)
    ) {
      return false;
    }
    return true;
  });
}

function paginateStakeholders(
  items: UiStakeholderSearchResult[],
  params: StakeholderListParams,
): UiStakeholderListResponse {
  const page = params.page ?? 1;
  const pageSize = params.pageSize ?? 25;
  const filtered = filterStakeholders(items, params);
  const sorted = sortStakeholders(filtered, params.sort, params.order);
  const start = (page - 1) * pageSize;

  return {
    total: sorted.length,
    page,
    pageSize,
    items: sorted.slice(start, start + pageSize),
  };
}

export async function getHealth(): Promise<ApiHealth> {
  if (USE_MOCKS) return { status: "ok", service: "stakeholder-intelligence-api (mock)" };
  return request<ApiHealth>("/api/v1/health");
}

export async function getNormalizationStatus(): Promise<UiNormalizationStatus> {
  if (USE_MOCKS) return mockNormalizationStatus;
  const data = await request<ApiNormalizationStatus>("/api/v1/system/normalization-status");
  return mapApiNormalizationStatusToUi(data);
}

export async function searchStakeholders(query: string): Promise<UiStakeholderSearchResult[]> {
  const normalizedQuery = query.trim();
  if (!normalizedQuery) return [];

  if (USE_MOCKS) {
    const normalized = normalizedQuery.toLowerCase();
    return mockStakeholders.filter((stakeholder) =>
      [stakeholder.id, stakeholder.name, stakeholder.phone, stakeholder.type]
        .join(" ")
        .toLowerCase()
        .includes(normalized),
    );
  }

  const data = await request<ApiStakeholderSearchResult[]>(
    `/api/v1/stakeholders/search?q=${encodeURIComponent(normalizedQuery)}`,
  );
  return data.map(mapApiStakeholderSearchToUi);
}

export async function listStakeholders(
  params: StakeholderListParams = {},
): Promise<UiStakeholderListResponse> {
  const page = params.page ?? 1;
  const pageSize = params.pageSize ?? 25;

  if (USE_MOCKS) {
    return paginateStakeholders(mockStakeholders, { ...params, page, pageSize });
  }

  if (!listEndpointAvailable) {
    return listStakeholdersViaSearchFallback(params, page, pageSize);
  }

  const searchParams = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
    sort: params.sort ?? "last_interaction",
    order: params.order ?? "desc",
  });
  if (params.q?.trim()) searchParams.set("q", params.q.trim());
  if (params.relationshipType) searchParams.set("relationship_type", params.relationshipType);
  if (params.status) searchParams.set("status", params.status);
  if (params.tag) searchParams.set("tag", params.tag);

  try {
    const data = await request<ApiStakeholderListResponse>(
      `/api/v1/stakeholders?${searchParams.toString()}`,
    );
    const response = mapApiStakeholderListToUi(data);
    if (response.total === 0) {
      const phoneSuffix = getPhoneSuffix(params.q);
      if (phoneSuffix && phoneSuffix !== params.q?.trim()) {
        const retryParams = new URLSearchParams(searchParams);
        retryParams.set("q", phoneSuffix);
        const retryData = await request<ApiStakeholderListResponse>(
          `/api/v1/stakeholders?${retryParams.toString()}`,
        );
        return mapApiStakeholderListToUi(retryData);
      }
    }
    return response;
  } catch (err) {
    if (err instanceof ApiRequestError && err.status === 404) {
      listEndpointAvailable = false;
      return listStakeholdersViaSearchFallback(params, page, pageSize);
    }
    throw err;
  }
}

async function listStakeholdersViaSearchFallback(
  params: StakeholderListParams,
  page: number,
  pageSize: number,
): Promise<UiStakeholderListResponse> {
  const normalizedQuery = params.q?.trim();
  if (!normalizedQuery) {
    throw new Error(
      "A API em localhost:8001 ainda nao tem a rota de listagem /api/v1/stakeholders. Reinicie o backend atualizado para ver todos os stakeholders sem busca.",
    );
  }

  const data = await request<ApiStakeholderSearchResult[]>(
    `/api/v1/stakeholders/search?q=${encodeURIComponent(normalizedQuery)}`,
  );
  let items = data.map(mapApiStakeholderSearchToUi);
  if (items.length === 0) {
    const phoneSuffix = getPhoneSuffix(normalizedQuery);
    if (phoneSuffix && phoneSuffix !== normalizedQuery) {
      const retryData = await request<ApiStakeholderSearchResult[]>(
        `/api/v1/stakeholders/search?q=${encodeURIComponent(phoneSuffix)}`,
      );
      items = retryData.map(mapApiStakeholderSearchToUi);
    }
  }
  return paginateStakeholders(items, {
    ...params,
    page,
    pageSize,
  });
}

export async function getStakeholder(contactId: string): Promise<UiStakeholderDetail> {
  if (USE_MOCKS) return { ...mockStakeholderDetail, id: contactId || mockStakeholderDetail.id };
  const data = await request<ApiStakeholderDetail>(
    `/api/v1/stakeholders/${encodeURIComponent(contactId)}`,
  );
  return mapApiStakeholderDetailToUi(data);
}

export async function getStakeholderConversations(contactId: string): Promise<UiConversation[]> {
  if (USE_MOCKS) return mockConversations.map((conversation) => ({ ...conversation, contactId }));
  const data = await request<ApiConversation[]>(
    `/api/v1/stakeholders/${encodeURIComponent(contactId)}/conversations`,
  );
  return data.map(mapApiConversationToUi);
}

export async function getStakeholderTimeline(contactId: string): Promise<UiTimelineEvent[]> {
  if (USE_MOCKS) return mockTimeline;
  const data = await request<ApiTimelineEvent[]>(
    `/api/v1/stakeholders/${encodeURIComponent(contactId)}/timeline`,
  );
  return data.map(mapApiTimelineToUi);
}

export async function getStakeholderOpportunities(contactId: string): Promise<UiOpportunity[]> {
  if (USE_MOCKS) return mockOpportunities;
  const data = await request<ApiOpportunity[]>(
    `/api/v1/stakeholders/${encodeURIComponent(contactId)}/opportunities`,
  );
  return data.map(mapApiOpportunityToUi);
}

export async function getConversationMessages(
  conversationId: string,
  params: MessageParams = {},
): Promise<UiMessageList> {
  if (USE_MOCKS) return mockMessageList;
  const limit = params.limit ?? 100;
  const offset = params.offset ?? 0;
  const order = params.order ?? "desc";
  const data = await request<ApiMessageList>(
    `/api/v1/conversations/${encodeURIComponent(
      conversationId,
    )}/messages?limit=${limit}&offset=${offset}&order=${order}`,
  );
  return mapApiMessageListToUi(data);
}
