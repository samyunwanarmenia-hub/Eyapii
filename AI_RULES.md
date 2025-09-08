# AI Rules for the Pyramid Wealth Application

This document outlines the core technologies used in the Pyramid Wealth application and provides guidelines for using specific libraries.

## Tech Stack Description

1.  **Backend Language**: Python, leveraging `asyncio` for efficient asynchronous operations.
2.  **Telegram Bot Framework**: `python-telegram-bot` is used for all interactions with the Telegram platform, handling commands, callbacks, and messages.
3.  **Blockchain Integration**: `web3.py` (Python) and `web3.js` (JavaScript) are employed for interacting with Ethereum Virtual Machine (EVM) compatible smart contracts.
4.  **Data Storage**: PostgreSQL serves as the primary relational database, managed asynchronously with `asyncpg`. Redis (`aioredis`) is used for caching, rate-limiting, and temporary data storage. SQLite is utilized for local database backups.
5.  **Machine Learning & AI**:
    *   `PyTorch` (`torch`) for deep learning models, specifically an LSTM for stability prediction.
    *   `scikit-learn` (`sklearn`) for anomaly detection using Isolation Forest.
    *   `Stable Baselines3` (`PPO`) for reinforcement learning to optimize in-game events.
6.  **Task Management**: `APScheduler` handles scheduled background jobs, while `Celery` (with Redis as a broker) manages asynchronous task queues.
7.  **Frontend Technologies**: The user interface is built with HTML, CSS, and vanilla JavaScript (ES Modules), integrated as a Telegram WebApp.
8.  **Data Visualization & UI Effects**: `D3.js` is used for rendering interactive referral trees, `Chart.js` for dynamic financial graphs, `three.js` for 3D animations (like the fan), and `particles.js` for visual particle effects.
9.  **Security & Utilities**: `DOMPurify` is crucial for sanitizing user-generated content on the frontend to prevent XSS attacks. `hashlib` and `py_ecc.bn128` are used for cryptographic operations, including ZKP-like proofs.
10. **Cloud Integration**: `boto3` is used for interacting with AWS S3, specifically for database backups.

## Library Usage Rules

To maintain consistency and efficiency, please adhere to the following guidelines when developing or modifying the application:

*   **Telegram Bot Interactions**: All Telegram bot functionalities (e.g., command handlers, callback queries, sending messages) must be implemented using the `python-telegram-bot` library.
*   **Database Operations**:
    *   For persistent data storage and complex queries, use `asyncpg` to interact with PostgreSQL.
    *   For caching, session management, and rate-limiting, use `aioredis` to interact with Redis.
    *   SQLite (`sqlite3`) is strictly for local database backup operations.
*   **Blockchain Smart Contract Interaction**:
    *   **Backend**: Use `web3.py` for all server-side interactions with smart contracts (e.g., `join`, `withdraw`, `mintForPayment`, `burnFromGame`, `votePayout`, `finalizePayout`, and listening for blockchain events).
    *   **Frontend**: Use `web3.js` for client-side wallet connections (e.g., MetaMask) and user-initiated smart contract calls.
*   **Machine Learning & AI Models**:
    *   `torch` (PyTorch) is designated for neural network-based models, such as the `AdvancedStabilityPredictor`.
    *   `sklearn` (IsolationForest) should be used for anomaly detection tasks.
    *   `stable_baselines3` (PPO) is to be used for reinforcement learning algorithms, particularly for event optimization.
*   **Scheduled Tasks**: All recurring background tasks should be managed using `APScheduler`.
*   **Asynchronous Task Queues**: For long-running or background tasks that need to be processed asynchronously, use `Celery`.
*   **Monitoring**: Integrate application metrics using `prometheus_client`.
*   **Frontend Data Visualization**:
    *   `D3.js` is the go-to library for creating and manipulating SVG-based data visualizations, such as the referral tree.
    *   `Chart.js` should be used for all chart and graph rendering (e.g., investment and payout trends).
*   **Frontend UI Effects**:
    *   `three.js` is for any 3D graphics rendering.
    *   `particles.js` is for adding particle effects to the UI.
*   **Frontend Security**: Always use `DOMPurify` to sanitize any user-generated content before it is inserted into the DOM to prevent Cross-Site Scripting (XSS) vulnerabilities.
*   **Styling**: Adhere to the existing inline CSS and the established "neon" aesthetic. Avoid introducing new CSS frameworks unless explicitly approved.
*   **External API Calls**: Use standard `fetch` API on the frontend and appropriate HTTP client libraries (e.g., `requests` or `aiohttp` if async) on the backend for external service integrations (e.g., NowPayments).
*   **Cryptography**: Use `hashlib` for general-purpose hashing and `py_ecc.bn128` for specific elliptic curve cryptography requirements (e.g., zero-knowledge proof-like mechanisms).
*   **Cloud Storage**: Use `boto3` for all interactions with AWS S3.