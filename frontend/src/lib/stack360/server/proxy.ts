import "server-only";

import { NextRequest, NextResponse } from "next/server";
import { getStack360AdminApiKey } from "./env";
import { Stack360UnreachableError, Stack360UpstreamError, stack360Fetch } from "./client";

export async function proxyGet(
  upstreamPath: string,
  req: NextRequest,
  allowedParams: readonly string[] = [],
): Promise<NextResponse> {
  const searchParams = new URLSearchParams();
  for (const name of allowedParams) {
    const value = req.nextUrl.searchParams.get(name);
    if (value !== null) searchParams.set(name, value);
  }

  try {
    const data = await stack360Fetch(upstreamPath, { searchParams });
    return NextResponse.json(data);
  } catch (err) {
    if (err instanceof Stack360UpstreamError) {
      return NextResponse.json(
        { error: { code: err.code, message: err.message, details: err.details } },
        { status: err.status },
      );
    }
    if (err instanceof Stack360UnreachableError) {
      return NextResponse.json(
        { error: { code: "BFF_UPSTREAM_UNREACHABLE", message: err.message, details: {} } },
        { status: 502 },
      );
    }
    return NextResponse.json(
      { error: { code: "BFF_INTERNAL_ERROR", message: "Erro interno no proxy", details: {} } },
      { status: 500 },
    );
  }
}

/** GET/POST autenticados com a key ADMIN — só pras rotas de gestão (workspace/source/api-key). */
export async function proxyAdmin(
  upstreamPath: string,
  req: NextRequest,
  options: { allowedParams?: readonly string[]; method?: "GET" | "POST" } = {},
): Promise<NextResponse> {
  const searchParams = new URLSearchParams();
  for (const name of options.allowedParams ?? []) {
    const value = req.nextUrl.searchParams.get(name);
    if (value !== null) searchParams.set(name, value);
  }

  const method = options.method ?? "GET";
  let body: unknown;
  if (method === "POST") {
    try {
      body = await req.json();
    } catch {
      body = undefined;
    }
  }

  try {
    const data = await stack360Fetch(upstreamPath, {
      searchParams,
      method,
      body,
      apiKey: getStack360AdminApiKey(),
    });
    return NextResponse.json(data);
  } catch (err) {
    if (err instanceof Stack360UpstreamError) {
      return NextResponse.json(
        { error: { code: err.code, message: err.message, details: err.details } },
        { status: err.status },
      );
    }
    if (err instanceof Stack360UnreachableError) {
      return NextResponse.json(
        { error: { code: "BFF_UPSTREAM_UNREACHABLE", message: err.message, details: {} } },
        { status: 502 },
      );
    }
    return NextResponse.json(
      { error: { code: "BFF_INTERNAL_ERROR", message: "Erro interno no proxy", details: {} } },
      { status: 500 },
    );
  }
}

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function isValidUuid(value: string): boolean {
  return UUID_RE.test(value);
}

export function invalidIdResponse(paramName: string): NextResponse {
  return NextResponse.json(
    {
      error: {
        code: "BFF_INVALID_ID",
        message: `${paramName} inválido (esperado UUID)`,
        details: {},
      },
    },
    { status: 400 },
  );
}
