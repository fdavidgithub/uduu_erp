# Design: Addon `chat_observer`

**Data:** 2026-06-01  
**Status:** Aprovado

---

## Contexto

O sistema UDUU processa pedidos via WhatsApp. A fase de cada conversa em andamento (produto, cliente, endereço, pagamento, operador, erro) é persistida no DynamoDB pelo orquestrador `orders.py` e exposta via API externa (em desenvolvimento). O `chat_observer` é um addon Odoo que consome essa API e oferece ao operador uma visão em tempo real de todos os chats em andamento, permitindo intervenção rápida quando necessário.

---

## Objetivo

Criar o addon `chat_observer` no repositório `uduu_erp` com um dashboard que exibe KPIs e cards de chats por cor de urgência, com atualização automática e modal de interação.

---

## Seção 1: Posicionamento e Dependências

- **Nome do diretório:** `addons/chat_observer`
- **Dependências Odoo:** `uduu_base`, `web`
- **Sem modelos próprios** — nenhuma tabela é criada no banco do Odoo; os dados vêm exclusivamente da API externa via proxy Python
- **Categoria:** `Customizations`
- **`application: True`** — aparece como app no menu principal

---

## Seção 2: Estrutura de Arquivos

```
addons/chat_observer/
├── __manifest__.py
├── __init__.py
├── controllers/
│   ├── __init__.py
│   └── chat_observer.py
├── views/
│   └── chat_observer_action.xml
├── data/
│   └── chat_observer_data.xml
├── static/
│   └── src/
│       ├── js/
│       │   ├── chat_observer_dashboard.js
│       │   └── chat_observer_card.js
│       ├── xml/
│       │   ├── chat_observer_dashboard.xml
│       │   └── chat_observer_card.xml
│       └── scss/
│           └── chat_observer.scss
└── security/
    └── ir.model.access.csv
```

---

## Seção 3: Parâmetros de Sistema

Criados em `data/chat_observer_data.xml` com valores padrão na instalação. Editáveis em **Configurações → Parâmetros → Parâmetros do Sistema**. Não são sobrescritos em atualizações.

| Chave (`ir.config_parameter`) | Padrão | Descrição |
|---|---|---|
| `chat_observer.api_base_url` | `""` | URL base da API externa. Vazio = modo não configurado |
| `chat_observer.api_chats_path` | `/chats/phases` | Path do endpoint de fases (relativo à base URL) |
| `chat_observer.api_history_path` | `/chats/{phone}/history` | Path do endpoint de histórico (`{phone}` é substituído) |
| `chat_observer.api_send_path` | `/chats/{phone}/message` | Path do endpoint de envio de mensagem (`{phone}` é substituído) |
| `chat_observer.refresh_interval` | `30` | Intervalo de atualização automática (segundos) |
| `chat_observer.yellow_threshold` | `5` | Minutos sem progresso para classificar chat como amarelo |

---

## Seção 4: Controller Python (Proxy)

**Arquivo:** `controllers/chat_observer.py`  
**Autenticação:** `auth="user"` em todos os endpoints — apenas usuários autenticados no Odoo.

### Endpoints

| Rota | Método | Descrição |
|---|---|---|
| `/chat_observer/chats` | GET | Retorna lista de chats com cor calculada + KPIs |
| `/chat_observer/history/<phone>` | GET | Retorna histórico completo do chat |
| `/chat_observer/send` | POST | Envia mensagem para o cliente |

### Lógica de `/chat_observer/chats`

1. Lê `api_base_url`, `api_chats_path`, `yellow_threshold` do `ir.config_parameter`
2. Se `api_base_url` vazio → retorna `{"error": "api_not_configured"}`
3. Chama `GET {api_base_url}{api_chats_path}` com `requests`
4. Para cada chat recebido, calcula `color`:
   - `phase in ("operator", "error")` → `"red"`
   - `updated_at` há mais de `yellow_threshold` minutos → `"yellow"`
   - Caso contrário → `"green"`
5. Exclui chats com `phase == "completed"`
6. Ordena: vermelho → amarelo → verde
7. Calcula KPIs contando por cor:
   - `total`: total de chats na lista
   - `in_progress`: chats com `color == "green"`
   - `attention`: chats com `color == "yellow"`
   - `action_required`: chats com `color == "red"`
8. Retorna JSON consolidado

### JSON retornado por `/chat_observer/chats`

```json
{
  "chats": [
    {
      "phone_number": "5511999990001",
      "phase": "operator",
      "color": "red",
      "elapsed_minutes": 18,
      "collected": {
        "product": true,
        "customer": false,
        "address": false,
        "payment": false
      }
    }
  ],
  "kpis": {
    "total": 19,
    "in_progress": 14,
    "attention": 3,
    "action_required": 2
  }
}
```

### Segurança

- `api_base_url` e eventuais tokens nunca trafegam para o browser
- O parâmetro `phone` em `/chat_observer/history/<phone>` é validado como somente dígitos antes de ser repassado à API (previne path traversal)

### Tratamento de Erros

