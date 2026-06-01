# Chat Observer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar o addon `chat_observer` no Odoo 19 que monitora fases de chats em andamento via API externa, exibindo um dashboard com KPIs e cards coloridos por urgência.

**Architecture:** Controller Python atua como proxy entre o componente OWL no browser e a API externa — recebe fases brutas, calcula cores e KPIs, retorna JSON processado. O componente OWL faz polling a cada N segundos e renderiza o dashboard sem recarregar a página. Toda a lógica de cor e KPI vive em `utils/chat_phases.py`, isolada e testável.

**Tech Stack:** Odoo 19 Community, Python 3.12, OWL (Odoo Web Library), QWeb templates, SCSS, `requests` (disponível na imagem oficial Odoo), `unittest`

---

## Mapa de Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `addons/chat_observer/__manifest__.py` | Declaração do módulo, assets, dependências |
| `addons/chat_observer/__init__.py` | Importa `controllers` |
| `addons/chat_observer/controllers/__init__.py` | Importa `chat_observer` |
| `addons/chat_observer/controllers/chat_observer.py` | Proxy HTTP: chama API externa, retorna JSON processado |
| `addons/chat_observer/utils/__init__.py` | Vazio |
| `addons/chat_observer/utils/chat_phases.py` | Funções puras: calcular cor, elapsed, KPIs, ordenar |
| `addons/chat_observer/tests/__init__.py` | Importa `test_chat_phases` |
| `addons/chat_observer/tests/test_chat_phases.py` | Testes unitários das funções puras |
| `addons/chat_observer/data/chat_observer_data.xml` | Parâmetros de sistema com valores padrão (`noupdate="1"`) |
| `addons/chat_observer/views/chat_observer_action.xml` | Client action + menu |
| `addons/chat_observer/security/ir.model.access.csv` | Header vazio (sem modelos) |
| `addons/chat_observer/static/src/js/chat_observer_card.js` | Componente OWL apresentacional do card |
| `addons/chat_observer/static/src/js/chat_observer_dashboard.js` | Componente OWL raiz: polling, estado, modal |
| `addons/chat_observer/static/src/xml/chat_observer_card.xml` | Template QWeb do card |
| `addons/chat_observer/static/src/xml/chat_observer_dashboard.xml` | Template QWeb do dashboard + modal |
| `addons/chat_observer/static/src/scss/chat_observer.scss` | Estilos: KPIs, cards coloridos, modal |

---

## Task 0: Criar branch de desenvolvimento

**Files:**
- (sem arquivos — apenas git)

- [ ] **Step 1: Criar branch a partir de `develop`**

```bash
git checkout develop
git checkout -b feat/chat-observer
```

Expected: `Switched to a new branch 'feat/chat-observer'`

---

## Task 1: Scaffold do módulo

**Files:**
- Create: `addons/chat_observer/__manifest__.py`
- Create: `addons/chat_observer/__init__.py`
- Create: `addons/chat_observer/controllers/__init__.py`
- Create: `addons/chat_observer/utils/__init__.py`
- Create: `addons/chat_observer/tests/__init__.py`
- Create: `addons/chat_observer/security/ir.model.access.csv`
- Create: `addons/chat_observer/data/.gitkeep`
- Create: `addons/chat_observer/views/.gitkeep`
- Create: `addons/chat_observer/static/src/js/.gitkeep`
- Create: `addons/chat_observer/static/src/xml/.gitkeep`
- Create: `addons/chat_observer/static/src/scss/.gitkeep`

- [ ] **Step 1: Criar estrutura de diretórios**

```bash
mkdir -p addons/chat_observer/{controllers,utils,tests,data,views,security}
mkdir -p addons/chat_observer/static/src/{js,xml,scss}
```

- [ ] **Step 2: Criar `__manifest__.py`**

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
            "chat_observer/static/src/xml/chat_observer_card.xml",
            "chat_observer/static/src/xml/chat_observer_dashboard.xml",
            "chat_observer/static/src/js/chat_observer_card.js",
            "chat_observer/static/src/js/chat_observer_dashboard.js",
        ],
    },
    "installable": True,
    "auto_install": False,
    "application": True,
}
```

- [ ] **Step 3: Criar `__init__.py` raiz**

```python
from . import controllers
```

- [ ] **Step 4: Criar `controllers/__init__.py`**

```python
from . import chat_observer
```

- [ ] **Step 5: Criar `utils/__init__.py` e `tests/__init__.py`**

Ambos os arquivos ficam **vazios**.

`utils/__init__.py`: (arquivo vazio)

`tests/__init__.py`:
```python
from . import test_chat_phases
```

- [ ] **Step 6: Criar `security/ir.model.access.csv`**

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
```

- [ ] **Step 7: Commit do scaffold**

```bash
git add addons/chat_observer/
git commit -m "feat: scaffold chat_observer module"
```

