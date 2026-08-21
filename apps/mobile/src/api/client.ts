const DEFAULT_TIMEOUT_MS = 8_000;

type ResponseSchema<T> = {
  parse(value: unknown): T;
};

export type FetchLike = (
  input: string,
  init?: RequestInit,
) => Promise<Response>;

export class ApiRequestError extends Error {
  constructor(
    message: string,
    readonly status: number | null,
  ) {
    super(message);
  }
}

export type ApiClient = {
  get<T>(path: `/${string}`, schema: ResponseSchema<T>): Promise<T>;
};

export function createApiClient(
  apiOrigin: string,
  fetcher: FetchLike = fetch,
  timeoutMs = DEFAULT_TIMEOUT_MS,
): ApiClient {
  return {
    async get<T>(path: `/${string}`, schema: ResponseSchema<T>): Promise<T> {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), timeoutMs);
      try {
        const response = await fetcher(`${apiOrigin}${path}`, {
          headers: { Accept: "application/json" },
          signal: controller.signal,
        });
        if (!response.ok) {
          throw new ApiRequestError("API вернул ошибку", response.status);
        }
        return schema.parse(await response.json());
      } catch (error) {
        if (error instanceof ApiRequestError) throw error;
        if (error instanceof Error && error.name === "AbortError") {
          throw new ApiRequestError("API не ответил вовремя", null);
        }
        throw new ApiRequestError("Не удалось получить данные API", null);
      } finally {
        clearTimeout(timeout);
      }
    },
  };
}
