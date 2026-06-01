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
