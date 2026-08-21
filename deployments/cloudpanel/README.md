# CloudPanel + Docker/Dockge

O CloudPanel atua como proxy TLS público; a aplicação permanece em Docker no gateway local `127.0.0.1:8800`.

Hosts obrigatórios:

- domínio principal;
- `control.<domínio>` para o Control Plane;
- `api.<domínio>` para OpenAPI, health e integrações centrais;
- `*.<domínio>` para tenants provisionados.

Os templates em `vhosts/` preservam o cabeçalho `Host`, condição obrigatória do isolamento. O instalador canônico é `install.sh`, que delega ao instalador completo da raiz. Para domínios personalizados, use o Domain Agent e a integração Cloudflare descritos em `docs/operations/DOMAINS_SSL.md`.
