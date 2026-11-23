FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

FROM nginx:1.27-alpine
ENV API_UPSTREAM=api.railway.internal:8080 \
    NGINX_ENVSUBST_FILTER=^API_UPSTREAM$
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/templates/default.conf.template
EXPOSE 80
