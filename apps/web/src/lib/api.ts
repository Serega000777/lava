let csrfToken: string | null = null;

async function getCsrfToken(apiOrigin: string): Promise<string> {
  if (csrfToken) return csrfToken;
  const response = await fetch(`${apiOrigin}/auth/csrf`, { credentials: "include" });
  if (!response.ok) throw new Error("csrf bootstrap failed");
  const data = await response.json() as { token: string };
  csrfToken = data.token;
  return csrfToken;
}

async function isInvalidCsrf(response: Response): Promise<boolean> {
  if (response.status !== 403) return false;
  const body = await response.clone().json().catch(() => null) as
    | { detail?: { code?: string } }
    | null;
  return body?.detail?.code === "csrf_invalid";
}

async function mutationFetch(input: string, init: RequestInit): Promise<Response> {
  const token = await getCsrfToken(new URL(input).origin);
  const headers = new Headers(init.headers);
  headers.set("X-CSRF-Token", token);
  return fetch(input, { ...init, headers, credentials: "include" });
}

export async function apiFetch(input: string, init: RequestInit = {}) {
  const method = (init.method ?? "GET").toUpperCase();
  if (!["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    return fetch(input, init);
  }
  let response = await mutationFetch(input, init);
  if (await isInvalidCsrf(response)) {
    csrfToken = null;
    response = await mutationFetch(input, init);
  }
  return response;
}
