import { config, t } from './config.js';
import { debounce, fetchWithDebounce, createPayment } from './apiService.js';
import {
    initUI, updateUserData, getRankClass, startTimer, updateVotingTimer,
    updateLeaderboard, updateFan, updateGuildInfo, updateQuests, updateAchievements
} from './uiService.js';
import { initFan, initParticles, initTree, initChart } from './visualizationService.js';
import {
    joinPyramid, buyPower, withdraw, joinGuild, votePayout, submitVote,
    showPaymentModal, submitPayment, closeModal, submitModal, showLeaderboard
} from './appActions.js';
import { supabase } from '../integrations/supabase/client.js';

// Mock process.env for Supabase client compatibility in a browser environment
// This is a workaround if the Supabase client library internally checks for process.env
// even when explicit arguments are provided.
if (typeof window !== 'undefined' && !window.process) {
    window.process = { env: {} };
}

const app = {
    config: config,
    t: t,
    user_id: window.Telegram?.WebApp?.initDataUnsafe?.user?.id || '123',
    userData: {
        name: "Игрок",
        investment: 0,
        gameBalances: 0,
        power: 0,
        referrals: 0,
        referrer: '0x0',
        guildId: 0,
        rank: "Новичок 🐣",
        vip: false,
        fan_speed: 1,
        guild: null,
        tree: [{ name: "Император", children: [{ name: "Босс" }, { name: "Игрок" }] }],
        investments: [0, 0, 0, 0, 0],
        payouts: [0, 0, 0, 0, 0],
        quests: [],
        achievements: [],
        leaderboard: []
    },
    cache: {},
    WebApp: window.Telegram?.WebApp,
    supabase: supabase, // Добавляем клиент Supabase в объект app

    // Привязываем импортированные функции к объекту app
    debounce: debounce, // debounce не требует привязки к app
    fetchWithDebounce: (self, url, options) => fetchWithDebounce(self, url, options),
    createPayment: (self, userId, usdAmount) => createPayment(self, userId, usdAmount),
    initUI: (self) => initUI(self),
    updateUserData: (self) => updateUserData(self),
    getRankClass: getRankClass,
    startTimer: (self, duration) => startTimer(self, duration),
    updateVotingTimer: (self) => updateVotingTimer(self),
    updateLeaderboard: (self) => updateLeaderboard(self),
    updateFan: (self, speed) => updateFan(self, speed),
    updateGuildInfo: (self) => updateGuildInfo(self),
    updateQuests: (self) => updateQuests(self),
    updateAchievements: (self) => updateAchievements(self),
    initFan: (self) => initFan(self),
    initParticles: (self) => initParticles(self),
    initTree: (self) => initTree(self),
    initChart: (self) => initChart(self),
    joinPyramid: (self) => joinPyramid(self),
    buyPower: (self) => buyPower(self),
    withdraw: (self) => withdraw(self),
    joinGuild: (self) => joinGuild(self),
    votePayout: (self) => votePayout(self),
    submitVote: (self) => submitVote(self),
    showPaymentModal: (self) => showPaymentModal(self),
    submitPayment: (self) => submitPayment(self),
    closeModal: closeModal,
    submitModal: (self) => submitModal(self),
    showLeaderboard: (self) => showLeaderboard(self),

    async init() {
        if (this.WebApp) {
            this.WebApp.ready();
            this.WebApp.expand();
        }
        // await this.initWeb3(this); // Removed
        await this.updateUserData(this);
        this.initUI(this);
        this.startTimer(this, 24 * 3600);
        this.initFan(this);
        this.initParticles(this);
        this.initTree(this);
        this.initChart(this);

        // Add event listeners
        document.getElementById('join-pyramid-btn').addEventListener('click', () => this.joinPyramid(this));
        document.getElementById('buy-power-btn').addEventListener('click', () => this.buyPower(this));
        document.getElementById('withdraw-btn').addEventListener('click', () => this.withdraw(this));
        document.getElementById('join-guild-btn').addEventListener('click', () => this.joinGuild(this));
        document.getElementById('vote-payout-btn').addEventListener('click', () => this.votePayout(this));
        document.getElementById('submit-vote-btn').addEventListener('click', () => this.submitVote(this));
        document.getElementById('show-leaderboard-btn').addEventListener('click', () => this.showLeaderboard(this));
        document.getElementById('pay-usd-btn').addEventListener('click', () => this.showPaymentModal(this));
        document.getElementById('submit-modal-btn').addEventListener('click', () => this.submitModal(this));
        document.getElementById('close-modal-btn').addEventListener('click', () => this.closeModal());
        document.getElementById('submit-payment-btn').addEventListener('click', () => this.submitPayment(this));
        document.getElementById('close-payment-modal-btn').addEventListener('click', () => this.closeModal());


        window.addEventListener('resize', () => {
            this.config.tree.width = window.innerWidth < 600 ? window.innerWidth - 40 : 800;
            d3.select("#tree-svg").attr("width", this.config.tree.width);
            this.initTree(this);
        });
    }
};

// Update URLs in uiService.js