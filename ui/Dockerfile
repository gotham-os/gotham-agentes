FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# NEXT_PUBLIC_AGNO_API_URL é injetado em build time pelo Coolify
ARG NEXT_PUBLIC_AGNO_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_AGNO_API_URL=$NEXT_PUBLIC_AGNO_API_URL

RUN npm run build

# ── Runtime ──────────────────────────────────────────────────────────────────
FROM node:20-alpine

WORKDIR /app

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME=0.0.0.0

CMD ["node", "server.js"]
