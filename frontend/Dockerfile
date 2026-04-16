# ── Stage 1: Build ────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

# Enable BuildKit cache mounts for faster builds
ENV NEXT_TELEMETRY_DISABLED=1

WORKDIR /app

# Install deps first (separate layer for caching)
COPY package*.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --prefer-offline

# Copy source and build with persistent Next.js cache
COPY . .
RUN --mount=type=cache,target=/app/.next/cache \
    npm run build

# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
# Standalone output produces a self-contained server with no node_modules needed
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000

# Copy only the standalone server output (tiny footprint, starts instantly)
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static    ./.next/static
COPY --from=builder /app/public          ./public

EXPOSE 3000

# Start the standalone Next.js server directly (no npm, no startup overhead)
CMD ["node", "server.js"]
