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
