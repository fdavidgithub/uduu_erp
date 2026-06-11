---
name: company-sync-design
description: Design do módulo uduu_company_sync — campo description em res.company e sincronização síncrona com API externa; inclui renomeação de parâmetros do chat_observer para namespace uduu_
metadata:
  type: project
---

# Design: uduu_company_sync + renomeação de parâmetros

**Data:** 2026-06-05  
**Escopo:** Novo módulo `uduu_company_sync` + refatoração de namespaces de configuração do `chat_observer`

---

## 1. Contexto

O Odoo precisa manter um serviço externo atualizado sempre que o cadastro de uma empresa (`res.company`) for criado ou alterado. O campo `description` (segmento/ramo de atuação) não existe nativamente e deve ser adicionado. Aproveita-se a oportunidade para padronizar os namespaces dos `ir.config_parameter` existentes no `chat_observer`.

---

## 2. Módulos afetados

| Módulo | Alteração |
|--------|-----------|
| `uduu_company_sync` | Novo módulo |
| `chat_observer` | Renomeação de parâmetros + migração de banco |

---

## 3. Módulo `uduu_company_sync`

### 3.1 Estrutura de arquivos

```
addons/uduu_company_sync/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── res_company.py
├── views/
│   └── res_company_views.xml
├── data/
│   └── uduu_company_sync_data.xml
└── security/
    └── ir.model.access.csv
```

### 3.2 Manifest

- `name`: "Uduu Company Sync"
- `version`: "19.0.1.0.0"
- `depends`: `["base"]`
- `license`: `LGPL-3`

### 3.3 Campo novo

`res.company` recebe um único campo novo:

```python
description = fields.Text(string="Descrição")
```

Exibido no formulário da empresa em uma aba ou após o campo `website`.

### 3.4 Lógica de sincronização

Override de `create` e `write` em `res.company`:

```python
def create(self, vals):
    record = super().create(vals)
    record._sync_to_api()
    return record

def write(self, vals):
    result = super().write(vals)
    for record in self:
        record._sync_to_api()
    return result
```

O método `_sync_to_api`:
1. Lê `uduu_common.api_base_url` via `ir.config_parameter`. Se vazio → `UserError`.
2. Lê `uduu_company_sync.api_post_path` (default `/odoo/company`).
3. Monta payload conforme contrato POST (ver seção 5).
4. Chama `requests.post(url, json=payload, timeout=10)`.
5. Exceções `ConnectionError`, `Timeout` → `UserError("API indisponível: ...")`.
6. `HTTPError` (4xx/5xx) → `UserError("Erro na API: HTTP {status}")`.
7. 200 OK → retorna normalmente; Odoo commita a transação.

Como o `UserError` é levantado dentro da transação aberta pelo Odoo, o rollback é automático — o save não persiste se a API falhar.

### 3.5 Mapeamento de campos — payload POST

```python
street_parts = (record.street or "").split(",", 1)
street_name = street_parts[0].strip()
street_number = street_parts[1].strip() if len(street_parts) > 1 else ""

payload = {
    "odoo_company_id": record.id,
    "name": record.name,
    "phone": record.phone or "",
    "email": record.email or "",
    "website": record.website or "",
    "description": record.description or "",
    "address": {
        "street": street_name,
        "number": street_number,
        "complement": "",
        "neighborhood": record.street2 or "",
        "city": record.city or "",
        "state": record.state_id.name if record.state_id else "",
        "zip_code": record.zip or "",
        "country": record.country_id.name if record.country_id else "",
    },
}
```

| Campo API | Origem Odoo | Observação |
|-----------|-------------|------------|
| `odoo_company_id` | `id` | |
| `name` | `name` | |
| `phone` | `phone` | |
| `email` | `email` | |
| `website` | `website` | |
| `description` | `description` | campo novo |
| `address.street` | `street` antes da primeira vírgula | |
| `address.number` | `street` depois da primeira vírgula | string |
| `address.complement` | `""` | sem equivalente nativo |
| `address.neighborhood` | `street2` | |
| `address.city` | `city` | |
| `address.state` | `state_id.name` | nome completo, não código |
| `address.zip_code` | `zip` | |
| `address.country` | `country_id.name` | nome completo, não código |

