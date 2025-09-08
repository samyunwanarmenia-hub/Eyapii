// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/math/SafeMath.sol";

contract USDToken is ERC20, Ownable, ReentrancyGuard {
    using SafeMath for uint256;

    uint256 public constant USD_RATE = 1000; // 1 USD = 1000 USD-токенов (18 decimals)
    address public paymentReceiver; // Твой кошелёк для DASH
    mapping(address => uint256) public gameBalances; // Игровые балансы USD-токенов

    event TokensMinted(address indexed user, uint256 amount, uint256 usdPaid);
    event TokensBurned(address indexed user, uint256 amount);

    constructor(address _paymentReceiver) ERC20("Game USD", "USD") Ownable(msg.sender) {
        paymentReceiver = _paymentReceiver;
        _mint(address(this), 1_000_000 * 10**18); // Начальная эмиссия
    }

    // Минтинг токенов за оплату
    function mintForPayment(address user, uint256 usdAmount) external onlyOwner nonReentrant {
        require(usdAmount > 0, "Invalid amount");
        uint256 tokenAmount = usdAmount.mul(USD_RATE); // 1 USD = 1000 USD-токенов
        gameBalances[user] = gameBalances[user].add(tokenAmount);
        _mint(user, tokenAmount);
        emit TokensMinted(user, tokenAmount, usdAmount);
    }

    // Сжигание токенов (например, для вывода мощности)
    function burnFromGame(address user, uint256 amount) external onlyOwner nonReentrant {
        require(gameBalances[user] >= amount, "Insufficient game balance");
        gameBalances[user] = gameBalances[user].sub(amount);
        _burn(user, amount);
        emit TokensBurned(user, amount);
    }

    // Обновление кошелька для DASH
    function updatePaymentReceiver(address newReceiver) external onlyOwner {
        require(newReceiver != address(0), "Invalid address");
        paymentReceiver = newReceiver;
    }
}