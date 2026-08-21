export type MobileConfig = {
  apiOrigin: string;
};

export class MobileConfigurationError extends Error {}

export function readMobileConfig(apiUrl: string | undefined): MobileConfig {
  if (!apiUrl) {
    throw new MobileConfigurationError(
      "Укажите EXPO_PUBLIC_API_URL в apps/mobile/.env.local",
    );
  }

  let parsed: URL;
  try {
    parsed = new URL(apiUrl);
  } catch {
    throw new MobileConfigurationError("EXPO_PUBLIC_API_URL должен быть корректным URL");
  }
  if (!new Set(["http:", "https:"]).has(parsed.protocol)) {
    throw new MobileConfigurationError("API должен использовать HTTP или HTTPS");
  }
  if (parsed.pathname !== "/" || parsed.search || parsed.hash) {
    throw new MobileConfigurationError("EXPO_PUBLIC_API_URL должен содержать только origin API");
  }

  return { apiOrigin: parsed.origin };
}