---

## Task 2: Lógica de fases — utilitário puro + testes (TDD)

**Files:**
- Create: `addons/chat_observer/utils/chat_phases.py`
- Create: `addons/chat_observer/tests/test_chat_phases.py`

- [ ] **Step 1: Escrever os testes primeiro**

Crie `addons/chat_observer/tests/test_chat_phases.py`:

```python
import unittest
from datetime import datetime, timezone, timedelta


def _ts(minutes_ago):
    """Helper: ISO timestamp N minutos atrás."""
    dt = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _chat(phone, phase, minutes_ago=1, collected=None):
    return {
        "phone_number": phone,
        "phase": phase,
        "updated_at": _ts(minutes_ago),
        "collected": collected or {},
    }


class TestCalculateColor(unittest.TestCase):

    def test_operator_is_red(self):
        from odoo.addons.chat_observer.utils.chat_phases import calculate_color
        self.assertEqual(calculate_color("operator", _ts(1), 5), "red")

    def test_error_is_red(self):
        from odoo.addons.chat_observer.utils.chat_phases import calculate_color
        self.assertEqual(calculate_color("error", _ts(1), 5), "red")

    def test_recent_chat_is_green(self):
        from odoo.addons.chat_observer.utils.chat_phases import calculate_color
        self.assertEqual(calculate_color("collecting_product", _ts(2), 5), "green")

    def test_old_chat_is_yellow(self):
        from odoo.addons.chat_observer.utils.chat_phases import calculate_color
        self.assertEqual(calculate_color("collecting_product", _ts(10), 5), "yellow")

    def test_exactly_at_threshold_is_yellow(self):
        from odoo.addons.chat_observer.utils.chat_phases import calculate_color
        self.assertEqual(calculate_color("collecting_product", _ts(5), 5), "yellow")

    def test_custom_threshold(self):
        from odoo.addons.chat_observer.utils.chat_phases import calculate_color
        self.assertEqual(calculate_color("collecting_customer", _ts(3), 2), "yellow")


class TestProcessChats(unittest.TestCase):

    def test_completed_chats_excluded(self):
        from odoo.addons.chat_observer.utils.chat_phases import process_chats
        result = process_chats([_chat("111", "completed")], 5)
        self.assertEqual(result["chats"], [])

    def test_ordering_red_yellow_green(self):
        from odoo.addons.chat_observer.utils.chat_phases import process_chats
        chats = [
            _chat("green", "collecting_product", minutes_ago=1),
            _chat("yellow", "collecting_product", minutes_ago=10),
            _chat("red", "operator", minutes_ago=1),
        ]
        result = process_chats(chats, 5)
        colors = [c["color"] for c in result["chats"]]
        self.assertEqual(colors, ["red", "yellow", "green"])

    def test_kpis_correct(self):
        from odoo.addons.chat_observer.utils.chat_phases import process_chats
        chats = [
            _chat("a", "collecting_product", minutes_ago=1),
            _chat("b", "collecting_product", minutes_ago=10),
            _chat("c", "operator", minutes_ago=1),
            _chat("d", "completed", minutes_ago=1),
        ]
        result = process_chats(chats, 5)
        self.assertEqual(result["kpis"]["total"], 3)
        self.assertEqual(result["kpis"]["in_progress"], 1)
        self.assertEqual(result["kpis"]["attention"], 1)
        self.assertEqual(result["kpis"]["action_required"], 1)

    def test_elapsed_minutes_in_result(self):
        from odoo.addons.chat_observer.utils.chat_phases import process_chats
        result = process_chats([_chat("111", "collecting_product", minutes_ago=7)], 5)
        self.assertGreaterEqual(result["chats"][0]["elapsed_minutes"], 7)

    def test_empty_list(self):
        from odoo.addons.chat_observer.utils.chat_phases import process_chats
        result = process_chats([], 5)
        self.assertEqual(result["chats"], [])
        self.assertEqual(result["kpis"]["total"], 0)
```

- [ ] **Step 2: Rodar testes — confirmar que falham**

```bash
docker compose exec odoo odoo -i chat_observer -d odoo --test-enable --stop-after-init 2>&1 | grep -E "ERROR|FAIL|chat_phases"
```

Expected: erros de `ImportError` ou `ModuleNotFoundError` para `chat_phases`.

- [ ] **Step 3: Implementar `utils/chat_phases.py`**

