# Company Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar campo `description` em `res.company`, sincronizar dados da empresa com API externa via POST síncrono a cada create/write, e renomear os `ir.config_parameter` do `chat_observer` para namespace `uduu_`.

**Architecture:** O módulo `uduu_company_sync` herda `res.company` via `_inherit`, sobrescreve `create`/`write`, e chama `requests.post` dentro da transação — qualquer falha levanta `UserError` e faz rollback automático. O `chat_observer` passa por renomeação de chaves de parâmetros (com script de migração SQL para instalações existentes) e bump de versão.

**Tech Stack:** Odoo 19 Community, Python 3.12, `requests` (já disponível na imagem), `ir.config_parameter` para configuração, `odoo.exceptions.UserError` para bloqueio de save.

---

## Mapa de arquivos

### chat_observer (modificações)
| Arquivo | Ação |
|---------|------|
| `addons/chat_observer/__manifest__.py` | Bump versão `19.0.1.0.0` → `19.0.1.1.0` |
| `addons/chat_observer/data/chat_observer_data.xml` | Renomear todas as chaves + remover `api_base_url` do módulo, adicionar `uduu_common.api_base_url` |
| `addons/chat_observer/controllers/chat_observer.py` | Atualizar todas as chamadas `_get_param` |
| `addons/chat_observer/migrations/19.0.1.1.0/__init__.py` | Criar (vazio) |
| `addons/chat_observer/migrations/19.0.1.1.0/post-rename-params.py` | Criar — renomeia chaves no banco |

### uduu_company_sync (novo módulo)
| Arquivo | Ação |
|---------|------|
| `addons/uduu_company_sync/__init__.py` | Criar |
| `addons/uduu_company_sync/__manifest__.py` | Criar |
| `addons/uduu_company_sync/models/__init__.py` | Criar |
| `addons/uduu_company_sync/models/res_company.py` | Criar — campo description + override create/write + _sync_to_api |
| `addons/uduu_company_sync/views/res_company_views.xml` | Criar — herda form, adiciona campo description |
| `addons/uduu_company_sync/data/uduu_company_sync_data.xml` | Criar — ir.config_parameter get/post paths |
| `addons/uduu_company_sync/tests/__init__.py` | Criar |
| `addons/uduu_company_sync/tests/test_res_company_sync.py` | Criar — testes da lógica de sync |

---

## Task 1: Renomear parâmetros do chat_observer — data XML e controller

**Files:**
- Modify: `addons/chat_observer/data/chat_observer_data.xml`
- Modify: `addons/chat_observer/controllers/chat_observer.py`

- [ ] **Step 1: Substituir conteúdo do data XML**

Conteúdo completo novo de `addons/chat_observer/data/chat_observer_data.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo noupdate="1">
    <record id="param_common_api_base_url" model="ir.config_parameter">
        <field name="key">uduu_common.api_base_url</field>
        <field name="value"></field>
    </record>
    <record id="param_api_chats_path" model="ir.config_parameter">
        <field name="key">uduu_chat_observer.api_chats_path</field>
        <field name="value">/chats/phases</field>
    </record>
    <record id="param_api_history_path" model="ir.config_parameter">
        <field name="key">uduu_chat_observer.api_history_path</field>
        <field name="value">/chats/{phone}/history</field>
    </record>
    <record id="param_api_send_path" model="ir.config_parameter">
        <field name="key">uduu_chat_observer.api_send_path</field>
        <field name="value">/meta/whatsapp/webhooks</field>
    </record>
    <record id="param_wa_phone_number_id" model="ir.config_parameter">
        <field name="key">uduu_chat_observer.wa_phone_number_id</field>
        <field name="value"></field>
    </record>
    <record id="param_history_refresh_interval" model="ir.config_parameter">
        <field name="key">uduu_chat_observer.history_refresh_interval</field>
        <field name="value">5</field>
    </record>
    <record id="param_refresh_interval" model="ir.config_parameter">
        <field name="key">uduu_chat_observer.refresh_interval</field>
        <field name="value">30</field>
    </record>
    <record id="param_yellow_threshold" model="ir.config_parameter">
        <field name="key">uduu_chat_observer.yellow_threshold</field>
        <field name="value">5</field>
    </record>
</odoo>
```

