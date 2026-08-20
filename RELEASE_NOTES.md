# Release Notes — v0.1.0-alpha.1

Esta entrega contém a plataforma SaaS financeira executável em Docker e permite validar o ciclo de cobrança de ponta a ponta usando providers Sandbox.

## Fluxo disponível

```text
Control Plane
 -> provisiona tenant
 -> cria banco, usuário PostgreSQL e bucket isolados
 -> registra domínio provisionado/customizado
 -> tenant cadastra empresas/clientes/contratos
 -> recorrência gera recebível
 -> provider Sandbox registra cobrança boleto/PIX
 -> régua envia SMTP/Evolution API
 -> pagamento/webhook baixa recebível
 -> conciliação
 -> recibo/NFS-e Sandbox
 -> documentos/auditoria
 -> backup/restore
```

## Classificação Alpha

A classificação Alpha não decorre de ausência do núcleo da plataforma. Ela permanece porque integrações financeiras externas exigem homologação com o banco, convênio, carteira, certificado e prefeitura escolhidos. O pacote não inventa credenciais nem declara homologação que não ocorreu.

## Validação executada no pacote

- compilação sintática de todos os módulos Python;
- configuração de todos os mapeamentos SQLAlchemy;
- **38 testes backend aprovados**;
- 85 rotas FastAPI encontradas sem duplicidade de método/caminho;
- sintaxe de 35 blocos TypeScript/Vue verificada;
- imports relativos do frontend validados;
- scripts Shell validados;
- YAML do Compose e workflows validado;
- instalador CloudPanel/Dockge executado com `--skip-up`;
- `.env` e credenciais gerados com permissão `0600`;
- consistência PostgreSQL/RabbitMQ/MinIO/S3 validada;
- importador validado contra o arquivo legado real, consolidando 319 registros da competência 2026-07;
- validador estrutural em `PASS`.

O build Docker e a instalação npm integral precisam ser executados pelo CI incluído ou no servidor de destino porque o ambiente de empacotamento não possui daemon Docker nem acesso ao registro npm.