```python
from datetime import datetime, timezone

_RED_PHASES = {"operator", "error"}
_COLOR_ORDER = {"red": 0, "yellow": 1, "green": 2}


def calculate_color(phase: str, updated_at: str, yellow_threshold_minutes: int) -> str:
    if phase in _RED_PHASES:
        return "red"
    if calculate_elapsed_minutes(updated_at) >= yellow_threshold_minutes:
        return "yellow"
    return "green"


def calculate_elapsed_minutes(updated_at: str) -> int:
    dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    return int((datetime.now(timezone.utc) - dt).total_seconds() / 60)


def process_chats(raw_chats: list, yellow_threshold_minutes: int) -> dict:
    processed = []
    for chat in raw_chats:
        if chat["phase"] == "completed":
            continue
        color = calculate_color(chat["phase"], chat["updated_at"], yellow_threshold_minutes)
        processed.append({
            "phone_number": chat["phone_number"],
            "phase": chat["phase"],
            "color": color,
            "elapsed_minutes": calculate_elapsed_minutes(chat["updated_at"]),
            "collected": chat.get("collected", {}),
        })
    processed.sort(key=lambda c: _COLOR_ORDER[c["color"]])
    return {"chats": processed, "kpis": _build_kpis(processed)}


def _build_kpis(chats: list) -> dict:
    return {
        "total": len(chats),
        "in_progress": sum(1 for c in chats if c["color"] == "green"),
        "attention": sum(1 for c in chats if c["color"] == "yellow"),
        "action_required": sum(1 for c in chats if c["color"] == "red"),
    }
```

- [ ] **Step 4: Rodar testes — confirmar que passam**

```bash
docker compose exec odoo odoo -i chat_observer -d odoo --test-enable --stop-after-init 2>&1 | grep -E "OK|ERROR|FAIL|Ran"
```

Expected: `Ran 11 tests` e `OK` (sem FAIL ou ERROR).

- [ ] **Step 5: Commit**

```bash
git add addons/chat_observer/utils/chat_phases.py addons/chat_observer/tests/
git commit -m "feat: add chat_phases utility with unit tests"
```

---

## Task 3: Parâmetros de sistema e XML de action/menu

**Files:**
- Create: `addons/chat_observer/data/chat_observer_data.xml`
- Create: `addons/chat_observer/views/chat_observer_action.xml`

- [ ] **Step 1: Criar `data/chat_observer_data.xml`**

`noupdate="1"` garante que os valores configurados pelo operador não sejam sobrescritos em atualizações do módulo.

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo noupdate="1">
    <record id="param_api_base_url" model="ir.config_parameter">
        <field name="key">chat_observer.api_base_url</field>
        <field name="value"></field>
    </record>
    <record id="param_api_chats_path" model="ir.config_parameter">
        <field name="key">chat_observer.api_chats_path</field>
        <field name="value">/chats/phases</field>
    </record>
    <record id="param_api_history_path" model="ir.config_parameter">
        <field name="key">chat_observer.api_history_path</field>
        <field name="value">/chats/{phone}/history</field>
    </record>
    <record id="param_api_send_path" model="ir.config_parameter">
        <field name="key">chat_observer.api_send_path</field>
        <field name="value">/chats/{phone}/message</field>
    </record>
    <record id="param_refresh_interval" model="ir.config_parameter">
        <field name="key">chat_observer.refresh_interval</field>
        <field name="value">30</field>
    </record>
    <record id="param_yellow_threshold" model="ir.config_parameter">
        <field name="key">chat_observer.yellow_threshold</field>
        <field name="value">5</field>
    </record>
</odoo>
```

- [ ] **Step 2: Criar `views/chat_observer_action.xml`**

A tag do client action (`chat_observer.dashboard`) deve bater exatamente com o nome registrado no `registry` do JS em Task 6.

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="action_chat_observer_dashboard" model="ir.actions.client">
        <field name="name">Chat Observer</field>
        <field name="tag">chat_observer.dashboard</field>
    </record>

    <menuitem
        id="menu_chat_observer_root"
        name="Chat Observer"
        action="action_chat_observer_dashboard"
        sequence="100"
    />
</odoo>
```

- [ ] **Step 3: Commit**

```bash
git add addons/chat_observer/data/ addons/chat_observer/views/
git commit -m "feat: add system parameters and client action menu"
```

---

## Task 4: Controller Python (proxy)

**Files:**
- Create: `addons/chat_observer/controllers/chat_observer.py`

- [ ] **Step 1: Implementar o controller**

