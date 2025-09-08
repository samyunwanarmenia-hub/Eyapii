import { config, t } from './config.js';

export function getRankClass(rankName) {
    if (rankName.includes("Новичок") || rankName.includes("Novice")) return 0;
    if (rankName.includes("Босс") || rankName.includes("Boss")) return 1;
    if (rankName.includes("Император") || rankName.includes("Emperor")) return 2;
    return 0;
}

export function startTimer(app, duration) {
    let time = duration;
    const timer = setInterval(() => {
        const hours = Math.floor(time / 3600);
        const minutes = Math.floor((time % 3600) / 60);
        const seconds = time % 60;
        document.getElementById('timer').textContent = t('timer', {
            time: `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
        });
        if (--time < 0) clearInterval(timer);
    }, 1000);
}

export async function updateVotingTimer(app) {
    // Temporarily disable blockchain voting timer
    document.getElementById('voting-timer').textContent = t('noVoting');
    // if (!app.contract) return; // Removed
    // try {
    //     const votingEnd = await app.contract.methods.votingEnd().call(); // Removed
    //     if (votingEnd > Math.floor(Date.now() / 1000)) { // Removed
    //         const timeLeft = votingEnd - Math.floor(Date.now() / 1000); // Removed
    //         const hours = Math.floor(timeLeft / 3600); // Removed
    //         const minutes = Math.floor((timeLeft % 3600) / 60); // Removed
    //         const seconds = timeLeft % 60; // Removed
    //         document.getElementById('voting-timer').textContent = t('votingTimer', { // Removed
    //             time: `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}` // Removed
    //         }); // Removed
    //     } else { // Removed
    //         document.getElementById('voting-timer').textContent = t('noVoting'); // Removed
    //     } // Removed
    // } catch (error) { // Removed
    //     console.error('Ошибка таймера голосования:', error); // Removed
    // } // Removed
}

export function updateLeaderboard(app) {
    const leaderboardList = document.getElementById('leaderboard-list');
    leaderboardList.innerHTML = '';
    app.userData.leaderboard.forEach((player, index) => {
        const div = document.createElement('div');
        div.className = 'leaderboard-item';
        const tier = player.investment < 1000 ? '🥉 Bronze' : player.investment < 5000 ? '🥈 Silver' : '🥇 Gold';
        div.innerHTML = DOMPurify.sanitize(`${index + 1}. ${player.name} (${tier}): ${player.investment.toFixed(2)} USD`);
        leaderboardList.appendChild(div);
    });
}

export function updateFan(app, speed) {
    app.userData.fan_speed = speed;
    document.getElementById('fan-speed').textContent = t('fan', { speed: speed.toFixed(2) });
}

export function updateGuildInfo(app) {
    const guildInfo = document.getElementById('guild-info');
    if (app.userData.guild) {
        guildInfo.innerHTML = DOMPurify.sanitize(
            t('ru') === 'ru'
                ? `Гильдия: ${app.userData.guild.name}, Бонус: +${app.userData.guild.bonus}%`
                : `Guild: ${app.userData.guild.name}, Bonus: +${app.userData.guild.bonus}%`
        );
    } else {
        guildInfo.textContent = t('guildNone');
    }
}

export function updateQuests(app) {
    const questList = document.getElementById('quest-list');
    questList.innerHTML = '';
    app.userData.quests.forEach(quest => {
        const div = document.createElement('div');
        div.className = `quest ${quest.progress >= quest.total ? 'completed' : ''}`;
        div.innerHTML = DOMPurify.sanitize(
            `${quest.task}: Прогресс ${quest.progress}/${quest.total} (Награда: ${quest.reward})`
        );
        const progressBar = document.createElement('div');
        progressBar.className = 'progress-bar';
        const progressFill = document.createElement('div');
        progressFill.className = 'progress-fill';
        progressFill.style.width = `${(quest.progress / quest.total) * 100}%`;
        progressBar.appendChild(progressFill);
        div.appendChild(progressBar);
        questList.appendChild(div);
    });
}

export function updateAchievements(app) {
    const achievementList = document.getElementById('achievement-list');
    achievementList.innerHTML = '';
    app.userData.achievements.forEach(ach => {
        const div = document.createElement('div');
        div.className = `achievement ${ach.completed ? 'completed' : ''}`;
        div.innerHTML = DOMPurify.sanitize(`${ach.task}: ${ach.completed ? '✅' : '⏳'}`);
        achievementList.appendChild(div);
    });
}

export async function updateUserData(app) {
    // if (!app.userAccount && window.ethereum) { // Removed
    //     await app.connectWallet(); // Removed
    // } // Removed

    try {
        const userFromApi = await app.fetchWithDebounce(app, `/user/${app.user_id}`, { method: 'GET' });
        if (userFromApi) {
            app.userData = {
                ...app.userData,
                name: userFromApi.name || "Игрок",
                investment: userFromApi.investment || 0,
                gameBalances: userFromApi.gameBalances || 0,
                power: userFromApi.power || 0,
                referrals: userFromApi.referrals || 0,
                referrer: userFromApi.referrer || '0x0',
                guildId: userFromApi.guild_id || 0,
                rank: userFromApi.rank || "Новичок 🐣",
                vip: userFromApi.vip === 1,
                fan_speed: 1 + (userFromApi.power * 0.1) + (userFromApi.fan_speed_bonus || 0),
                quests: userFromApi.quests || [],
                achievements: userFromApi.achievements || [],
                leaderboard: userFromApi.leaderboard || []
            };
            // if (app.userData.guildId > 0 && app.contract) { // Removed
            //     const guildData = await app.contract.methods.guilds(app.userData.guildId).call(); // Removed
            //     app.userData.guild = { name: guildData.name, bonus: Number(guildData.bonus) / 100, members: Number(guildData.members) }; // Removed
            // } else { // Replaced with mock/API call
            //     app.userData.guild = null; // Removed
            // }
            // Mock guild data for now
            if (app.userData.guildId > 0) {
                // In a real scenario, you'd fetch guild data from your backend API
                app.userData.guild = { name: `Guild ${app.userData.guildId}`, bonus: 0.05, members: 10 };
            } else {
                app.userData.guild = null;
            }
        }
    } catch (error) {
        console.error('Ошибка получения данных пользователя с API:', error);
    }
    app.cache.userData = app.userData;
    await initUI(app);
}

export async function initUI(app) {
    document.getElementById('user-name').textContent = DOMPurify.sanitize(app.userData.name);
    document.getElementById('fan-speed').textContent = t('fan', { speed: app.userData.fan_speed.toFixed(2) });
    document.getElementById('eva-balance').textContent = app.userData.gameBalances.toFixed(2);
    document.getElementById('user-rank').textContent = DOMPurify.sanitize(app.userData.rank);
    document.getElementById('user-rank').className = `rank-${getRankClass(app.userData.rank)}`;
    document.querySelector('h1').innerHTML = t('welcome', { name: DOMPurify.sanitize(app.userData.name) }) + (app.userData.vip ? ' <span class="vip">[VIP]</span>' : '');
    document.querySelector('h2').textContent = t('title');
    document.querySelector('#event h2').textContent = t('event');
    document.querySelector('#quests h2').textContent = t('quests');
    document.querySelector('#achievements h2').textContent = t('achievements');
    document.querySelector('#guild h2').textContent = t('guild');
    document.querySelector('#voting h2').textContent = t('voting');
    document.getElementById('join-pyramid-btn').textContent = t('join');
    document.getElementById('buy-power-btn').textContent = t('buyPower');
    document.getElementById('withdraw-btn').textContent = t('withdraw');
    document.getElementById('join-guild-btn').textContent = t('joinGuild');
    document.getElementById('vote-payout-btn').textContent = t('vote');
    document.getElementById('show-leaderboard-btn').textContent = t('leaderboard');
    document.getElementById('pay-usd-btn').textContent = t('payUSD');
    updateGuildInfo(app);
    updateQuests(app);
    updateAchievements(app);
    updateLeaderboard(app);
    updateVotingTimer(app);
}