- [ ] **Step 2: Atualizar controller — substituir todas as referências de chave**

Conteúdo completo novo de `addons/chat_observer/controllers/chat_observer.py`:

```python
import json
import logging
import time

import requests

from odoo import http
from odoo.http import request

from odoo.addons.chat_observer.utils.chat_phases import process_chats

_logger = logging.getLogger(__name__)


def _json_response(data, status=200):
    return request.make_response(
        json.dumps(data),
        headers=[("Content-Type", "application/json")],
        status=status,
    )


def _get_param(key, default=""):
    return request.env["ir.config_parameter"].sudo().get_param(key, default)


class ChatObserverController(http.Controller):

    @http.route("/chat_observer/chats", type="http", auth="user", methods=["GET"], csrf=False)
    def get_chats(self):
        api_base_url = _get_param("uduu_common.api_base_url")
        if not api_base_url:
            return _json_response({"error": "api_not_configured"}, status=503)

        api_chats_path = _get_param("uduu_chat_observer.api_chats_path", "/chats/phases")
        try:
            yellow_threshold = int(_get_param("uduu_chat_observer.yellow_threshold", "5"))
        except ValueError:
            yellow_threshold = 5

        try:
            resp = requests.get(f"{api_base_url}{api_chats_path}", timeout=10)
            resp.raise_for_status()
            raw_chats = resp.json()
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            _logger.warning("chat_observer: API unavailable: %s", e)
            return _json_response({"error": "api_unavailable"})
        except requests.exceptions.HTTPError as e:
            _logger.warning("chat_observer: API error %s: %s", resp.status_code, e)
            return _json_response({"error": "api_error", "status": resp.status_code})

        return _json_response(process_chats(raw_chats, yellow_threshold))

    @http.route("/chat_observer/history/<phone>", type="http", auth="user", methods=["GET"], csrf=False)
    def get_history(self, phone):
        if not phone.isdigit() or not (7 <= len(phone) <= 15):
            return _json_response({"error": "invalid_phone"}, status=400)

        api_base_url = _get_param("uduu_common.api_base_url")
        if not api_base_url:
            return _json_response({"error": "api_not_configured"}, status=503)

        path = _get_param("uduu_chat_observer.api_history_path", "/uduu/chats/history")

        try:
            resp = requests.get(f"{api_base_url}{path}", params={"phone": phone}, timeout=10)
            if resp.status_code == 404:
                return _json_response({"error": "not_found"}, status=404)
            resp.raise_for_status()
            return request.make_response(resp.text, headers=[("Content-Type", "application/json")])
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            _logger.warning("chat_observer: API unavailable: %s", e)
            return _json_response({"error": "api_unavailable"})
        except requests.exceptions.HTTPError as e:
            _logger.warning("chat_observer: API error %s: %s | body: %s", resp.status_code, e, resp.text[:500])
            return _json_response({"error": "api_error", "status": resp.status_code})

    @http.route("/chat_observer/send", type="http", auth="user", methods=["POST"], csrf=False)
    def send_message(self):
        try:
            body = json.loads(request.httprequest.data)
        except (json.JSONDecodeError, AttributeError):
            return _json_response({"error": "invalid_payload"}, status=400)

        phone_number = body.get("phone_number", "")
        message = body.get("message", "").strip()

        if not phone_number.isdigit() or not (7 <= len(phone_number) <= 15):
            return _json_response({"error": "invalid_phone"}, status=400)
        if not message:
            return _json_response({"error": "empty_message"}, status=400)

        api_base_url = _get_param("uduu_common.api_base_url")
        if not api_base_url:
            return _json_response({"error": "api_not_configured"}, status=503)

        path = _get_param("uduu_chat_observer.api_send_path", "/meta/whatsapp/webhooks")
        phone_number_id = _get_param("uduu_chat_observer.wa_phone_number_id", "")

        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "",
                                    "phone_number_id": phone_number_id,
                                },
                                "contacts": [
                                    {
                                        "profile": {"name": ""},
                                        "wa_id": phone_number,
                                    }
                                ],
                                "messages": [
                                    {
                                        "from": phone_number,
                                        "id": "",
                                        "timestamp": str(int(time.time())),
                                        "text": {"body": message},
                                        "type": "text",
                                    }
                                ],
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }

        try:
            resp = requests.post(f"{api_base_url}{path}", json=payload, timeout=10)
            resp.raise_for_status()
            return _json_response({"success": True})
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            _logger.warning("chat_observer: API unavailable: %s", e)
            return _json_response({"error": "api_unavailable"})
        except requests.exceptions.HTTPError as e:
            _logger.warning("chat_observer: API error %s: %s", resp.status_code, e)
            return _json_response({"error": "send_failed"})
```