```python
import json
import requests

from odoo import http
from odoo.http import request

from odoo.addons.chat_observer.utils.chat_phases import process_chats


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
        api_base_url = _get_param("chat_observer.api_base_url")
        if not api_base_url:
            return _json_response({"error": "api_not_configured"})

        api_chats_path = _get_param("chat_observer.api_chats_path", "/chats/phases")
        yellow_threshold = int(_get_param("chat_observer.yellow_threshold", "5"))

        try:
            resp = requests.get(f"{api_base_url}{api_chats_path}", timeout=10)
            resp.raise_for_status()
            raw_chats = resp.json()
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            return _json_response({"error": "api_unavailable"})
        except requests.exceptions.HTTPError:
            return _json_response({"error": "api_error", "status": resp.status_code})

        return _json_response(process_chats(raw_chats, yellow_threshold))

    @http.route("/chat_observer/history/<phone>", type="http", auth="user", methods=["GET"], csrf=False)
    def get_history(self, phone):
        if not phone.isdigit():
            return _json_response({"error": "invalid_phone"}, status=400)

        api_base_url = _get_param("chat_observer.api_base_url")
        if not api_base_url:
            return _json_response({"error": "api_not_configured"})

        path = _get_param("chat_observer.api_history_path", "/chats/{phone}/history").replace("{phone}", phone)

        try:
            resp = requests.get(f"{api_base_url}{path}", timeout=10)
            if resp.status_code == 404:
                return _json_response({"error": "not_found"}, status=404)
            resp.raise_for_status()
            return request.make_response(resp.text, headers=[("Content-Type", "application/json")])
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            return _json_response({"error": "api_unavailable"})
        except requests.exceptions.HTTPError:
            return _json_response({"error": "api_error", "status": resp.status_code})

    @http.route("/chat_observer/send", type="http", auth="user", methods=["POST"], csrf=False)
    def send_message(self):
        try:
            body = json.loads(request.httprequest.data)
        except (ValueError, KeyError):
            return _json_response({"error": "invalid_payload"}, status=400)

        phone_number = body.get("phone_number", "")
        message = body.get("message", "").strip()

        if not phone_number.isdigit():
            return _json_response({"error": "invalid_phone"}, status=400)
        if not message:
            return _json_response({"error": "empty_message"}, status=400)

        api_base_url = _get_param("chat_observer.api_base_url")
        if not api_base_url:
            return _json_response({"error": "api_not_configured"})

        path = _get_param("chat_observer.api_send_path", "/chats/{phone}/message").replace("{phone}", phone_number)

        try:
            resp = requests.post(f"{api_base_url}{path}", json={"message": message}, timeout=10)
            resp.raise_for_status()
            return _json_response({"success": True})
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            return _json_response({"error": "api_unavailable"})
        except requests.exceptions.HTTPError:
            return _json_response({"error": "send_failed"})
```

- [ ] **Step 2: Reinstalar módulo para verificar que o controller carrega sem erro**

```bash
docker compose exec odoo odoo -u chat_observer -d odoo --stop-after-init 2>&1 | grep -E "ERROR|WARNING|chat_observer"
```

Expected: nenhum `ERROR` relacionado ao `chat_observer`.

- [ ] **Step 3: Commit**

```bash
git add addons/chat_observer/controllers/chat_observer.py
git commit -m "feat: add HTTP proxy controller"
```

---

## Task 5: Componente OWL — Card

**Files:**
- Create: `addons/chat_observer/static/src/xml/chat_observer_card.xml`
- Create: `addons/chat_observer/static/src/js/chat_observer_card.js`

- [ ] **Step 1: Criar template XML do card**

```xml
<?xml version="1.0" encoding="utf-8"?>
<templates xml:space="preserve">
    <t t-name="chat_observer.Card">
        <div
            class="o_chat_card"
            t-att-class="'o_chat_card--' + props.chat.color"
            t-on-click="() => props.onOpen(props.chat)"
        >
            <div class="o_chat_card__status">
                <span class="o_chat_card__dot">■</span>
                <span t-esc="statusLabel"/>
            </div>
            <div class="o_chat_card__phone" t-esc="props.chat.phone_number"/>
            <div class="o_chat_card__info">
                <span t-esc="props.chat.phase"/>
                <span> · </span>
                <span t-esc="props.chat.elapsed_minutes"/>
                <span>min</span>
            </div>
        </div>
    </t>
</templates>
```

- [ ] **Step 2: Criar componente JS do card**

```js
/** @odoo-module **/
import { Component } from "@odoo/owl";

const STATUS_LABELS = {
    red: "REQUER AÇÃO",
    yellow: "ATENÇÃO",
    green: "NORMAL",
};

export class ChatObserverCard extends Component {
    static template = "chat_observer.Card";
    static props = {
        chat: Object,
        onOpen: Function,
    };

    get statusLabel() {
        return STATUS_LABELS[this.props.chat.color] || this.props.chat.color.toUpperCase();
    }
}
```

- [ ] **Step 3: Commit**

```bash
git add addons/chat_observer/static/src/xml/chat_observer_card.xml \
        addons/chat_observer/static/src/js/chat_observer_card.js
git commit -m "feat: add ChatObserverCard OWL component"
```

---

## Task 6: Componente OWL — Dashboard

**Files:**
- Create: `addons/chat_observer/static/src/xml/chat_observer_dashboard.xml`
- Create: `addons/chat_observer/static/src/js/chat_observer_dashboard.js`

