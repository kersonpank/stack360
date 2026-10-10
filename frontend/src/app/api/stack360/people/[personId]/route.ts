import type { NextRequest } from "next/server";
import { invalidIdResponse, isValidUuid, proxyGet } from "@/lib/stack360/server/proxy";

export async function GET(req: NextRequest, { params }: { params: Promise<{ personId: string }> }) {
  const { personId } = await params;
  if (!isValidUuid(personId)) return invalidIdResponse("personId");
  return proxyGet(`/api/v1/people/${personId}`, req);
}
