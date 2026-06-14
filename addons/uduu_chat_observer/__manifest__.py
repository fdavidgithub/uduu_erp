{
    "name": "Uduu Chat Observer",
    "version": "19.0.1.1.0",
    "summary": "Monitoramento em tempo real de chats em andamento",
    "author": "Uduu",
    "website": "",
    "category": "Customizations",
    "license": "LGPL-3",
    "depends": ["uduu_base", "web"],
    "demo": [],
    "data": [
        "security/ir.model.access.csv",
        "data/chat_observer_data.xml",
        "views/chat_observer_action.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "uduu_chat_observer/static/src/scss/chat_observer.scss",
            "uduu_chat_observer/static/src/xml/chat_observer_card.xml",
            "uduu_chat_observer/static/src/xml/chat_observer_dashboard.xml",
            "uduu_chat_observer/static/src/js/chat_observer_card.js",
            "uduu_chat_observer/static/src/js/chat_observer_dashboard.js",
        ],
    },
    "installable": True,
    "auto_install": False,
    "application": False,
}