- [ ] **Step 1: Criar template XML do dashboard**

```xml
<?xml version="1.0" encoding="utf-8"?>
<templates xml:space="preserve">
    <t t-name="chat_observer.Dashboard">
        <div class="o_chat_observer">

            <!-- Banner de erro -->
            <t t-if="state.error">
                <div class="o_chat_observer__error">
                    <t t-if="state.error === 'api_not_configured'">
                        API não configurada. Defina
                        <strong>chat_observer.api_base_url</strong>
                        em Configurações → Parâmetros do Sistema.
                    </t>
                    <t t-elif="state.error === 'api_unavailable'">
                        API externa indisponível. Tentando reconectar...
                    </t>
                    <t t-else="">
                        Erro ao carregar chats. Tentando novamente...
                    </t>
                </div>
            </t>

            <!-- KPIs -->
            <div class="o_chat_observer__kpis">
                <div class="o_chat_kpi o_chat_kpi--neutral">
                    <span class="o_chat_kpi__value" t-esc="state.kpis.total"/>
                    <span class="o_chat_kpi__label">TOTAL</span>
                </div>
                <div class="o_chat_kpi o_chat_kpi--green">
                    <span class="o_chat_kpi__value" t-esc="state.kpis.in_progress"/>
                    <span class="o_chat_kpi__label">ANDAMENTO</span>
                </div>
                <div class="o_chat_kpi o_chat_kpi--yellow">
                    <span class="o_chat_kpi__value" t-esc="state.kpis.attention"/>
                    <span class="o_chat_kpi__label">ATENÇÃO</span>
                </div>
                <div class="o_chat_kpi o_chat_kpi--red">
                    <span class="o_chat_kpi__value" t-esc="state.kpis.action_required"/>
                    <span class="o_chat_kpi__label">REQUER AÇÃO</span>
                </div>
            </div>

            <!-- Grid de cards -->
            <div class="o_chat_observer__grid">
                <t t-foreach="state.chats" t-as="chat" t-key="chat.phone_number">
                    <ChatObserverCard chat="chat" onOpen.bind="openChat"/>
                </t>
                <t t-if="!state.error and state.chats.length === 0">
                    <div class="o_chat_observer__empty">Nenhum chat em andamento.</div>
                </t>
            </div>

            <!-- Indicador de atualização -->
            <div class="o_chat_observer__footer">
                <span t-if="state.lastUpdated">
                    ↻ atualizado há <t t-esc="state.secondsSinceUpdate"/>s
                </span>
            </div>

            <!-- Modal de detalhe -->
            <t t-if="state.selectedChat">
                <div class="o_chat_modal_overlay" t-on-click="closeModal">
                    <div class="o_chat_modal" t-on-click.stop="">
                        <div class="o_chat_modal__header">
                            <div>
                                <strong t-esc="state.selectedChat.phone_number"/>
                                <span
                                    class="o_chat_badge"
                                    t-att-class="'o_chat_badge--' + state.selectedChat.color"
                                >
                                    <t t-esc="state.selectedChat.phase"/>
                                    <span> · </span>
                                    <t t-esc="state.selectedChat.elapsed_minutes"/>min
                                </span>
                            </div>
                            <button class="o_chat_modal__close" t-on-click="closeModal">✕</button>
                        </div>

                        <div class="o_chat_modal__history">
                            <t t-if="state.modalLoading">
                                <div class="o_chat_modal__loading">Carregando histórico...</div>
                            </t>
                            <t t-elif="state.modalError">
                                <div class="o_chat_modal__error">
                                    Erro ao carregar histórico.
                                </div>
                            </t>
                            <t t-else="">
                                <t t-foreach="state.modalHistory" t-as="msg" t-key="msg_index">
                                    <div
                                        class="o_chat_msg"
                                        t-att-class="'o_chat_msg--' + (msg.role || 'unknown')"
                                    >
                                        <span class="o_chat_msg__role" t-esc="msg.role"/>
                                        <span class="o_chat_msg__text" t-esc="msg.content"/>
                                    </div>
                                </t>
                                <t t-if="state.modalHistory.length === 0">
                                    <div class="o_chat_modal__empty">Sem histórico disponível.</div>
                                </t>
                            </t>
                        </div>

                        <div class="o_chat_modal__footer">
                            <input
                                class="o_chat_modal__input"
                                type="text"
                                placeholder="Digite uma mensagem..."
                                t-model="state.sendMessage"
                                t-on-keydown="onInputKeydown"
                            />
                            <button
                                class="o_chat_modal__send"
                                t-att-disabled="state.sendLoading or !state.sendMessage.trim()"
                                t-on-click="sendMessage"
                            >
                                <t t-if="state.sendLoading">...</t>
                                <t t-else="">Enviar</t>
                            </button>
                        </div>
                        <t t-if="state.sendError">
                            <div class="o_chat_modal__send_error">
                                Falha ao enviar mensagem. Tente novamente.
                            </div>
                        </t>
                    </div>
                </div>
            </t>

        </div>
    </t>
</templates>
```

