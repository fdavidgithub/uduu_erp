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
            """
            UPDATE ir_config_parameter SET key = %s
            WHERE key = %s
              AND NOT EXISTS (
                  SELECT 1 FROM ir_config_parameter WHERE key = %s
              )
            """,
            (new_key, old_key, new_key),
        )
        if cr.rowcount:
            _logger.info("uduu: renamed ir.config_parameter %s → %s", old_key, new_key)