### 3.6 Parâmetros de configuração

Definidos em `data/uduu_company_sync_data.xml` com `noupdate="1"`:

| Chave | Valor padrão |
|-------|-------------|
| `uduu_company_sync.api_get_path` | `/odoo/company` |
| `uduu_company_sync.api_post_path` | `/odoo/company` |

A URL base é lida de `uduu_common.api_base_url` (definida no `chat_observer`).

---

## 4. Refatoração: `chat_observer`

### 4.1 Renomeação de parâmetros

| Chave antiga | Chave nova |
|-------------|-----------|
| `chat_observer.api_base_url` | `uduu_common.api_base_url` |
| `chat_observer.api_chats_path` | `uduu_chat_observer.api_chats_path` |
| `chat_observer.api_history_path` | `uduu_chat_observer.api_history_path` |
| `chat_observer.api_send_path` | `uduu_chat_observer.api_send_path` |
| `chat_observer.wa_phone_number_id` | `uduu_chat_observer.wa_phone_number_id` |
| `chat_observer.history_refresh_interval` | `uduu_chat_observer.history_refresh_interval` |
| `chat_observer.refresh_interval` | `uduu_chat_observer.refresh_interval` |
| `chat_observer.yellow_threshold` | `uduu_chat_observer.yellow_threshold` |

### 4.2 Arquivos alterados no `chat_observer`

- `data/chat_observer_data.xml` — chaves atualizadas; registro `param_api_base_url` renomeado para `uduu_common.api_base_url`
- `controllers/chat_observer.py` — todas as chamadas `_get_param("chat_observer.*")` atualizadas
- `__manifest__.py` — versão bumped para `19.0.1.1.0`

### 4.3 Migração de banco

Script `migrations/19.0.1.1.0/post-rename-params.py` que faz UPDATE nas chaves existentes em `ir.config_parameter` para instalações já rodando:

```python
# Renomeia chaves existentes sem perder os valores
renames = {
    "chat_observer.api_base_url": "uduu_common.api_base_url",
    "chat_observer.api_chats_path": "uduu_chat_observer.api_chats_path",
    "chat_observer.api_history_path": "uduu_chat_observer.api_history_path",
    "chat_observer.api_send_path": "uduu_chat_observer.api_send_path",
    "chat_observer.wa_phone_number_id": "uduu_chat_observer.wa_phone_number_id",
    "chat_observer.history_refresh_interval": "uduu_chat_observer.history_refresh_interval",
    "chat_observer.refresh_interval": "uduu_chat_observer.refresh_interval",
    "chat_observer.yellow_threshold": "uduu_chat_observer.yellow_threshold",
}
for old_key, new_key in renames.items():
    env["ir.config_parameter"].search([("key", "=", old_key)]).write({"key": new_key})
```

---

## 5. Contrato da API (referência)

### GET `/odoo/company?odoo_company_id={id}`

Resposta 200:
```json
{
  "odoo_company_id": 1,
  "name": "UDUU Soluções Ltda",
  "phone": "+55 11 99999-0000",
  "email": "contato@uduu.com.br",
  "website": "https://uduu.com.br",
  "description": "Tecnologia para vendas conversacionais",
  "address": { "street": "...", "number": "...", "complement": "...",
                "neighborhood": "...", "city": "...", "state": "...",
                "zip_code": "...", "country": "..." },
  "updated_at": "2026-06-05T14:30:00.000000+00:00"
}
```

### POST `/odoo/company`

Body: payload descrito na seção 3.5.  
Resposta 200: `{"message": "Company profile saved", "item": {"odoo_company_id": 1, "name": "...", "updated_at": "..."}}`

Erros mapeados: 400 (campos inválidos), 404 (não encontrado), 500 (erro interno).

---

## 6. Fora do escopo

- Implementação do GET no Odoo (parâmetro registrado apenas para uso futuro)
- Autenticação no endpoint externo (não mencionada no contrato)
- Sincronização retroativa de empresas existentes