- [ ] **Step 2: Criar componente JS do dashboard**

```js
/** @odoo-module **/
import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ChatObserverCard } from "./chat_observer_card";

class ChatObserverDashboard extends Component {
    static template = "chat_observer.Dashboard";
    static components = { ChatObserverCard };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            chats: [],
            kpis: { total: 0, in_progress: 0, attention: 0, action_required: 0 },
            error: null,
            lastUpdated: null,
            secondsSinceUpdate: 0,
            selectedChat: null,
            modalHistory: [],
            modalLoading: false,
            modalError: false,
            sendLoading: false,
            sendMessage: "",
            sendError: false,
        });
        this._pollInterval = null;
        this._clockInterval = null;

        onMounted(async () => {
            const interval = await this._getRefreshInterval();
            await this._fetchChats();
            this._pollInterval = setInterval(() => this._fetchChats(), interval * 1000);
            this._clockInterval = setInterval(() => this._tickClock(), 1000);
        });

        onWillUnmount(() => {
            clearInterval(this._pollInterval);
            clearInterval(this._clockInterval);
        });
    }

    async _getRefreshInterval() {
        const val = await this.orm.call(
            "ir.config_parameter",
            "get_param",
            ["chat_observer.refresh_interval", "30"]
        );
        return parseInt(val) || 30;
    }

    async _fetchChats() {
        try {
            const resp = await fetch("/chat_observer/chats");
            const data = await resp.json();
            if (data.error) {
                this.state.error = data.error;
            } else {
                this.state.error = null;
                this.state.chats = data.chats;
                this.state.kpis = data.kpis;
                this.state.lastUpdated = Date.now();
                this.state.secondsSinceUpdate = 0;
            }
        } catch {
            this.state.error = "api_unavailable";
        }
    }

    _tickClock() {
        if (this.state.lastUpdated) {
            this.state.secondsSinceUpdate = Math.floor((Date.now() - this.state.lastUpdated) / 1000);
        }
    }

    async openChat(chat) {
        this.state.selectedChat = chat;
        this.state.modalHistory = [];
        this.state.modalLoading = true;
        this.state.modalError = false;
        this.state.sendMessage = "";
        this.state.sendError = false;
        try {
            const resp = await fetch(`/chat_observer/history/${chat.phone_number}`);
            const data = await resp.json();
            if (data.error) {
                this.state.modalError = true;
            } else {
                this.state.modalHistory = data.history || [];
            }
        } catch {
            this.state.modalError = true;
        } finally {
            this.state.modalLoading = false;
        }
    }

    closeModal() {
        this.state.selectedChat = null;
        this.state.modalHistory = [];
        this.state.sendMessage = "";
        this.state.sendError = false;
    }

    onInputKeydown(ev) {
        if (ev.key === "Enter" && !this.state.sendLoading) {
            this.sendMessage();
        }
    }

    async sendMessage() {
        const msg = this.state.sendMessage.trim();
        if (!msg || this.state.sendLoading) return;
        this.state.sendLoading = true;
        this.state.sendError = false;
        try {
            const resp = await fetch("/chat_observer/send", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    phone_number: this.state.selectedChat.phone_number,
                    message: msg,
                }),
            });
            const data = await resp.json();
            if (data.error) {
                this.state.sendError = true;
            } else {
                this.state.sendMessage = "";
            }
        } catch {
            this.state.sendError = true;
        } finally {
            this.state.sendLoading = false;
        }
    }
}

registry.category("actions").add("chat_observer.dashboard", ChatObserverDashboard);
```

- [ ] **Step 3: Commit**

```bash
git add addons/chat_observer/static/src/xml/chat_observer_dashboard.xml \
        addons/chat_observer/static/src/js/chat_observer_dashboard.js
git commit -m "feat: add ChatObserverDashboard OWL component"
```

---

## Task 7: Estilos SCSS

**Files:**
- Create: `addons/chat_observer/static/src/scss/chat_observer.scss`

- [ ] **Step 1: Criar `chat_observer.scss`**

