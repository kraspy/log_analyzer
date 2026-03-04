# ── Build stage ──────────────────────────────────────
FROM node:24.14.0-alpine AS builder

WORKDIR /app

# Copy dependency files first (Docker layer caching)
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Copy source code and build
COPY . .
RUN npm run build

# ── Runtime stage ────────────────────────────────────
# Nginx serves the static build output
FROM nginx:alpine

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx config: SPA fallback (all routes → index.html)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
