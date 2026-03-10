# Web ALT (Next.js) - Production Dockerfile
# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
ENV NODE_ENV=production
# Install deps
COPY package.json package-lock.json* ./
RUN npm ci --include=dev
# Copy source and build
COPY . .
# NEXT_PUBLIC_API_BASE must be provided at runtime (Railway env). No build-time default.
RUN npm run build

# Runtime stage
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
# Copy only what we need to run
COPY --from=builder /app/package.json /app/package-lock.json ./
COPY --from=builder /app/.next ./.next
# Install only production deps
RUN npm ci --omit=dev
# Expose web port
EXPOSE 3000
# Start Next.js (bind to Railway's PORT and 0.0.0.0)
CMD ["sh", "-c", "npx next start -H 0.0.0.0 -p ${PORT:-3000}"]
