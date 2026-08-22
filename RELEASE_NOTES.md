# Release Notes — v1.0.0-rc.17

Esta release faz um hardening funcional e de UX no ambiente financeiro do cliente, corrigindo erros observados no uso real após o primeiro login e removendo detalhes internos que não devem aparecer fora do Control Plane.

## Segurança e isolamento de infraestrutura

- downloads de remessa CNAB deixam de expor URL interna do MinIO, bucket, host Docker e parâmetros AWS no navegador;
- remessas passam a ser baixadas por endpoint autenticado da própria API, com verificação de permissão e acesso à empresa;
- `S3StorageProvider.presigned_url()` não gera mais link usando `S3_ENDPOINT_URL` interno; somente um `S3_PUBLIC_ENDPOINT_URL` explicitamente configurado pode produzir URL pública;
- erros 500/422 deixam de exibir mensagens técnicas genéricas do Axios ao usuário final;
- mensagens de integração não expõem Evolution API/SMTP no fluxo gerenciado da plataforma;
- WhatsApp e e-mail gerenciados utilizam configuração global da plataforma no backend quando não existe integração personalizada da empresa.

## Correções dos 422 e 500 observados

- seletores que pediam `per_page=200`, `500` ou `1000` foram substituídos por paginação automática respeitando o limite real de `100` registros da API;
- corrigidos Pagamentos, Negociações, CNAB e Pix Automático;
- importação `FINANCEIRO Vitor.zip` deixa de converter UUIDs para string antes do acesso ao PostgreSQL e passa a tratar falhas de persistência de forma segura;
- formulários exibem a mensagem de validação útil ao usuário sem vazar detalhes internos.

## Cadastros e edição

- Empresas: criação e edição de dados operacionais, endereço e identidade visual;
- Clientes: criação e edição com endereço, contato, tags e status;
- Serviços: edição funcional sem JSON técnico;
- Contratos: edição funcional da regra recorrente;
- Contas bancárias e convênios: criação e edição;
- Usuários: edição, redefinição de senha e acesso por empresa;
- Perfis: permissões apresentadas por grupos e checkboxes, com código interno opcional somente em opções avançadas.

## Linguagem do cliente

No ambiente financeiro do cliente:

- `TENANT_ADMIN` passa a ser exibido como `Administrador`;
- códigos internos de papéis e permissões deixam de ser a interface principal;
- termos de infraestrutura como `tenant plane`, provider, Evolution API, SMTP, MinIO, bucket e object key são removidos da experiência normal;
- o termo `tenant` continua disponível apenas no Control Plane, onde representa o conceito administrativo da plataforma.

## WhatsApp gerenciado pela plataforma

A tela de Integrações passa a separar claramente:

- **WhatsApp** e **E-mail** fornecidos e administrados pela ARGWS, sem API Key ou servidor informado pelo cliente;
- **Integrações personalizadas**, opcionais, onde provedores específicos podem ser configurados conscientemente.

O Control Plane passa a controlar por tenant:

- habilitação do WhatsApp;
- inclusão no plano ou cobrança como adicional;
- valor mensal do adicional;
- permissão para integrações personalizadas.

## Demo e landing page por tenant

O detalhe do tenant no Control Plane passa a permitir:

- ativar ou desativar modo demonstração;
- editar nome, status, plano e fuso horário;
- desativar landing pública;
- usar landing gerenciada pela plataforma com título, subtítulo e CTA;
- associar uma landing externa;
- visualizar o estado comercial de WhatsApp e integrações personalizadas.

Quando uma landing gerenciada está habilitada, o domínio do tenant apresenta a página pública antes do login. Se estiver desabilitada, o domínio segue diretamente para autenticação. O modo demonstração é sinalizado tanto na landing quanto no ambiente autenticado.

## UX e grids

- barras de rolagem permanecem funcionais, porém ficam invisíveis/imperceptíveis em navegadores modernos;
- menu lateral e áreas internas preservam scroll sem a barra visual;
- tabelas voltam a usar largura fluida com mínimo responsivo, evitando o aspecto achatado observado nas telas grandes;
- cards recebem `min-width: 0` para impedir estouro e deformação dentro de grids.

## Topologia preservada

- `finance.argws.com.br` — landing pública da plataforma;
- `demo.finance.argws.com.br` — demonstração;
- `control.finance.argws.com.br` — Control Plane;
- `admin.finance.argws.com.br` — alias administrativo;
- `api.finance.argws.com.br` — API;
- `*.finance.argws.com.br` — domínios dos clientes;
- produção continua image-only via GHCR `:latest`;
- nenhuma porta interna adicional é publicada.
