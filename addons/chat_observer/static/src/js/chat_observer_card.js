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
