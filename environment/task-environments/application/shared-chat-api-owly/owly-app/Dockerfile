# Owly (Hesper-Labs/owly) pinned build.
#
# We vendor our own Dockerfile instead of building from the upstream git
# context because upstream's `npm run build` (Next.js page-data collection)
# hard-requires JWT_SECRET at BUILD time. Those build-time values are dummies
# used only for static analysis; the real secrets are injected at RUNTIME via
# compose `environment:` and override these when the server actually starts.
#
# Structure mirrors the upstream two-stage Dockerfile at commit 430c646e.

# ---- Builder stage ----
FROM node:22-slim AS builder

WORKDIR /app

# Download the pinned Owly source (self-contained; no git build context needed).
ADD https://github.com/Hesper-Labs/owly/archive/430c646e51aea8367d1e1a88953e9b56d059fa8d.tar.gz /tmp/owly.tar.gz
RUN tar -xzf /tmp/owly.tar.gz --strip-components=1 -C /app && rm /tmp/owly.tar.gz

RUN npm ci

RUN npx prisma generate

# Build-time-only placeholders so `next build` can statically analyze routes
# that import the config module. Overridden at runtime by compose env.
ENV JWT_SECRET=build-time-placeholder-not-used-at-runtime
ENV NEXTAUTH_SECRET=build-time-placeholder-not-used-at-runtime
ENV WEBHOOK_SECRET=build-time-placeholder-not-used-at-runtime
# Owly server components/layouts query Postgres at module eval; Next.js
# would run those queries while statically prerendering at build time,
# when no DB exists. Force every server route dynamic (skip prerender).
# POSIX sh (dash): no `read -d`; repo paths contain no spaces.
RUN set -e; \
    for f in $(find src/app -type f \( -name "page.tsx" -o -name "layout.tsx" -o -name "route.ts" \)); do \
      if ! head -1 "$f" | grep -q "use client" && ! grep -q "export const dynamic" "$f"; then \
        printf 'export const dynamic = "force-dynamic";\n' | cat - "$f" > "$f.tmp" && mv "$f.tmp" "$f"; \
      fi; \
    done

ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ---- Runner stage ----
FROM node:22-slim AS runner

LABEL org.opencontainers.image.source="https://github.com/Hesper-Labs/owly"
LABEL org.opencontainers.image.description="AI-powered customer support agent"

RUN apt-get update && apt-get install -y \
    chromium \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production
ENV PORT=3000

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

WORKDIR /app

COPY --from=builder /app/package*.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/prisma ./prisma
COPY --from=builder /app/src/generated ./src/generated
COPY --from=builder /app/next.config.ts ./
# Owly's schema.prisma datasource has no url; it lives only in the root
# prisma.config.ts (url: process.env.DATABASE_URL). Upstream's Dockerfile
# omits this file, so `prisma migrate deploy` has no datasource at runtime.
COPY --from=builder /app/prisma.config.ts ./

RUN chown -R nextjs:nodejs /app

USER nextjs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD node -e "fetch('http://localhost:3000/api/health').then(r => { if (!r.ok) process.exit(1) }).catch(() => process.exit(1))"

# migrate + seed (return/refund KB) + start; seed is best-effort.
# Prisma 7 ignores package.json prisma.seed, so run the seed script via tsx
# directly rather than `prisma db seed` (which reports "no seed configured").
CMD ["sh", "-c", "npx prisma migrate deploy && (npx tsx prisma/seed.ts || echo 'seed skipped') && npm start"]
