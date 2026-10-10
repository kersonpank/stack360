import type { NextRequest } from "next/server";
import { proxyGet } from "@/lib/stack360/server/proxy";

export async function GET(req: NextRequest) {
  return proxyGet("/api/v1/sources", req);
}
