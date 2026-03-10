# ISO Middleware - Mock Producer (Docker)
# Build with:
#   docker build -t iso-mock-producer ./mock-producer
# Run with:
#   docker run --rm -p 4001:4001 --env-file .env iso-mock-producer

FROM node:18-alpine AS base
WORKDIR /app

# Install deps first (better layer caching)
COPY package.json package-lock.json* ./
RUN npm ci || npm install

# App source
COPY src ./src

# Default env
ENV PORT=4001

EXPOSE 4001
CMD ["node", "src/server.js"]
