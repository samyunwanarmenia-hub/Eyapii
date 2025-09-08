import { config, t } from './config.js';
import { updateUserData, updateVotingTimer } from './uiService.js';

export async function joinPyramid(app) {
    // if (!app.userAccount) { // Removed
    //     await app.connectWallet(); // Removed
    //     if (!app.userAccount) return; // Removed
    // } // Removed
    document.getElementById('modal-title').textContent = t('modalJoin');
    document.getElementById('modal-input').placeholder = t('inputAmount');
    document.getElementById('modal').style.display = 'flex';
    app.modalMode = 'join';
}

export async function buyPower(app) {
    // if (!app.userAccount) { // Removed
    //     await app.connectWallet(); // Removed
    //     if (!app.userAccount) return; // Removed
    // } // Removed
    const canProceed = await app.fetchWithDebounce(app, `/check_transaction_limit/${app.user_id}`, { method: 'GET' });
    if (!canProceed?.allowed) {
        app.WebApp?.showAlert(t('transactionLimit'));
        return;
    }
    document.getElementById('modal-title').textContent = t('modalPower');
    document.getElementById('modal-input').placeholder = t('inputPower');
    document.getElementById('modal').style.display = 'flex';
    app.modalMode = 'power';
}

export async function withdraw(app) {
    // if (!app.userAccount) { // Removed
    //     await app.connectWallet(); // Removed
    //     if (!app.userAccount) return; // Removed
    // } // Removed
    const canProceed = await app.fetchWithDebounce(app, `/check_transaction_limit/${app.user_id}`, { method: 'GET' });
    if (!canProceed?.allowed) {
        app.WebApp?.showAlert(t('transactionLimit'));
        return;
    }
    try {
        // if (!app.contract) throw new Error("Contract not initialized"); // Removed
        // await app.contract.methods.withdraw().send({ from: app.userAccount }); // Replaced with API call
        const response = await app.fetchWithDebounce(app, `/withdraw/${app.user_id}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ amount: app.userData.gameBalances }) // Withdraw all for simplicity
        });
        if (response?.success) {
            app.WebApp?.showAlert(t('successWithdraw'));
            await updateUserData(app);
        } else {
            throw new Error(response?.error || 'Withdrawal failed');
        }
    } catch (error) {
        console.error('Withdraw наебнулся:', error);
        app.WebApp?.showAlert(t('errorWithdraw') + `: ${error.message}`);
    }
}

export async function joinGuild(app) {
    // if (!app.userAccount) { // Removed
    //     await app.connectWallet(); // Removed
    //     if (!app.userAccount) return; // Removed
    // } // Removed
    document.getElementById('modal-title').textContent = t('modalGuild');
    document.getElementById('modal-input').placeholder = t('inputGuild');
    document.getElementById('modal').style.display = 'flex';
    app.modalMode = 'guild';
}

export async function votePayout(app) {
    // if (!app.userAccount) { // Removed
    //     await app.connectWallet(); // Removed
    //     if (!app.userAccount) return; // Removed
    // } // Removed
    if (app.userData.investment < 1000) {
        app.WebApp?.showAlert(t('ru') === 'ru' ? 'Нужно вложить 1000+ USD для голосования!' : 'Need to invest 1000+ USD to vote!');
        return;
    }
    document.getElementById('modal-title').textContent = t('modalVote');
    document.getElementById('modal-input').placeholder = t('inputVote');
    document.getElementById('modal').style.display = 'flex';
    app.modalMode = 'vote';
}

export async function submitVote(app) {
    const newPercent = Number(document.getElementById('payout-input').value);
    if (newPercent < 10 || newPercent > 50) {
        app.WebApp?.showAlert(t('invalidVote'));
        return;
    }
    try {
        // if (!app.contract) throw new Error("Contract not initialized"); // Removed
        // await app.contract.methods.votePayout(newPercent * 100).send({ from: app.userAccount }); // Replaced with API call
        const response = await app.fetchWithDebounce(app, `/vote_payout/${app.user_id}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ percent: newPercent })
        });
        if (response?.success) {
            app.WebApp?.showAlert(t('successVote'));
            await updateVotingTimer(app); // This will now just show "Not active"
        } else {
            throw new Error(response?.error || 'Voting failed');
        }
    } catch (error) {
        console.error('VotePayout наебнулся:', error);
        app.WebApp?.showAlert(t('errorVote') + `: ${error.message}`);
    }
}

export async function showPaymentModal(app) {
    // if (!app.userAccount) { // Removed
    //     await app.connectWallet(); // Removed
    //     if (!app.userAccount) return; // Removed
    // } // Removed
    document.getElementById('modal-title').textContent = t('modalPay');
    document.getElementById('payment-modal').style.display = 'flex';
}