- [ ] **Step 3: Verificar que os testes existentes do chat_observer ainda passam**

```bash
docker compose exec odoo odoo -u chat_observer -d uduu --test-enable --test-tags /chat_observer --stop-after-init 2>&1 | tail -20
```

Esperado: nenhum `FAILED` ou `ERROR` nos testes de `chat_phases`.

---

## Task 2: Adicionar script de migração ao chat_observer

**Files:**
- Create: `addons/chat_observer/migrations/19.0.1.1.0/__init__.py`
- Create: `addons/chat_observer/migrations/19.0.1.1.0/post-rename-params.py`

- [ ] **Step 1: Criar `__init__.py` vazio**

```python
```

(arquivo vazio)

- [ ] **Step 2: Criar `post-rename-params.py`**

```python
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
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
        cr.execute(
            "UPDATE ir_config_parameter SET key = %s WHERE key = %s",
            (new_key, old_key),
        )
        if cr.rowcount:
            _logger.info("uduu: renamed ir.config_parameter %s → %s", old_key, new_key)
```

---

## Task 3: Bump versão do chat_observer e commitar

**Files:**
- Modify: `addons/chat_observer/__manifest__.py`

- [ ] **Step 1: Atualizar versão no manifest**

Em `addons/chat_observer/__manifest__.py`, alterar:

```python
"version": "19.0.1.1.0",
```

- [ ] **Step 2: Commitar todas as alterações do chat_observer**

```bash
git add addons/chat_observer/
git commit -m "refactor: rename chat_observer ir.config_parameter keys to uduu_ namespace"
```

---

## Task 4: Criar scaffold do módulo uduu_company_sync

**Files:**
- Create: `addons/uduu_company_sync/__init__.py`
- Create: `addons/uduu_company_sync/__manifest__.py`
- Create: `addons/uduu_company_sync/models/__init__.py`
- Create: `addons/uduu_company_sync/models/res_company.py`
- Create: `addons/uduu_company_sync/views/res_company_views.xml`
- Create: `addons/uduu_company_sync/data/uduu_company_sync_data.xml`
- Create: `addons/uduu_company_sync/tests/__init__.py`
- Create: `addons/uduu_company_sync/tests/test_res_company_sync.py`

- [ ] **Step 1: Criar `__init__.py` do módulo**

`addons/uduu_company_sync/__init__.py`:
```python
from . import models
```

- [ ] **Step 2: Criar `__manifest__.py`**

`addons/uduu_company_sync/__manifest__.py`:
```python
{
    "name": "Uduu Company Sync",
    "version": "19.0.1.0.0",
    "summary": "Syncs res.company to external API on create/write",
    "author": "Uduu",
    "category": "Customizations",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "data/uduu_company_sync_data.xml",
        "views/res_company_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
}
```

- [ ] **Step 3: Criar `models/__init__.py`**

`addons/uduu_company_sync/models/__init__.py`:
```python
from . import res_company
```

- [ ] **Step 4: Criar `models/res_company.py` com stub (sem lógica ainda)**

`addons/uduu_company_sync/models/res_company.py`:
```python
import logging

import requests

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    description = fields.Text(string="Descrição")

    def _get_param(self, key, default=""):
        return self.env["ir.config_parameter"].sudo().get_param(key, default)

    def _build_sync_payload(self):
        self.ensure_one()
        return {}

    def _sync_to_api(self):
        self.ensure_one()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record._sync_to_api()
        return records

    def write(self, vals):
        result = super().write(vals)
        for record in self:
            record._sync_to_api()
        return result
```

