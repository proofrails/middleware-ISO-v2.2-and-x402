// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

/**
 * @title MockEIP3009Token
 * @notice Minimal EIP-3009 mock for testing X402Facilitator.
 */
contract MockEIP3009Token {
    string public name = "MockUSDT0";
    string public symbol = "MUSDT0";
    uint8 public decimals = 6;

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(bytes32 => bool)) private _authUsed;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event AuthorizationUsed(address indexed authorizer, bytes32 indexed nonce);

    constructor() {
        // Mint test tokens to deployer
        balanceOf[msg.sender] = 1_000_000 * 10 ** 6;
    }

    function mint(address to, uint256 amount) external {
        balanceOf[to] += amount;
    }

    function authorizationState(address authorizer, bytes32 nonce) external view returns (bool) {
        return _authUsed[authorizer][nonce];
    }

    // solhint-disable-next-line func-name-mixedcase
    function DOMAIN_SEPARATOR() external pure returns (bytes32) {
        return bytes32(0);
    }

    function transferWithAuthorization(
        address from,
        address to,
        uint256 value,
        uint256 validAfter,
        uint256 validBefore,
        bytes32 nonce,
        uint8,   // v
        bytes32, // r
        bytes32  // s
    ) public {
        require(block.timestamp > validAfter, "Not yet valid");
        require(block.timestamp < validBefore, "Expired");
        require(!_authUsed[from][nonce], "Nonce used");
        require(balanceOf[from] >= value, "Insufficient balance");

        _authUsed[from][nonce] = true;
        balanceOf[from] -= value;
        balanceOf[to] += value;

        emit Transfer(from, to, value);
        emit AuthorizationUsed(from, nonce);
    }

    function receiveWithAuthorization(
        address from,
        address to,
        uint256 value,
        uint256 validAfter,
        uint256 validBefore,
        bytes32 nonce,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        require(msg.sender == to, "Caller must be recipient");
        transferWithAuthorization(from, to, value, validAfter, validBefore, nonce, v, r, s);
    }
}
