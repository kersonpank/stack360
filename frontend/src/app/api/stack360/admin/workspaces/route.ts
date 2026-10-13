import type { NextRequest } from "next/server";
import { proxyAdmin } from "@/lib/stack360/server/proxy";

export async function GET(req: NextRequest) {
  return proxyAdmin("/api/v1/admin/workspaces", req);
}

export async function POST(req: NextRequest) {
  return proxyAdmin("/api/v1/admin/workspaces", req, { method: "POST" });
}