| Situação | Resposta |
|---|---|
| `api_base_url` não configurado | `{"error": "api_not_configured"}` |
| API externa indisponível (timeout/connection error) | `{"error": "api_unavailable"}` |
| API retorna status ≥ 400 | `{"error": "api_error", "status": <código>}` |
| Chat não encontrado no histórico | `{"error": "not_found"}` |
| Falha ao enviar mensagem | `{"error": "send_failed"}` |

Em todos os casos de erro o dashboard exibe um banner informativo e continua o polling — nunca quebra a tela.

---

## Seção 5: Componente OWL (Frontend)

### `chat_observer_dashboard.js` — componente raiz

**Ciclo de vida:**

1. `onMounted`: lê `refresh_interval` via RPC, inicia polling com `setInterval`
2. A cada N segundos: chama `GET /chat_observer/chats`, atualiza estado reativo
3. `onWillUnmount`: limpa o intervalo

**Estado reativo:**

```js
this.state = useState({
  chats: [],
  kpis: { total: 0, in_progress: 0, attention: 0, action_required: 0 },
  error: null,           // "api_not_configured" | "api_unavailable" | null
  selectedChat: null,    // chat aberto no modal
  modalHistory: [],      // histórico carregado
  modalLoading: false,
  sendLoading: false,
  sendMessage: "",
});
```

**Interação com o modal:**

- Clique num card → `selectedChat = chat`, `modalLoading = true`, chama `GET /chat_observer/history/<phone>`
- Ao receber histórico → `modalHistory = resultado`, `modalLoading = false`
- Envio de mensagem → `sendLoading = true`, `POST /chat_observer/send`, feedback inline, `sendLoading = false`
- Fechar modal → `selectedChat = null`, `modalHistory = []`

### `chat_observer_card.js` — componente do card

Props recebidas: `chat` (objeto com `phone_number`, `phase`, `color`, `elapsed_minutes`).  
Emite: evento `open-chat` com o `phone_number` ao clicar.  
Sem estado próprio — puramente apresentacional.

---

## Seção 6: Layout Visual

### Dashboard principal

```
┌─────────────────────────────────────────────────────┐
│  [19 TOTAL]  [14 ANDAMENTO]  [3 ATENÇÃO]  [2 AÇÃO]  │  ← KPIs grandes
├─────────────────────────────────────────────────────┤
│  ■ REQUER AÇÃO          ■ REQUER AÇÃO                │
│  +55 11 9999-0001       +55 11 9888-0009             │  ← cards vermelhos
│  operator · 18min       error · 22min                │
│                                                      │
│  ■ ATENÇÃO              ■ ATENÇÃO                    │
│  +55 21 8888-0002       +55 31 7712-0041             │  ← cards amarelos
│  collecting_payment...  collecting_address...        │
│                                                      │
│  ■ NORMAL               ■ NORMAL                     │
│  +55 31 7777-0003       +55 41 6600-0014             │  ← cards verdes
│  collecting_product...  collecting_address...        │
│                                              ↻ 5s   │
└─────────────────────────────────────────────────────┘
```

Cards com borda lateral colorida (4px). Ordenação: vermelho → amarelo → verde. Grid responsivo de 3 colunas. Fase `completed` nunca exibida.

### Modal de detalhe (ao clicar num card)

```
┌──────────────────────────────────────┐
│  +55 11 9999-0001          [✕ fechar]│
│  ● operator · 18min                  │
│  ┌────────────────────────────────┐  │
│  │ [histórico do chat]            │  │
│  │ Cliente: Quero um pastel...    │  │
│  │ IA: Qual sabor?                │  │
│  │ Cliente: De queijo             │  │
│  └────────────────────────────────┘  │
│  [Digite uma mensagem...   ] [Enviar]│
└──────────────────────────────────────┘
```

Modal centralizado com overlay escuro. Campo de texto livre. Botão desabilitado durante envio. A fase continua sendo atualizada pela API — o modal não altera a fase.

---

## Seção 7: Manifest

```python
{
    "name": "Chat Observer",
    "version": "19.0.1.0.0",
    "summary": "Monitoramento em tempo real de chats em andamento",
    "author": "Uduu",
    "website": "",
    "category": "Customizations",
    "license": "LGPL-3",
    "depends": ["uduu_base", "web"],
    "data": [
        "security/ir.model.access.csv",
        "data/chat_observer_data.xml",
        "views/chat_observer_action.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "chat_observer/static/src/scss/chat_observer.scss",
            "chat_observer/static/src/js/chat_observer_dashboard.js",
            "chat_observer/static/src/js/chat_observer_card.js",
            "chat_observer/static/src/xml/chat_observer_dashboard.xml",
            "chat_observer/static/src/xml/chat_observer_card.xml",
        ],
    },
    "installable": True,
    "auto_install": False,
    "application": True,
}
```

---

## Fora do Escopo

- Tela de configuração própria (usa Parâmetros do Sistema nativos do Odoo)
- Controle de acesso por grupo (todos os usuários internos têm acesso)
- Persistência local de chats no banco Odoo
- Notificações push / som de alerta
- Histórico de intervenções do operador
