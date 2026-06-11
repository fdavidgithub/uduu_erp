import logging

from odoo import models

_logger = logging.getLogger(__name__)

PARTNER_SYNC_FIELDS = {
    "name", "phone", "email", "website",
    "street", "street2", "city", "state_id", "zip", "country_id",
    "comment",
}


class ResPartner(models.Model):
    _inherit = "res.partner"

    def write(self, vals):
        result = super().write(vals)
        if PARTNER_SYNC_FIELDS & vals.keys():
            companies = self.env["res.company"].search([("partner_id", "in", self.ids)])
            for company in companies:
                company._sync_to_api()
        return result
