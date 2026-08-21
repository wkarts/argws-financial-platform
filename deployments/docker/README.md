# Docker Compose

Há dois contratos de produção:

- `../../compose.yaml`: constrói API, PWA, gateway e agentes a partir do código-fonte do pacote;
- `compose.images.yaml`: usa imagens versionadas do GHCR, apropriado para servidores sem toolchain de build.

## Instalação a partir do fonte

```bash
./deployments/docker/install.sh --domain financeiro.exemplo.com.br --admin-email admin@exemplo.com.br --mode source
```

## Instalação com imagens

```bash
./deployments/docker/install.sh --domain financeiro.exemplo.com.br --admin-email admin@exemplo.com.br --mode images
```

O gateway publica somente `127.0.0.1:8800` por padrão. CloudPanel, Nginx, Traefik ou outro proxy deve preservar o cabeçalho `Host`.
