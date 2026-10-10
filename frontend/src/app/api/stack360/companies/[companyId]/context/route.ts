import type { NextRequest } from "next/server";
import { invalidIdResponse, isValidUuid, proxyGet } from "@/lib/stack360/server/proxy";

const ALLOWED_PARAMS = ["include", "limit", "since"] as const;

export async function GET(req: NextRequest, { params }: { params: Promise<{ companyId: string }> }) {
  const { companyId } = await params;
  if (!isValidUuid(companyId)) return invalidIdResponse("companyId");
  return proxyGet(`/api/v1/companies/${companyId}/context`, req, ALLOWED_PARAMS);
}