- [ ] **Step 5: Criar `views/res_company_views.xml`**

`addons/uduu_company_sync/views/res_company_views.xml`:
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_company_form_description" model="ir.ui.view">
        <field name="name">res.company.form.description</field>
        <field name="model">res.company</field>
        <field name="inherit_id" ref="base.view_company_form"/>
        <field name="arch" type="xml">
            <xpath expr="//field[@name='website']" position="after">
                <field name="description"/>
            </xpath>
        </field>
    </record>
</odoo>
```

- [ ] **Step 6: Criar `data/uduu_company_sync_data.xml`**

`addons/uduu_company_sync/data/uduu_company_sync_data.xml`:
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo noupdate="1">
    <record id="param_api_get_path" model="ir.config_parameter">
        <field name="key">uduu_company_sync.api_get_path</field>
        <field name="value">/odoo/company</field>
    </record>
    <record id="param_api_post_path" model="ir.config_parameter">
        <field name="key">uduu_company_sync.api_post_path</field>
        <field name="value">/odoo/company</field>
    </record>
</odoo>
```

- [ ] **Step 7: Criar `tests/__init__.py`**

`addons/uduu_company_sync/tests/__init__.py`:
```python
from . import test_res_company_sync
```

- [ ] **Step 8: Criar arquivo de testes com stub vazio por ora**

`addons/uduu_company_sync/tests/test_res_company_sync.py`:
```python
from odoo.tests import TransactionCase


class TestResCompanySync(TransactionCase):
    pass
```

- [ ] **Step 9: Instalar o módulo no banco de dev para validar scaffold**

```bash
docker compose exec odoo odoo -i uduu_company_sync -d uduu --stop-after-init 2>&1 | tail -20
```

Esperado: sem `ERROR` na saída. O módulo deve aparecer como instalado.

---

## Task 5: Escrever testes com falha esperada

**Files:**
- Modify: `addons/uduu_company_sync/tests/test_res_company_sync.py`

- [ ] **Step 1: Substituir o conteúdo do arquivo de testes**

