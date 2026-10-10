import type { NextRequest } from "next/server";
import { proxyGet } from "@/lib/stack360/server/proxy";

const ALLOWED_PARAMS = ["query", "identity_type", "identity_value", "limit", "cursor"] as const;

export async function GET(req: NextRequest) {
  return proxyGet("/api/v1/people", req, ALLOWED_PARAMS);
}
