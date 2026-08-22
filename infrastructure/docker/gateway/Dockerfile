FROM nginx:1.27-alpine
COPY infrastructure/nginx/gateway.conf.template /etc/nginx/templates/default.conf.template
COPY infrastructure/docker/gateway/landing/ /usr/share/nginx/landing/
ENV PLATFORM_DOMAIN=finance.argws.com.br \
    CONTROL_PLANE_HOST=control.finance.argws.com.br \
    ADMIN_HOST=admin.finance.argws.com.br \
    API_HOST=api.finance.argws.com.br \
    DEMO_HOST=demo.finance.argws.com.br \
    TENANT_DOMAIN_ROOT=finance.argws.com.br
EXPOSE 80
HEALTHCHECK --interval=15s --timeout=5s --retries=20 CMD wget -q --spider --header="Host: ${API_HOST}" http://127.0.0.1/health/live || exit 1
