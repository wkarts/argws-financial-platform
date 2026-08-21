FROM node:22-alpine AS build
WORKDIR /app
ARG VITE_APP_NAME="ARGWS Financial Platform"
ARG VITE_CONTROL_PLANE_HOST="control.localhost"
ARG VITE_API_BASE_URL="/api"
ENV VITE_APP_NAME=$VITE_APP_NAME \
    VITE_CONTROL_PLANE_HOST=$VITE_CONTROL_PLANE_HOST \
    VITE_API_BASE_URL=$VITE_API_BASE_URL
COPY VERSION /VERSION
COPY frontend/package.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
# vite.config.ts lê /VERSION através do caminho relativo ../VERSION; a versão
# publicada nunca precisa ser duplicada em ARG/ENV do Dockerfile.
RUN cp /VERSION ../VERSION && npm run build

FROM nginx:1.27-alpine
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