`addons/uduu_company_sync/tests/test_res_company_sync.py`:
```python
from unittest.mock import MagicMock, patch

import requests

from odoo.exceptions import UserError
from odoo.tests import TransactionCase


class TestResCompanySync(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env.ref("base.main_company")
        self.env["ir.config_parameter"].sudo().set_param(
            "uduu_common.api_base_url", "http://test.example.com"
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "uduu_company_sync.api_post_path", "/odoo/company"
        )

    def _ok_mock(self):
        mock = MagicMock()
        mock.status_code = 200
        mock.raise_for_status = MagicMock()
        return mock

    @patch("odoo.addons.uduu_company_sync.models.res_company.requests.post")
    def test_write_calls_post_with_correct_url(self, mock_post):
        mock_post.return_value = self._ok_mock()
        self.company.write({"name": self.company.name})
        mock_post.assert_called_once()
        url = mock_post.call_args[0][0]
        self.assertEqual(url, "http://test.example.com/odoo/company")

    @patch("odoo.addons.uduu_company_sync.models.res_company.requests.post")
    def test_create_calls_post_endpoint(self, mock_post):
        mock_post.return_value = self._ok_mock()
        new_company = self.env["res.company"].create({"name": "Empresa Teste"})
        mock_post.assert_called_once()
        payload = mock_post.call_args[1]["json"]
        self.assertEqual(payload["odoo_company_id"], new_company.id)
        self.assertEqual(payload["name"], "Empresa Teste")

    def test_write_blocks_when_base_url_empty(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "uduu_common.api_base_url", ""
        )
        with self.assertRaises(UserError):
            self.company.write({"name": self.company.name})

    @patch("odoo.addons.uduu_company_sync.models.res_company.requests.post")
    def test_write_blocks_on_connection_error(self, mock_post):
        mock_post.side_effect = requests.exceptions.ConnectionError("refused")
        with self.assertRaises(UserError):
            self.company.write({"name": self.company.name})

    @patch("odoo.addons.uduu_company_sync.models.res_company.requests.post")
    def test_write_blocks_on_timeout(self, mock_post):
        mock_post.side_effect = requests.exceptions.Timeout("timeout")
        with self.assertRaises(UserError):
            self.company.write({"name": self.company.name})

    @patch("odoo.addons.uduu_company_sync.models.res_company.requests.post")
    def test_write_blocks_on_http_error(self, mock_post):
        mock = MagicMock()
        mock.status_code = 500
        mock.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
        mock_post.return_value = mock
        with self.assertRaises(UserError):
            self.company.write({"name": self.company.name})

    @patch("odoo.addons.uduu_company_sync.models.res_company.requests.post")
    def test_street_split_before_comma(self, mock_post):
        mock_post.return_value = self._ok_mock()
        self.company.write({"street": "Rua das Flores, 123"})
        payload = mock_post.call_args[1]["json"]
        self.assertEqual(payload["address"]["street"], "Rua das Flores")
        self.assertEqual(payload["address"]["number"], "123")

    @patch("odoo.addons.uduu_company_sync.models.res_company.requests.post")
    def test_street_without_comma_has_empty_number(self, mock_post):
        mock_post.return_value = self._ok_mock()
        self.company.write({"street": "Rua das Flores"})
        payload = mock_post.call_args[1]["json"]
        self.assertEqual(payload["address"]["street"], "Rua das Flores")
        self.assertEqual(payload["address"]["number"], "")

    @patch("odoo.addons.uduu_company_sync.models.res_company.requests.post")
    def test_street2_maps_to_neighborhood(self, mock_post):
        mock_post.return_value = self._ok_mock()
        self.company.write({"street2": "Centro"})
        payload = mock_post.call_args[1]["json"]
        self.assertEqual(payload["address"]["neighborhood"], "Centro")

    @patch("odoo.addons.uduu_company_sync.models.res_company.requests.post")
    def test_state_name_sent_not_code(self, mock_post):
        mock_post.return_value = self._ok_mock()
        state = self.env["res.country.state"].search(
            [("country_id.code", "=", "BR"), ("code", "=", "SP")], limit=1
        )
        if not state:
            self.skipTest("Estado SP/BR não encontrado no banco de teste")
        self.company.write({"state_id": state.id})
        payload = mock_post.call_args[1]["json"]
        self.assertEqual(payload["address"]["state"], state.name)
        self.assertNotEqual(payload["address"]["state"], "SP")

    @patch("odoo.addons.uduu_company_sync.models.res_company.requests.post")
    def test_country_name_sent_not_code(self, mock_post):
        mock_post.return_value = self._ok_mock()
        country = self.env["res.country"].search([("code", "=", "BR")], limit=1)
        if not country:
            self.skipTest("País BR não encontrado no banco de teste")
        self.company.write({"country_id": country.id})
        payload = mock_post.call_args[1]["json"]
        self.assertEqual(payload["address"]["country"], country.name)
        self.assertNotEqual(payload["address"]["country"], "BR")

    @patch("odoo.addons.uduu_company_sync.models.res_company.requests.post")
    def test_description_field_in_payload(self, mock_post):
        mock_post.return_value = self._ok_mock()
        self.company.write({"description": "Tecnologia para vendas conversacionais"})
        payload = mock_post.call_args[1]["json"]
        self.assertEqual(payload["description"], "Tecnologia para vendas conversacionais")

    @patch("odoo.addons.uduu_company_sync.models.res_company.requests.post")
    def test_payload_has_all_required_fields(self, mock_post):
        mock_post.return_value = self._ok_mock()
        self.company.write({"name": self.company.name})
        payload = mock_post.call_args[1]["json"]
        for field in ("odoo_company_id", "name", "phone", "email", "website", "description", "address"):
            self.assertIn(field, payload)
        for addr_field in ("street", "number", "complement", "neighborhood", "city", "state", "zip_code", "country"):
            self.assertIn(addr_field, payload["address"])
```

- [ ] **Step 2: Rodar os testes — confirmar falhas**

```bash
docker compose exec odoo odoo -u uduu_company_sync -d uduu --test-enable --test-tags /uduu_company_sync --stop-after-init 2>&1 | grep -E "FAIL|ERROR|OK|test_"
```

