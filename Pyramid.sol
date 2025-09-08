// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface USDToken {
    function mintForPayment(address account, uint256 amount) external;
    function burnFromGame(address account, uint256 amount) external;
    function balanceOf(address account) external view returns (uint256);
    function transfer(address recipient, uint256 amount) external returns (bool);
}

contract Pyramid {
    USDToken public usdToken;
    address public usdTokenAddress;
    mapping(address => uint256) public gameBalances; // Replaced evaBalance with gameBalances
    mapping(address => address) public referrers;
    mapping(address => uint256) public referrals;
    uint256 public payoutPercent = 25;
    uint256 public constant MIN_INVESTMENT = 1e18; // 1 USD (assuming 18 decimals)
    uint256 public constant MAX_INVESTMENT = 1000e18; // 1000 USD

    event Join(address indexed user, uint256 amount);
    event Withdraw(address indexed user, uint256 amount);

    constructor(address _usdTokenAddress) {
        usdTokenAddress = _usdTokenAddress;
        usdToken = USDToken(_usdTokenAddress);
    }

    function join(address referrer, uint256 amount) external payable nonReentrant {
        require(amount >= MIN_INVESTMENT && amount <= MAX_INVESTMENT, "Invalid amount");
        require(msg.value == 0, "No ETH required, use USDToken");
        
        // Check if user has enough USDToken
        require(usdToken.balanceOf(msg.sender) >= amount, "Insufficient USDToken balance");
        
        // Burn tokens from user for joining the game
        usdToken.burnFromGame(msg.sender, amount);
        
        // Update game balances
        gameBalances[msg.sender] += amount;
        referrers[msg.sender] = referrer;
        referrals[referrer]++;
        
        emit Join(msg.sender, amount);
        
        // Distribute payout to referrer chain
        address current = referrer;
        uint256 payout = (amount * payoutPercent) / 100;
        while (current != address(0)) {
            gameBalances[current] += payout;
            // Mint tokens for referrer payout
            usdToken.mintForPayment(current, payout);
            current = referrers[current];
        }
    }

    function withdraw() external nonReentrant {
        uint256 amount = gameBalances[msg.sender];
        require(amount > 0, "No funds to withdraw");
        
        // Reset balance before transfer to prevent reentrancy
        gameBalances[msg.sender] = 0;
        
        // Mint tokens to user for withdrawal
        usdToken.mintForPayment(msg.sender, amount);
        
        emit Withdraw(msg.sender, amount);
    }
}

contract PyramidDAO {
    USDToken public usdToken;
    address public usdTokenAddress;
    mapping(address => uint256) public votes;
    uint256 public payoutPercent;
    uint256 public constant VOTING_THRESHOLD = 1000e18; // 1000 USDToken

    constructor(address _usdTokenAddress) {
        usdTokenAddress = _usdTokenAddress;
        usdToken = USDToken(_usdTokenAddress);
    }

    function votePayout(uint256 newPercent) external {
        require(usdToken.balanceOf(msg.sender) >= VOTING_THRESHOLD, "Not enough stake");
        votes[msg.sender] = newPercent;
    }

    function finalizePayout() external {
        uint256 total = 0;
        uint256 count = 0;
        // Iterate through voters (implementation depends on how votes are tracked)
        // This is a simplified version; in practice, you'd need a way to iterate mappings
        for (uint256 i = 0; i < count; i++) {
            // Assuming some way to access voters, this is placeholder logic
            address voter = address(uint160(i + 1)); // Placeholder for voter iteration
            if (votes[voter] > 0) {
                total += votes[voter];
                count++;
            }
        }
        require(count > 0, "No votes cast");
        payoutPercent = total / count;
    }
}