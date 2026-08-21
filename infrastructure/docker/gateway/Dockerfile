FROM nginx:1.27-alpine
COPY infrastructure/nginx/gateway.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=15s --timeout=5s --retries=20 CMD wget -q --spider http://127.0.0.1/health/live || exit 1
