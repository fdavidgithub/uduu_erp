/** @odoo-module **/
import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ChatObserverCard } from "./chat_observer_card";

class ChatObserverDashboard extends Component {
    static template = "chat_observer.Dashboard";
    static components = { ChatObserverCard };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            chats: [],
            kpis: { total: 0, in_progress: 0, attention: 0, action_required: 0 },
            error: null,
            lastUpdated: null,
            secondsSinceUpdate: 0,
            selectedChat: null,
            modalHistory: [],
            modalLoading: false,
            modalError: false,
            sendLoading: false,
            sendMessage: "",
            sendError: false,
        });
        this._pollInterval = null;
        this._clockInterval = null;

        onMounted(async () => {
            const interval = await this._getRefreshInterval();
            await this._fetchChats();
            this._pollInterval = setInterval(() => this._fetchChats(), interval * 1000);
            this._clockInterval = setInterval(() => this._tickClock(), 1000);
        });

        onWillUnmount(() => {
            clearInterval(this._pollInterval);
            clearInterval(this._clockInterval);
        });
    }

    async _getRefreshInterval() {
        const val = await this.orm.call(
            "ir.config_parameter",
            "get_param",
            ["chat_observer.refresh_interval", "30"]
        );
        return parseInt(val) || 30;
    }

    async _fetchChats() {
        try {
            const resp = await fetch("/chat_observer/chats");
            const data = await resp.json();
            if (data.error) {
                this.state.error = data.error;
            } else {
                this.state.error = null;
                this.state.chats = data.chats;
                this.state.kpis = data.kpis;
                this.state.lastUpdated = Date.now();
                this.state.secondsSinceUpdate = 0;
            }
        } catch {
            this.state.error = "api_unavailable";
        }
    }

    _tickClock() {
        if (this.state.lastUpdated) {
            this.state.secondsSinceUpdate = Math.floor((Date.now() - this.state.lastUpdated) / 1000);
        }
    }

    async openChat(chat) {
        this.state.selectedChat = chat;
        this.state.modalHistory = [];
        this.state.modalLoading = true;
        this.state.modalError = false;
        this.state.sendMessage = "";
        this.state.sendError = false;
        try {
            const resp = await fetch(`/chat_observer/history/${chat.phone_number}`);
            const data = await resp.json();
            if (data.error) {
                this.state.modalError = true;
            } else {
                this.state.modalHistory = data.history || [];
            }
        } catch {
            this.state.modalError = true;
        } finally {
            this.state.modalLoading = false;
        }
    }

    closeModal() {
        this.state.selectedChat = null;
        this.state.modalHistory = [];
        this.state.sendMessage = "";
        this.state.sendError = false;
    }

    onInputKeydown(ev) {
        if (ev.key === "Enter" && !this.state.sendLoading) {
            this.sendMessage();
        }
    }

    async sendMessage() {
        const msg = this.state.sendMessage.trim();
        if (!msg || this.state.sendLoading) return;
        this.state.sendLoading = true;
        this.state.sendError = false;
        try {
            const resp = await fetch("/chat_observer/send", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    phone_number: this.state.selectedChat.phone_number,
                    message: msg,
                }),
            });
            const data = await resp.json();
            if (data.error) {
                this.state.sendError = true;
            } else {
                this.state.sendMessage = "";
            }
        } catch {
            this.state.sendError = true;
        } finally {
            this.state.sendLoading = false;
        }
    }
}

registry.category("actions").add("chat_observer.dashboard", ChatObserverDashboard);