export async function submitPayment(app) {
    const usdAmount = Number(document.getElementById('payment-input').value);
    if (usdAmount <= 0) {
        app.WebApp?.showAlert(t('ru') === 'ru' ? 'Недопустимая сумма!' : 'Invalid amount!');
        return;
    }
    try {
        const paymentResult = await app.createPayment(app, app.user_id, usdAmount);
        
        if (paymentResult.success) {
            // No direct minting on frontend. Backend will handle it after payment confirmation.
            // For now, we'll simulate success and update user data.
            app.WebApp?.showAlert(t('successPayment'));
            await updateUserData(app);
        } else {
            throw new Error(paymentResult.error || 'Payment failed');
        }
    } catch (error) {
        console.error('Payment наебнулся:', error);
        app.WebApp?.showAlert(t('errorPayment') + `: ${error.message}`);
    }
    closeModal();
}

export function closeModal() {
    document.getElementById('modal').style.display = 'none';
    document.getElementById('payment-modal').style.display = 'none';
    document.getElementById('modal-input').value = '';
    document.getElementById('payment-input').value = '';
}

export async function submitModal(app) {
    const value = document.getElementById('modal-input').value;
    closeModal();
    try {
        let response;
        if (app.modalMode === 'join') {
            const amount = parseFloat(value);
            if (isNaN(amount) || amount <= 0) {
                app.WebApp?.showAlert(t('invalidAmount'));
                return;
            }
            // if (!app.contract) throw new Error("Contract not initialized"); // Removed
            // await app.contract.methods.join("0x0000000000000000000000000000000000000000", app.web3.utils.toWei(amount.toString(), 'ether')).send({ from: app.userAccount, value: app.web3.utils.toWei(amount.toString(), 'ether') }); // Replaced with API call
            response = await app.fetchWithDebounce(app, `/join/${app.user_id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: app.userData.name, amount: amount, referrer_id: null })
            });
            if (response?.success) {
                app.WebApp?.showAlert(t('successJoin'));
            } else {
                throw new Error(response?.error || 'Join failed');
            }
        } else if (app.modalMode === 'power') {
            const powerAmount = parseInt(value);
            if (isNaN(powerAmount) || powerAmount <= 0) {
                app.WebApp?.showAlert(t('invalidPower'));
                return;
            }
            // if (!app.contract) throw new Error("Contract not initialized"); // Removed
            // await app.contract.methods.buyPower(powerAmount).send({ from: app.userAccount }); // Replaced with API call
            response = await app.fetchWithDebounce(app, `/buy_power/${app.user_id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ amount: powerAmount })
            });
            if (response?.success) {
                app.WebApp?.showAlert(t('successPower'));
            } else {
                throw new Error(response?.error || 'Buy power failed');
            }
        } else if (app.modalMode === 'guild') {
            const guildId = parseInt(value);
            if (isNaN(guildId) || guildId <= 0) {
                app.WebApp?.showAlert(t('invalidGuild'));
                return;
            }
            // if (!app.contract) throw new Error("Contract not initialized"); // Removed
            // await app.contract.methods.joinGuild(guildId).send({ from: app.userAccount }); // Replaced with API call
            response = await app.fetchWithDebounce(app, `/join_guild/${app.user_id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ guild_id: guildId })
            });
            if (response?.success) {
                app.WebApp?.showAlert(t('successGuild'));
            } else {
                throw new Error(response?.error || 'Join guild failed');
            }
        } else if (app.modalMode === 'vote') {
            const newPercent = parseFloat(value);
            if (isNaN(newPercent) || newPercent < 10 || newPercent > 50) {
                app.WebApp?.showAlert(t('invalidVote'));
                return;
            }
            // if (!app.contract) throw new Error("Contract not initialized"); // Removed
            // await app.contract.methods.votePayout(newPercent * 100).send({ from: app.userAccount }); // Replaced with API call
            response = await app.fetchWithDebounce(app, `/vote_payout/${app.user_id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ percent: newPercent })
            });
            if (response?.success) {
                app.WebApp?.showAlert(t('successVote'));
            } else {
                throw new Error(response?.error || 'Voting failed');
            }
        }
        await updateUserData(app);
    } catch (error) {
        console.error('Ошибка в submitModal:', error);
        app.WebApp?.showAlert(t('errorApi') + `: ${error.message}`);
    }
}

export async function showLeaderboard(app) {
    document.getElementById('leaderboard').style.display = 'block';
    await updateUserData(app);
    app.updateLeaderboard(app); // Pass app to updateLeaderboard
}