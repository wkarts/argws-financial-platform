# Deploy no Portainer

A stack usa imagens GHCR produzidas pelo workflow `images.yml`, portanto não depende de build local no Portainer.

## Pela interface

1. Registre `ghcr.io` em **Registries** quando o repositório for privado.
2. Crie uma Stack a partir de `stack.yaml`.
3. Carregue as variáveis de `.env.example` e substitua todos os `CHANGE_ME`.
4. Habilite o webhook da stack para atualização controlada.

## Pela API

Configure:

```bash
export PORTAINER_URL=https://portainer.exemplo.com.br
export PORTAINER_API_KEY=ptr_...
export PORTAINER_ENDPOINT_ID=1
export PORTAINER_STACK_NAME=argws-financial-platform
./deploy.sh
```

O script cria ou atualiza a stack de forma idempotente e nunca envia a API key para logs.

## Preparação offline

```bash
./deploy.sh --domain financeiro.exemplo.com.br --admin-email admin@exemplo.com.br --env-file /opt/argws-financial-platform/stack.env --prepare-only
```
