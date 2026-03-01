# WhatsApp Module

## Objetivo

Centralizar a operacao de mensagens por tenant, com inbox casado por cliente ou lead.

## Entidades principais

- `tenant_whatsapp_account`
- `messages`
- `whatsapp_unmatched_inbox`

## Fluxo recomendado

1. Criar ou atualizar a sessao do tenant.
2. Receber webhook inbound.
3. O backend tenta casar por prioridade: `client` antes de `lead`.
4. Se nao houver match, a mensagem cai em `whatsapp_unmatched_inbox`.
5. Para outbound, enviar mensagem pelo endpoint do tenant.
6. Receber webhook de status para atualizar entrega.

## Endpoints principais

- `POST /tenant/{workspace}/whatsapp/session`
- `GET /tenant/{workspace}/whatsapp/session`
- `POST /tenant/{workspace}/whatsapp/inbound`
- `POST /tenant/{workspace}/whatsapp/outbound`
- `POST /tenant/{workspace}/whatsapp/status`
- `GET /tenant/{workspace}/whatsapp/unmatched`

## Permissoes

- `whatsapp.manage`: sessao e configuracao
- `whatsapp.send`: envio outbound

## Observacoes

- Status aceitos: `sending`, `sent`, `delivered`, `read`, `failed`.
- A implementacao atual cobre a logica de API e rastreio; a integracao externa do provider ainda depende da camada de integracao real.
