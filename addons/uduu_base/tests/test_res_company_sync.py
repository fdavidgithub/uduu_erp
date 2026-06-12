from unittest.mock import MagicMock, patch

import requests

from odoo.exceptions import UserError
from odoo.tests import TransactionCase


class TestResCompanySync(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env.ref("base.main_company")
        self.env["ir.config_parameter"].sudo().set_param(
            "uduu_base.api_base_url", "http://test.example.com"
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "uduu_base.api_post_path", "/odoo/company"
        )

    def _ok_mock(self):
        mock = MagicMock()
        mock.status_code = 200
        mock.raise_for_status = MagicMock()
        return mock

    @patch("odoo.addons.uduu_base.models.res_company.requests.post")
    def test_write_calls_post_with_correct_url(self, mock_post):
        mock_post.return_value = self._ok_mock()
        self.company.write({"name": self.company.name})
        mock_post.assert_called_once()
        url = mock_post.call_args[0][0]
        self.assertEqual(url, "http://test.example.com/odoo/company")

    @patch("odoo.addons.uduu_base.models.res_company.requests.post")
    def test_create_calls_post_endpoint(self, mock_post):
        mock_post.return_value = self._ok_mock()
        new_company = self.env["res.company"].create({"name": "Empresa Teste"})
        mock_post.assert_called_once()
        payload = mock_post.call_args[1]["json"]
        self.assertEqual(payload["odoo_company_id"], new_company.id)
        self.assertEqual(payload["name"], "Empresa Teste")

    def test_write_blocks_when_base_url_empty(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "uduu_base.api_base_url", ""
        )
        with self.assertRaises(UserError):
            self.company.write({"name": self.company.name})

    @patch("odoo.addons.uduu_base.models.res_company.requests.post")
    def test_write_blocks_on_connection_error(self, mock_post):
        mock_post.side_effect = requests.exceptions.ConnectionError("refused")
        with self.assertRaises(UserError):
            self.company.write({"name": self.company.name})

    @patch("odoo.addons.uduu_base.models.res_company.requests.post")
    def test_write_blocks_on_timeout(self, mock_post):
        mock_post.side_effect = requests.exceptions.Timeout("timeout")
        with self.assertRaises(UserError):
            self.company.write({"name": self.company.name})

    @patch("odoo.addons.uduu_base.models.res_company.requests.post")
    def test_write_blocks_on_http_error(self, mock_post):
        mock = MagicMock()
        mock.status_code = 500
        mock.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
        mock_post.return_value = mock
        with self.assertRaises(UserError):
            self.company.write({"name": self.company.name})

    @patch("odoo.addons.uduu_base.models.res_company.requests.post")
    def test_street_split_before_comma(self, mock_post):
        mock_post.return_value = self._ok_mock()
        self.company.write({"street": "Rua das Flores, 123"})
        payload = mock_post.call_args[1]["json"]
        self.assertEqual(payload["address"]["street"], "Rua das Flores")
        self.assertEqual(payload["address"]["number"], "123")

    @patch("odoo.addons.uduu_base.models.res_company.requests.post")
    def test_street_without_comma_has_empty_number(self, mock_post):
        mock_post.return_value = self._ok_mock()
        self.company.write({"street": "Rua das Flores"})
        payload = mock_post.call_args[1]["json"]
        self.assertEqual(payload["address"]["street"], "Rua das Flores")
        self.assertEqual(payload["address"]["number"], "")

    @patch("odoo.addons.uduu_base.models.res_company.requests.post")
    def test_street2_maps_to_neighborhood(self, mock_post):
        mock_post.return_value = self._ok_mock()
        self.company.write({"street2": "Centro"})
        payload = mock_post.call_args[1]["json"]
        self.assertEqual(payload["address"]["neighborhood"], "Centro")

    @patch("odoo.addons.uduu_base.models.res_company.requests.post")
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

    @patch("odoo.addons.uduu_base.models.res_company.requests.post")
    def test_country_name_sent_not_code(self, mock_post):
        mock_post.return_value = self._ok_mock()
        country = self.env["res.country"].search([("code", "=", "BR")], limit=1)
        if not country:
            self.skipTest("País BR não encontrado no banco de teste")
        self.company.write({"country_id": country.id})
        payload = mock_post.call_args[1]["json"]
        self.assertEqual(payload["address"]["country"], country.name)
        self.assertNotEqual(payload["address"]["country"], "BR")

    @patch("odoo.addons.uduu_base.models.res_company.requests.post")
    def test_description_field_in_payload(self, mock_post):
        mock_post.return_value = self._ok_mock()
        self.company.write({"description": "Tecnologia para vendas conversacionais"})
        payload = mock_post.call_args[1]["json"]
        self.assertEqual(payload["description"], "Tecnologia para vendas conversacionais")

    @patch("odoo.addons.uduu_base.models.res_company.requests.post")
    def test_payload_has_all_required_fields(self, mock_post):
        mock_post.return_value = self._ok_mock()
        self.company.write({"name": self.company.name})
        payload = mock_post.call_args[1]["json"]
        for field in ("odoo_company_id", "name", "phone", "email", "website", "description", "address"):
            self.assertIn(field, payload)
        for addr_field in ("street", "number", "complement", "neighborhood", "city", "state", "zip_code", "country"):
            self.assertIn(addr_field, payload["address"])
