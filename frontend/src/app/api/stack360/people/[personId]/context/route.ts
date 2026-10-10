import type { NextRequest } from "next/server";
import { invalidIdResponse, isValidUuid, proxyGet } from "@/lib/stack360/server/proxy";

const ALLOWED_PARAMS = ["include", "limit", "since"] as const;

export async function GET(req: NextRequest, { params }: { params: Promise<{ personId: string }> }) {
  const { personId } = await params;
  if (!isValidUuid(personId)) return invalidIdResponse("personId");
  return proxyGet(`/api/v1/people/${personId}/context`, req, ALLOWED_PARAMS);
}
