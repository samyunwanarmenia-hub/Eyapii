import { config, t } from './config.js';

export function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

export const fetchWithDebounce = debounce(async (app, url, options) => {
    try {
        const response = await fetch(`${config.api}${url}`, {
            ...options,
            headers: { ...options.headers, 'Authorization': `Bearer ${app.user_id}` }
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`HTTP error ${response.status}: ${errorData.error || response.statusText}`);
        }
        return await response.json();
    } catch (error) {
        console.error('API наебнулся:', error);
        app.WebApp?.showAlert(t('errorApi') + `: ${error.message}`);
        return null;
    }
}, 500);

export async function createPayment(app, userId, usdAmount) {
    try {
        // Call your backend API to initiate the payment
        const response = await fetchWithDebounce(app, '/create_payment', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: userId,
                amount: usdAmount
            })
        });
        return response;
    } catch (error) {
        console.error('Payment initiation error:', error);
        return { success: false, error: error.message };
    }
}