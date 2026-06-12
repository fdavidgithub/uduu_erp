/** @odoo-module **/
import { Component, useState, onMounted, onWillUnmount, useRef } from "@odoo/owl";
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
        this.historyRef = useRef("historyContainer");
        this._pollInterval = null;
        this._clockInterval = null;
        this._historyInterval = null;

        onMounted(async () => {
            const interval = await this._getRefreshInterval();
            await this._fetchChats();
            this._pollInterval = setInterval(() => this._fetchChats(), interval * 1000);
            this._clockInterval = setInterval(() => this._tickClock(), 1000);
        });

        onWillUnmount(() => {
            clearInterval(this._pollInterval);
            clearInterval(this._clockInterval);
            clearInterval(this._historyInterval);
        });
    }

    async _getRefreshInterval() {
        const val = await this.orm.call(
            "ir.config_parameter",
            "get_param",
            ["uduu_chat_observer.refresh_interval", "30"]
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

    _scrollHistoryToBottom() {
        setTimeout(() => {
            const el = this.historyRef.el;
            if (el) el.scrollTop = el.scrollHeight;
        }, 0);
    }

    async _fetchHistory(phone) {
        try {
            const resp = await fetch(`/chat_observer/history/${phone}`);
            const data = await resp.json();
            if (!Array.isArray(data) && data.error) {
                this.state.modalError = true;
            } else {
                this.state.modalError = false;
                this.state.modalHistory = Array.isArray(data) ? data : (data.history || []);
                this._scrollHistoryToBottom();
            }
        } catch {
            this.state.modalError = true;
        }
    }

    async openChat(chat) {
        if (!chat.phone_number) return;
        clearInterval(this._historyInterval);
        this.state.selectedChat = chat;
        this.state.modalHistory = [];
        this.state.modalLoading = true;
        this.state.modalError = false;
        this.state.sendMessage = "";
        this.state.sendError = false;

        await this._fetchHistory(chat.phone_number);
        this.state.modalLoading = false;

        const intervalSec = await this.orm.call(
            "ir.config_parameter",
            "get_param",
            ["uduu_chat_observer.history_refresh_interval", "5"]
        );
        const ms = (parseInt(intervalSec) || 5) * 1000;
        this._historyInterval = setInterval(() => {
            if (this.state.selectedChat) {
                this._fetchHistory(this.state.selectedChat.phone_number);
            }
        }, ms);
    }

    formatMsgDate(isoString) {
        if (!isoString) return "";
        const d = new Date(isoString);
        const pad = (n) => String(n).padStart(2, "0");
        return `${pad(d.getDate())}/${pad(d.getMonth() + 1)} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
    }

    closeModal() {
        clearInterval(this._historyInterval);
        this._historyInterval = null;
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
                await this._fetchHistory(this.state.selectedChat.phone_number);
            }
        } catch {
            this.state.sendError = true;
        } finally {
            this.state.sendLoading = false;
        }
    }
}

registry.category("actions").add("chat_observer.dashboard", ChatObserverDashboard);
