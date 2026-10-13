import type { NextRequest } from "next/server";
import { invalidIdResponse, isValidUuid, proxyAdmin } from "@/lib/stack360/server/proxy";

export async function POST(req: NextRequest, { params }: { params: Promise<{ keyId: string }> }) {
  const { keyId } = await params;
  if (!isValidUuid(keyId)) return invalidIdResponse("keyId");
  return proxyAdmin(`/api/v1/admin/api-keys/${keyId}/revoke`, req, { method: "POST" });
}
