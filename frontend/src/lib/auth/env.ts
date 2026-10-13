import "server-only";

function readEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Variável de ambiente obrigatória ausente: ${name}`);
  }
  return value;
}

export function getAdminUsername(): string {
  return process.env.ADMIN_USERNAME?.trim() || "admin";
}

export function getAdminPasswordHash(): string {
  return readEnv("ADMIN_PASSWORD_HASH");
}

export function getSessionSecret(): string {
  return readEnv("SESSION_SECRET");
}
