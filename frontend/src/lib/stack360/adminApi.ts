import { Stack360ClientError } from "./api";
import type {
  AdminApiKey,
  AdminSource,
  AdminWorkspace,
  CreatedApiKey,
  Stack360Error,
} from "./types";

async function bffRequest<T>(path: string, init?: { method?: "GET" | "POST"; body?: unknown }): Promise<T> {
  const response = await fetch(path, {
    method: init?.method ?? "GET",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      ...(init?.body !== undefined ? { "Content-Type": "application/json" } : {}),
    },
    body: init?.body !== undefined ? JSON.stringify(init.body) : undefined,
  });

  if (!response.ok) {
    let body: Stack360Error = { code: "UNKNOWN_ERROR", message: `Falha ao chamar ${path} (${response.status})` };
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

export async function listWorkspaces(): Promise<AdminWorkspace[]> {
  const data = await bffRequest<{ items: AdminWorkspace[] }>("/api/stack360/admin/workspaces");
  return data.items;
}

export async function createWorkspace(slug: string, name: string): Promise<AdminWorkspace> {
  return bffRequest<AdminWorkspace>("/api/stack360/admin/workspaces", { method: "POST", body: { slug, name } });
}

export async function listSources(workspaceId: string): Promise<AdminSource[]> {
  const data = await bffRequest<{ items: AdminSource[] }>(
    `/api/stack360/admin/sources?workspace_id=${encodeURIComponent(workspaceId)}`,
  );
  return data.items;
}

export async function createSource(
  workspaceId: string,
  key: string,
  name: string,
  sourceType: string,
): Promise<AdminSource> {
  return bffRequest<AdminSource>("/api/stack360/admin/sources", {
    method: "POST",
    body: { workspace_id: workspaceId, key, name, source_type: sourceType },
  });
}

export async function listApiKeys(workspaceId: string): Promise<AdminApiKey[]> {
  const data = await bffRequest<{ items: AdminApiKey[] }>(
    `/api/stack360/admin/api-keys?workspace_id=${encodeURIComponent(workspaceId)}`,
  );
  return data.items;
}

export async function createApiKey(params: {
  workspaceId: string;
  sourceId?: string;
  name: string;
  scopes: string[];
}): Promise<CreatedApiKey> {
  return bffRequest<CreatedApiKey>("/api/stack360/admin/api-keys", {
    method: "POST",
    body: {
      workspace_id: params.workspaceId,
      source_id: params.sourceId ?? null,
      name: params.name,
      scopes: params.scopes,
    },
  });
}

export async function revokeApiKey(id: string): Promise<void> {
  await bffRequest(`/api/stack360/admin/api-keys/${encodeURIComponent(id)}/revoke`, { method: "POST" });
}
