# Build API binary
FROM golang:1.22-alpine AS builder
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /server ./cmd/server

# Runtime: Node + Playwright Chromium for future export-slides execution
FROM node:20-bookworm-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
	&& rm -rf /var/lib/apt/lists/*
RUN npm init -y && npm install playwright@1.49.0 \
	&& npx playwright install chromium --with-deps \
	&& rm -rf /root/.npm
COPY --from=builder /server /app/server
EXPOSE 8080
ENV PORT=8080
CMD ["/app/server"]
