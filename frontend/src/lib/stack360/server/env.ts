import "server-only";

function readEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Variável de ambiente obrigatória ausente: ${name}`);
  }
  return value;
}

export function getStack360ApiBaseUrl(): string {
  return readEnv("STACK360_API_BASE_URL").replace(/\/$/, "");
}

export function getStack360ApiKey(): string {
  return readEnv("STACK360_API_KEY");
}

export function getStack360AdminApiKey(): string {
  return readEnv("STACK360_ADMIN_API_KEY");
}
