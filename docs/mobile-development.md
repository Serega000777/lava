# Mobile development

## Scope

`apps/mobile` is an Expo SDK 57 test client and the boundary for a future native
application. It is intentionally smaller than the web MVP: today it verifies API
health, category contracts and the newest public listings on a physical phone.
FastAPI remains the only home for authorization and business rules.

Shared runtime response schemas are published by the private workspace package
`@lava/api-contracts`. Mobile feature services consume those schemas through a
small HTTP adapter with an eight-second timeout and safe errors. UI components do
not trust arbitrary JSON or reproduce search, pricing or moderation logic.

## Start on a physical phone

Requirements:

- Node.js 22 or newer;
- Docker stack running with API port `8000` exposed;
- current Expo Go application compatible with SDK 57;
- phone and development computer on the same trusted local network.

Copy the example configuration:

```powershell
Copy-Item apps/mobile/.env.example apps/mobile/.env.local
```

Find the computer's active private IPv4 address and place it in the file:

```text
EXPO_PUBLIC_API_URL=http://192.168.1.25:8000
```

Then start the stack and Metro:

```powershell
docker compose up -d
npm run mobile
```

Scan the QR code with Expo Go. Do not use `localhost`: on a physical device it
means the phone. If the health card cannot connect, verify `http://<LAN-IP>:8000/health`
from the phone browser and allow inbound TCP 8000 only on the trusted private
network. Plain HTTP is development-only; production mobile builds must use HTTPS.

## Verification

```powershell
npm run check:mobile
npx expo install --check
npx expo-doctor@latest --verbose
```

`check:mobile` runs ESLint, strict TypeScript, unit tests and a deterministic
Android JavaScript bundle export. Expo Doctor also contacts an Expo schema
service; if that service returns a non-JSON gateway page, validate the local
configuration with `npx expo config --type public` and record the external failure.

## Security boundary for future private screens

The current browser session is an HttpOnly cookie protected by CSRF controls. It
must not be copied into JavaScript storage merely to make native screens work.
Before login, profile, favorites or chat are enabled in Expo, implement and review:

1. an explicit native session transport using the same revocable server sessions;
2. OS-backed secure token storage (for example Expo SecureStore);
3. logout and remote revocation behavior;
4. mobile rate-limit and device privacy policy;
5. tests proving browser cookie/CSRF behavior is unchanged.

Never place credentials, session tokens or provider secrets in `EXPO_PUBLIC_*`.
Camera, media-library and notification permissions will be requested only when a
user-visible feature actually needs them.
