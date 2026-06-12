import logging
import re
import requests

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    comment = fields.Html(related="partner_id.comment", readonly=False, string="Notas")

    def _get_param(self, key, default=""):
        return self.env["ir.config_parameter"].sudo().get_param(key, default)

    def _build_sync_payload(self):
        self.ensure_one()
        street_parts = (self.street or "").split(",", 1)
        street_name = street_parts[0].strip()
        street_number = street_parts[1].strip() if len(street_parts) > 1 else ""
        description = re.sub(r"<[^>]+>", "", self.partner_id.comment or "").strip()
        return {
            "odoo_company_id": self.id,
            "name": self.name,
            "phone": self.phone or "",
            "email": self.email or "",
            "website": self.website or "",
            "description": description,
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
        base_url = self._get_param("uduu_base.api_base_url")
        if not base_url:
            raise UserError(
                "Integração com API não configurada. "
                "Defina 'uduu_base.api_base_url' em Técnico → Parâmetros do Sistema."
            )
        post_path = self._get_param("uduu_base.api_post_path", "/odoo/company")
        url = f"{base_url}{post_path}"
        payload = self._build_sync_payload()
        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
        except requests.exceptions.ConnectionError as e:
            _logger.error("uduu_base: API indisponível: %s", e)
            raise UserError(
                f"Não foi possível conectar à API ({base_url}). Verifique a conexão."
            ) from e
        except requests.exceptions.Timeout as e:
            _logger.error("uduu_base: Timeout: %s", e)
            raise UserError(
                f"Timeout ao chamar a API ({base_url}). Tente novamente."
            ) from e
        except requests.exceptions.HTTPError as e:
            _logger.error("uduu_base: HTTP %s: %s", resp.status_code, e)
            raise UserError(
                f"Erro na API ao sincronizar empresa: HTTP {resp.status_code}."
            ) from e
        except requests.exceptions.RequestException as e:
            _logger.error("uduu_base: unexpected request error: %s", e)
            raise UserError(
                f"Erro inesperado ao sincronizar com a API ({base_url})."
            ) from e

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record._sync_to_api()
        return records