```scss
.o_chat_observer {
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 24px;
    min-height: 100%;
}

// ── KPIs ──────────────────────────────────────────────────────────────────────

.o_chat_observer__kpis {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
}

.o_chat_kpi {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 16px 24px;
    border-radius: 8px;
    min-width: 100px;
    border: 1px solid transparent;

    &__value {
        font-size: 2rem;
        font-weight: 700;
        line-height: 1.1;
    }

    &__label {
        font-size: 0.65rem;
        letter-spacing: 0.08em;
        margin-top: 4px;
        font-weight: 600;
    }

    &--neutral {
        background: #f8f9fa;
        border-color: #dee2e6;
        .o_chat_kpi__value, .o_chat_kpi__label { color: #495057; }
    }

    &--green {
        background: #d4edda;
        border-color: #c3e6cb;
        .o_chat_kpi__value, .o_chat_kpi__label { color: #155724; }
    }

    &--yellow {
        background: #fff3cd;
        border-color: #ffeeba;
        .o_chat_kpi__value, .o_chat_kpi__label { color: #856404; }
    }

    &--red {
        background: #f8d7da;
        border-color: #f5c6cb;
        .o_chat_kpi__value, .o_chat_kpi__label { color: #721c24; }
    }
}

// ── Cards grid ────────────────────────────────────────────────────────────────

.o_chat_observer__grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 12px;
}

.o_chat_card {
    padding: 12px 14px;
    border-radius: 6px;
    border-left: 4px solid transparent;
    cursor: pointer;
    background: #fff;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
    transition: box-shadow 0.15s;

    &:hover {
        box-shadow: 0 3px 8px rgba(0, 0, 0, 0.15);
    }

    &__status {
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        margin-bottom: 6px;
    }

    &__phone {
        font-size: 0.95rem;
        font-weight: 600;
        color: #212529;
    }

    &__info {
        font-size: 0.78rem;
        color: #6c757d;
        margin-top: 4px;
    }

    &--red {
        border-color: #dc3545;
        background: #fff5f5;
        .o_chat_card__status { color: #dc3545; }
    }

    &--yellow {
        border-color: #ffc107;
        background: #fffdf0;
        .o_chat_card__status { color: #856404; }
    }

    &--green {
        border-color: #28a745;
        background: #f6fff8;
        .o_chat_card__status { color: #155724; }
    }
}

// ── Mensagens de estado ───────────────────────────────────────────────────────

.o_chat_observer__error {
    padding: 12px 16px;
    border-radius: 6px;
    background: #fff3cd;
    border: 1px solid #ffeeba;
    color: #856404;
    font-size: 0.875rem;
}

.o_chat_observer__empty {
    color: #6c757d;
    font-size: 0.875rem;
    padding: 24px 0;
}

.o_chat_observer__footer {
    font-size: 0.75rem;
    color: #adb5bd;
    text-align: right;
}

// ── Modal ─────────────────────────────────────────────────────────────────────

.o_chat_modal_overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1050;
}

.o_chat_modal {
    background: #fff;
    border-radius: 8px;
    width: 480px;
    max-width: 95vw;
    max-height: 80vh;
    display: flex;
    flex-direction: column;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);

    &__header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        padding: 16px 20px;
        border-bottom: 1px solid #dee2e6;
        font-size: 1rem;
    }

    &__close {
        background: none;
        border: none;
        font-size: 1.1rem;
        color: #6c757d;
        cursor: pointer;
        padding: 0 4px;
        line-height: 1;

        &:hover { color: #343a40; }
    }

    &__history {
        flex: 1;
        overflow-y: auto;
        padding: 16px 20px;
        display: flex;
        flex-direction: column;
        gap: 8px;
        background: #f8f9fa;
    }

    &__loading,
    &__error,
    &__empty {
        text-align: center;
        color: #6c757d;
        font-size: 0.875rem;
        padding: 24px 0;
    }

    &__footer {
        display: flex;
        gap: 8px;
        padding: 12px 20px;
        border-top: 1px solid #dee2e6;
    }

    &__input {
        flex: 1;
        border: 1px solid #ced4da;
        border-radius: 4px;
        padding: 8px 12px;
        font-size: 0.875rem;
        outline: none;

        &:focus { border-color: #80bdff; box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25); }
    }

    &__send {
        background: #007bff;
        color: #fff;
        border: none;
        border-radius: 4px;
        padding: 8px 16px;
        font-size: 0.875rem;
        cursor: pointer;

        &:disabled { background: #b3d7ff; cursor: not-allowed; }
        &:hover:not(:disabled) { background: #0069d9; }
    }

    &__send_error {
        padding: 4px 20px 8px;
        font-size: 0.78rem;
        color: #dc3545;
    }
}

// ── Mensagens do chat ─────────────────────────────────────────────────────────

.o_chat_msg {
    display: flex;
    flex-direction: column;
    gap: 2px;

    &__role {
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: #6c757d;
    }

    &__text {
        font-size: 0.875rem;
        color: #212529;
        background: #fff;
        padding: 6px 10px;
        border-radius: 4px;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
    }

    &--user .o_chat_msg__text { background: #e8f4fd; }
    &--assistant .o_chat_msg__text { background: #fff; }
}

// ── Badge de fase ─────────────────────────────────────────────────────────────

.o_chat_badge {
    display: inline-block;
    margin-left: 8px;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;

    &--red    { background: #f8d7da; color: #721c24; }
    &--yellow { background: #fff3cd; color: #856404; }
    &--green  { background: #d4edda; color: #155724; }
}
```

