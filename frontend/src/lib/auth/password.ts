import "server-only";

import bcrypt from "bcryptjs";
import { getAdminPasswordHash, getAdminUsername } from "./env";

export async function verifyCredentials(username: string, password: string): Promise<boolean> {
  if (username !== getAdminUsername()) return false;
  try {
    return await bcrypt.compare(password, getAdminPasswordHash());
  } catch {
    return false;
  }
}
