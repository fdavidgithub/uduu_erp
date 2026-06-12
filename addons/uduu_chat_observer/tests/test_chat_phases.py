import unittest
from datetime import datetime, timezone, timedelta

try:
    from odoo.tests.common import BaseCase as _TestCase
except ImportError:
    _TestCase = unittest.TestCase


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


class TestCalculateColor(_TestCase):

    def test_operator_is_red(self):
        from odoo.addons.uduu_chat_observer.utils.chat_phases import calculate_color
        self.assertEqual(calculate_color("operator", _ts(1), 5), "red")

    def test_error_is_red(self):
        from odoo.addons.uduu_chat_observer.utils.chat_phases import calculate_color
        self.assertEqual(calculate_color("error", _ts(1), 5), "red")

    def test_recent_chat_is_green(self):
        from odoo.addons.uduu_chat_observer.utils.chat_phases import calculate_color
        self.assertEqual(calculate_color("collecting_product", _ts(2), 5), "green")

    def test_old_chat_is_yellow(self):
        from odoo.addons.uduu_chat_observer.utils.chat_phases import calculate_color
        self.assertEqual(calculate_color("collecting_product", _ts(10), 5), "yellow")

    def test_exactly_at_threshold_is_yellow(self):
        from odoo.addons.uduu_chat_observer.utils.chat_phases import calculate_color
        self.assertEqual(calculate_color("collecting_product", _ts(5), 5), "yellow")

    def test_custom_threshold(self):
        from odoo.addons.uduu_chat_observer.utils.chat_phases import calculate_color
        self.assertEqual(calculate_color("collecting_customer", _ts(3), 2), "yellow")


class TestProcessChats(_TestCase):

    def test_completed_chats_excluded(self):
        from odoo.addons.uduu_chat_observer.utils.chat_phases import process_chats
        result = process_chats([_chat("111", "completed")], 5)
        self.assertEqual(result["chats"], [])

    def test_ordering_red_yellow_green(self):
        from odoo.addons.uduu_chat_observer.utils.chat_phases import process_chats
        chats = [
            _chat("green", "collecting_product", minutes_ago=1),
            _chat("yellow", "collecting_product", minutes_ago=10),
            _chat("red", "operator", minutes_ago=1),
        ]
        result = process_chats(chats, 5)
        colors = [c["color"] for c in result["chats"]]
        self.assertEqual(colors, ["red", "yellow", "green"])

    def test_kpis_correct(self):
        from odoo.addons.uduu_chat_observer.utils.chat_phases import process_chats
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
        from odoo.addons.uduu_chat_observer.utils.chat_phases import process_chats
        result = process_chats([_chat("111", "collecting_product", minutes_ago=7)], 5)
        self.assertGreaterEqual(result["chats"][0]["elapsed_minutes"], 7)

    def test_empty_list(self):
        from odoo.addons.uduu_chat_observer.utils.chat_phases import process_chats
        result = process_chats([], 5)
        self.assertEqual(result["chats"], [])
        self.assertEqual(result["kpis"]["total"], 0)
