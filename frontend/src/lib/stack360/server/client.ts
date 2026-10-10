import "server-only";

import { getStack360ApiBaseUrl, getStack360ApiKey } from "./env";

export type Stack360ErrorBody = {
  code: string;
  message: string;
  details?: Record<string, unknown>;
};

export class Stack360UpstreamError extends Error {
  status: number;
  code: string;
  details: Record<string, unknown>;

  constructor(status: number, body: Stack360ErrorBody) {
    super(body.message);
    this.name = "Stack360UpstreamError";
    this.status = status;
    this.code = body.code;
    this.details = body.details ?? {};
  }
}

export class Stack360UnreachableError extends Error {
  constructor(cause: unknown) {
    super("Não foi possível alcançar a API Stack360");
    this.name = "Stack360UnreachableError";
    this.cause = cause;
  }
}

export async function stack360Fetch<T>(
  path: string,
  options: { searchParams?: URLSearchParams } = {},
): Promise<T> {
  const query = options.searchParams?.toString();
  const url = `${getStack360ApiBaseUrl()}${path}${query ? `?${query}` : ""}`;

  let response: Response;
  try {
    response = await fetch(url, {
      cache: "no-store",
      headers: {
        Authorization: `Bearer ${getStack360ApiKey()}`,
        Accept: "application/json",
      },
    });
  } catch (cause) {
    throw new Stack360UnreachableError(cause);
  }

  if (!response.ok) {
    let body: Stack360ErrorBody = { code: "UNKNOWN_ERROR", message: `Falha na API (${response.status})` };
    try {
      const parsed = (await response.json()) as { error?: Stack360ErrorBody };
      if (parsed.error) body = parsed.error;
    } catch {
      // resposta sem corpo JSON — mantém o fallback acima
    }
    throw new Stack360UpstreamError(response.status, body);
  }

  return response.json() as Promise<T>;
}
