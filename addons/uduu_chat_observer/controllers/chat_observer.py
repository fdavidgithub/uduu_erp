import json
import logging
import time

import requests

from odoo import http
from odoo.http import request

from odoo.addons.uduu_chat_observer.utils.chat_phases import process_chats

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
        api_base_url = _get_param("uduu_base.api_base_url")
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

        api_base_url = _get_param("uduu_base.api_base_url")
        if not api_base_url:
            return _json_response({"error": "api_not_configured"}, status=503)

        path = _get_param("uduu_chat_observer.api_history_path", "/chats/{phone}/history")

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

        api_base_url = _get_param("uduu_base.api_base_url")
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