Esperado: vários `FAIL` — os testes de URL, payload e bloqueio falharão pois `_sync_to_api` e `_build_sync_payload` ainda são stubs vazios.

---

## Task 6: Implementar ResCompany — payload e lógica de sync

**Files:**
- Modify: `addons/uduu_company_sync/models/res_company.py`

- [ ] **Step 1: Substituir conteúdo com implementação completa**

`addons/uduu_company_sync/models/res_company.py`:
```python
import logging

import requests

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    description = fields.Text(string="Descrição")

    def _get_param(self, key, default=""):
        return self.env["ir.config_parameter"].sudo().get_param(key, default)

    def _build_sync_payload(self):
        self.ensure_one()
        street_parts = (self.street or "").split(",", 1)
        street_name = street_parts[0].strip()
        street_number = street_parts[1].strip() if len(street_parts) > 1 else ""
        return {
            "odoo_company_id": self.id,
            "name": self.name,
            "phone": self.phone or "",
            "email": self.email or "",
            "website": self.website or "",
            "description": self.description or "",
            "address": {
                "street": street_name,
                "number": street_number,
                "complement": "",
                "neighborhood": self.street2 or "",
                "city": self.city or "",
                "state": self.state_id.name if self.state_id else "",
                "zip_code": self.zip or "",
                "country": self.country_id.name if self.country_id else "",
            },
        }

    def _sync_to_api(self):
        self.ensure_one()
        base_url = self._get_param("uduu_common.api_base_url")
        if not base_url:
            raise UserError(
                "Integração com API não configurada. "
                "Defina 'uduu_common.api_base_url' em Técnico → Parâmetros do Sistema."
            )
        post_path = self._get_param("uduu_company_sync.api_post_path", "/odoo/company")
        url = f"{base_url}{post_path}"
        payload = self._build_sync_payload()
        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
        except requests.exceptions.ConnectionError as e:
            _logger.error("uduu_company_sync: API indisponível: %s", e)
            raise UserError(
                f"Não foi possível conectar à API ({base_url}). Verifique a conexão."
            ) from e
        except requests.exceptions.Timeout as e:
            _logger.error("uduu_company_sync: Timeout: %s", e)
            raise UserError(
                f"Timeout ao chamar a API ({base_url}). Tente novamente."
            ) from e
        except requests.exceptions.HTTPError as e:
            _logger.error("uduu_company_sync: HTTP %s: %s", resp.status_code, e)
            raise UserError(
                f"Erro na API ao sincronizar empresa: HTTP {resp.status_code}."
            ) from e

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record._sync_to_api()
        return records

    def write(self, vals):
        result = super().write(vals)
        for record in self:
            record._sync_to_api()
        return result
```

---

## Task 7: Rodar testes e verificar aprovação

- [ ] **Step 1: Atualizar e rodar testes**

```bash
docker compose exec odoo odoo -u uduu_company_sync -d uduu --test-enable --test-tags /uduu_company_sync --stop-after-init 2>&1 | grep -E "FAIL|ERROR|OK|Ran [0-9]"
```

Esperado: `Ran 12 tests` com resultado `OK`. Nenhum `FAIL` ou `ERROR`.

- [ ] **Step 2: Commitar implementação e testes**

```bash
git add addons/uduu_company_sync/
git commit -m "feat: add uduu_company_sync — description field and API sync on company create/write"
```

---

## Self-review (executado pelo agente antes de marcar completo)

- [x] **Cobertura do spec:** campo description ✓, override create ✓, override write ✓, POST síncrono ✓, rollback em erro ✓, ir.config_parameter get/post path ✓, renomeação chat_observer ✓, migração SQL ✓, view description ✓
- [x] **Placeholders:** nenhum TBD/TODO no plano
- [x] **Consistência de tipos:** `_build_sync_payload` retorna dict, `_sync_to_api` chama `_build_sync_payload` — consistente em Task 4 (stub) e Task 6 (implementação)
- [x] **`@api.model_create_multi`:** assinatura `create(self, vals_list)` usada em Task 4 e Task 6 — consistente
