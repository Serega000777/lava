FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
RUN --mount=type=cache,target=/root/.npm \
    npm ci --workspace @lava/web --fetch-retries=5 --fetch-timeout=60000
COPY apps/web apps/web
RUN npm run build --workspace @lava/web

FROM node:24-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
RUN apk upgrade --no-cache \
    && rm -rf /usr/local/lib/node_modules/npm \
      /usr/local/lib/node_modules/corepack \
      /opt/yarn-v1.22.22 \
    && rm -f /usr/local/bin/npm /usr/local/bin/npx \
      /usr/local/bin/corepack /usr/local/bin/yarn /usr/local/bin/yarnpkg
COPY --chown=node:node --from=build /app/apps/web/.next/standalone ./
COPY --chown=node:node --from=build /app/apps/web/.next/static ./apps/web/.next/static
USER node
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
