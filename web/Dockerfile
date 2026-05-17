# syntax=docker/dockerfile:1.7
# T3.6.1 — Frontend production image для Credit Assistant.
#
# Next.js 16 standalone output:
# * deps stage: ставит prod deps (npm ci --omit=dev) — кешируется на
#   package-lock.json;
# * builder stage: ставит full deps + builds production bundle;
# * runner stage: минимальный node:20-alpine + standalone server.js.
#
# Результат image ~200-250 MB (vs ~800 MB при full npm runtime). Не имеет
# npm, не имеет dev deps — surface attack минимальна.

FROM node:20-alpine AS deps
WORKDIR /app
# musl libc + libc6-compat для нативных модулей (sharp / next-swc).
RUN apk add --no-cache libc6-compat
COPY package.json package-lock.json ./
RUN npm ci --omit=dev


FROM node:20-alpine AS builder
WORKDIR /app
RUN apk add --no-cache libc6-compat
COPY package.json package-lock.json ./
# Build требует dev deps (типы, eslint-plugin-next, tailwind).
RUN npm ci
COPY . .
# Telemetry off в build-time — банк-internal сборка не должна стучаться.
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build


FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

# Non-root user — security baseline.
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

# Standalone output: ``.next/standalone`` уже содержит server.js +
# минимальное node_modules. Public assets копируем отдельно.
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
    CMD wget --quiet --tries=1 --spider http://127.0.0.1:3000/ || exit 1

CMD ["node", "server.js"]