- [ ] **Step 2: Commit**

```bash
git add addons/chat_observer/static/src/scss/chat_observer.scss
git commit -m "feat: add dashboard SCSS styles"
```

---

## Task 8: Atualizar módulo e verificar no browser

**Files:**
- (sem novos arquivos — verificação manual)

- [ ] **Step 1: Subir ambiente de desenvolvimento**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

- [ ] **Step 2: Instalar/atualizar o módulo**

Se é a primeira instalação:
```bash
docker compose exec odoo odoo -i chat_observer -d odoo --stop-after-init
```

Se o módulo já estava instalado de passos anteriores:
```bash
docker compose exec odoo odoo -u chat_observer -d odoo --stop-after-init
```

Expected: sem linhas `ERROR` relacionadas ao `chat_observer`.

- [ ] **Step 3: Verificar banner de API não configurada**

1. Abra o Odoo no browser em `http://localhost:8069`
2. Clique em **Chat Observer** no menu principal
3. Expected: banner amarelo com o texto "API não configurada. Defina `chat_observer.api_base_url` nos Parâmetros do Sistema."
4. Os KPIs devem mostrar `0` e o grid deve estar vazio

- [ ] **Step 4: Rodar testes unitários**

```bash
docker compose exec odoo odoo -u chat_observer -d odoo --test-enable --stop-after-init 2>&1 | grep -E "Ran|OK|ERROR|FAIL"
```

Expected: `Ran 11 tests` / `OK`

- [ ] **Step 5: Commit final de verificação**

```bash
git add -A
git commit -m "feat: chat_observer complete — dashboard with polling, KPIs, colored cards and chat modal"
```

---

## Task 9: Criar Pull Request

**Files:**
- (sem arquivos — apenas git/GitHub)

- [ ] **Step 1: Push da branch**

```bash
git push -u origin feat/chat-observer
```

- [ ] **Step 2: Criar PR via `gh`**

```bash
gh pr create \
  --base develop \
  --title "feat: add chat_observer addon" \
  --body "$(cat <<'EOF'
## Summary

- Novo addon `chat_observer` que monitora fases de chats em andamento via API externa
- Dashboard OWL com KPIs (total, andamento, atenção, requer ação) e cards coloridos por urgência
- Proxy Python com lógica de cor (vermelho=operator/error, amarelo=≥5min, verde=normal) e KPIs calculados localmente
- Modal de detalhe com histórico do chat e envio de mensagem livre
- Polling automático com intervalo configurável; todos os endpoints da API configuráveis via Parâmetros do Sistema
- 11 testes unitários cobrindo lógica de cor, KPIs, ordenação e exclusão de chats concluídos

## Spec

`docs/superpowers/specs/2026-06-01-chat-observer-design.md`

## Test plan

- [ ] `docker compose exec odoo odoo -u chat_observer -d odoo --test-enable --stop-after-init` passa sem FAIL
- [ ] Menu "Chat Observer" aparece no Odoo
- [ ] Banner de aviso exibido quando `api_base_url` não configurado
- [ ] Cards ordenados vermelho → amarelo → verde após configurar API
- [ ] Clicar num card abre modal com histórico
- [ ] Enviar mensagem no modal chama `/chat_observer/send`
- [ ] Dashboard atualiza automaticamente a cada N segundos
EOF
)"
```

---

## Self-Review

### Spec coverage

| Requisito | Tarefa |
|---|---|
| Addon herda `uduu_base` | Task 1 (`__manifest__.py`) |
| Dashboard com KPIs | Task 6 (template) + Task 7 (SCSS) |
| Blocos coloridos (verde/amarelo/vermelho) | Task 2 (lógica) + Task 5 (card) + Task 7 (SCSS) |
| Vermelho = operator/error | Task 2 (`_RED_PHASES`) |
| Amarelo = ≥5min, configurável | Task 2 (`yellow_threshold`) + Task 3 (parâmetro) |
| Completados não exibidos | Task 2 (`phase == "completed"` excluído) |
| Ordenação vermelho→amarelo→verde | Task 2 (`_COLOR_ORDER`) |
| Polling configurável em segundos | Task 3 (`refresh_interval`) + Task 6 (JS `_getRefreshInterval`) |
| Clicar abre modal com detalhe | Task 6 (`openChat`, template modal) |
| Envio de mensagem livre | Task 6 (`sendMessage`) + Task 4 (`/send`) |
| Endpoints configuráveis | Task 3 (todos os paths como parâmetros) |
| API não configurada = banner amigável | Task 4 (controller) + Task 6 (template) |
| Branch antes de desenvolver | Task 0 |
| PR ao final | Task 9 |
