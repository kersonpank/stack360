import type { NextRequest } from "next/server";
import { proxyGet } from "@/lib/stack360/server/proxy";

const ALLOWED_PARAMS = ["query", "domain", "cnpj", "limit", "cursor"] as const;

export async function GET(req: NextRequest) {
  return proxyGet("/api/v1/companies", req, ALLOWED_PARAMS);
}
