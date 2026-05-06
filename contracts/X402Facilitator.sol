// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title IEIP3009
 * @notice Interface for EIP-3009 authorization methods
 */
interface IEIP3009 {
    function transferWithAuthorization(
        address from,
        address to,
        uint256 value,
        uint256 validAfter,
        uint256 validBefore,
        bytes32 nonce,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external;

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
    ) external;

    function authorizationState(address authorizer, bytes32 nonce) external view returns (bool);

    // solhint-disable-next-line func-name-mixedcase
    function DOMAIN_SEPARATOR() external view returns (bytes32);
}

/**
 * @title X402Facilitator
 * @notice x402-compatible payment facilitator for EIP-3009 tokens (USDT0 on Flare mainnet).
 * @dev Audit status: internal review — deploy to testnet (Coston2) and commission external
 *      audit before mainnet use with significant value.
 *
 * Settlement modes
 * ----------------
 *   settlePaymentAsPayee  — uses transferWithAuthorization, restricted to msg.sender == to.
 *                           Only the payee server/wallet can call this path through the
 *                           facilitator. receiveWithAuthorization cannot be used here because
 *                           a contract caller cannot satisfy its msg.sender == to invariant.
 *   settlePayment         — uses transferWithAuthorization (callable by anyone).
 *                           Server-submitted mode; see GRIEFING note below.
 *
 * GRIEFING NOTE: A third party can observe a pending settlePaymentAsPayee tx and front-run
 * it by calling settlePayment with the same payload. The funds still arrive at payload.to
 * (correct recipient) because EIP-3009 sigs bind the destination. The payee's tx reverts
 * and wastes gas. Mitigation: use private mempool (Flashbots, FastLane) on mainnet.
 *
 * Security properties
 * -------------------
 *   - CEI pattern followed: all state writes happen before external token calls
 *   - NonReentrant on all settlement paths
 *   - Pausable for emergency stop
 *   - Zero-value payments rejected
 *   - Zero-address recipient rejected
 *   - Both settlement functions check our record AND the token's authorizationState
 *     before writing state, preventing double-settlement across paths
 */
contract X402Facilitator is Ownable, ReentrancyGuard, Pausable {
    struct PaymentRecord {
        address from;
        address to;
        address token;
        uint256 amount;
        bytes32 nonce;       // EIP-3009 nonce, for cross-reference with token.authorizationState
        uint256 timestamp;
        bool settled;
    }

    struct PaymentPayload {
        address from;
        address to;
        address token;
        uint256 value;
        uint256 validAfter;
        uint256 validBefore;
        bytes32 nonce;
        uint8 v;
        bytes32 r;
        bytes32 s;
    }

    // Supported EIP-3009 tokens (allowlist controlled by owner)
    mapping(address => bool) public supportedTokens;

    // Minimum accepted amount per token (raw units). 0 = not configured (use DEFAULT_MIN).
    mapping(address => uint256) public minimumAmounts;

    // Absolute floor to prevent dust/spam even when no per-token minimum is set.
    // Operators should override per-token via setMinimumAmount.
    uint256 public constant DEFAULT_MIN = 1;

    // Payment records keyed by paymentId — ensures idempotency across both settlement paths
    mapping(bytes32 => PaymentRecord) public payments;

    // ── Events ──────────────────────────────────────────────────────────────

    event TokenAdded(address indexed token);
    event TokenRemoved(address indexed token);
    event MinimumAmountSet(address indexed token, uint256 amount);

    /**
     * @notice Emitted on every successful settlement.
     * @dev paymentId = keccak256(from, to, token, value, nonce) — deterministic, replayable off-chain.
     */
    event X402PaymentSettled(
        address indexed token,
        address indexed payer,
        address indexed recipient,
        uint256 amount,
        bytes32 nonce,
        bytes32 paymentId
    );

    // ── Errors ───────────────────────────────────────────────────────────────

    error TokenNotSupported();
    error PaymentAlreadySettled();
    error AuthorizationAlreadyUsed();
    error InvalidPaymentPayload();
    error InsufficientAmount(uint256 provided, uint256 minimum);
    error InvalidRecipient();
    error AuthorizationExpired();
    error AuthorizationNotYetValid();
    error ZeroAddress();

    // ── Constructor ──────────────────────────────────────────────────────────

    /**
     * @param _owner Address that will own this contract (receives onlyOwner privileges).
     *               Pass the deployer's address or a multisig.
     */
    constructor(address _owner) Ownable(_owner) {
        if (_owner == address(0)) revert ZeroAddress();
    }

    // ── Admin ────────────────────────────────────────────────────────────────

    function addSupportedToken(address token) external onlyOwner {
        if (token == address(0)) revert ZeroAddress();
        supportedTokens[token] = true;
        emit TokenAdded(token);
    }

    function removeSupportedToken(address token) external onlyOwner {
        supportedTokens[token] = false;
        minimumAmounts[token] = 0; // clear per-token minimum to avoid stale state on re-add
        emit TokenRemoved(token);
    }

    function setMinimumAmount(address token, uint256 amount) external onlyOwner {
        minimumAmounts[token] = amount;
        emit MinimumAmountSet(token, amount);
    }

    /** @notice Emergency stop — blocks new settlements while investigations proceed. */
    function pause() external onlyOwner { _pause(); }
    function unpause() external onlyOwner { _unpause(); }

    // ── Settlement ───────────────────────────────────────────────────────────

    /**
     * @notice Settle via transferWithAuthorization, restricted to the payee.
     * @dev msg.sender must equal payload.to — only the recipient server/wallet
     *      can call this function through the facilitator. Uses transferWithAuthorization
     *      because a contract caller cannot satisfy receiveWithAuthorization's
     *      `msg.sender == to` check (msg.sender would be this contract, not the payee).
     *      CEI order: checks → effects (state write) → interaction (token call).
     */
    function settlePaymentAsPayee(
        PaymentPayload calldata payload
    ) external nonReentrant whenNotPaused returns (bytes32 paymentId) {
        // ── Checks ──────────────────────────────────────────────────────────
        if (!supportedTokens[payload.token]) revert TokenNotSupported();
        if (payload.to == address(0)) revert InvalidRecipient();
        if (payload.to != msg.sender) revert InvalidPaymentPayload();

        _validateTimeWindow(payload.validAfter, payload.validBefore);
        _validateAmount(payload.token, payload.value);

        paymentId = _paymentId(payload);
        if (payments[paymentId].settled) revert PaymentAlreadySettled();

        // External read — check token's own nonce registry before our state write
        if (IEIP3009(payload.token).authorizationState(payload.from, payload.nonce)) {
            revert AuthorizationAlreadyUsed();
        }

        // ── Effects (before external call — CEI) ────────────────────────────
        _record(paymentId, payload);

        // ── Interaction ──────────────────────────────────────────────────────
        IEIP3009(payload.token).transferWithAuthorization(
            payload.from,
            payload.to,
            payload.value,
            payload.validAfter,
            payload.validBefore,
            payload.nonce,
            payload.v,
            payload.r,
            payload.s
        );
    }

    /**
     * @notice Settle via transferWithAuthorization (callable by anyone with the sig).
     * @dev Use in server-submitted mode where the server submits on behalf of the payer.
     *      See GRIEFING NOTE in contract header regarding front-running of settlePaymentAsPayee.
     */
    function settlePayment(
        PaymentPayload calldata payload
    ) external nonReentrant whenNotPaused returns (bytes32 paymentId) {
        // ── Checks ──────────────────────────────────────────────────────────
        if (!supportedTokens[payload.token]) revert TokenNotSupported();
        if (payload.to == address(0)) revert InvalidRecipient();

        _validateTimeWindow(payload.validAfter, payload.validBefore);
        _validateAmount(payload.token, payload.value);

        paymentId = _paymentId(payload);
        if (payments[paymentId].settled) revert PaymentAlreadySettled();

        if (IEIP3009(payload.token).authorizationState(payload.from, payload.nonce)) {
            revert AuthorizationAlreadyUsed();
        }

        // ── Effects (before external call — CEI) ────────────────────────────
        _record(paymentId, payload);

        // ── Interaction ──────────────────────────────────────────────────────
        IEIP3009(payload.token).transferWithAuthorization(
            payload.from,
            payload.to,
            payload.value,
            payload.validAfter,
            payload.validBefore,
            payload.nonce,
            payload.v,
            payload.r,
            payload.s
        );
    }

    // ── Verification ─────────────────────────────────────────────────────────

    /**
     * @notice Check whether a payment can currently be settled (view only).
     * @return paymentId Deterministic ID for this authorization.
     * @return valid     True if the payment can be settled right now.
     */
    function verifyPayment(
        PaymentPayload calldata payload
    ) external view returns (bytes32 paymentId, bool valid) {
        paymentId = _paymentId(payload);

        if (!supportedTokens[payload.token]) return (paymentId, false);
        if (payments[paymentId].settled) return (paymentId, false);
        if (IEIP3009(payload.token).authorizationState(payload.from, payload.nonce)) return (paymentId, false);
        if (block.timestamp <= payload.validAfter || block.timestamp >= payload.validBefore) return (paymentId, false);

        uint256 min = minimumAmounts[payload.token];
        uint256 effectiveMin = min > 0 ? min : DEFAULT_MIN;
        if (payload.value < effectiveMin) return (paymentId, false);

        return (paymentId, true);
    }

    function getPayment(bytes32 paymentId) external view returns (PaymentRecord memory) {
        return payments[paymentId];
    }

    function isNonceUsed(address token, address authorizer, bytes32 nonce) external view returns (bool) {
        return IEIP3009(token).authorizationState(authorizer, nonce);
    }

    function getTokenDomainSeparator(address token) external view returns (bytes32) {
        return IEIP3009(token).DOMAIN_SEPARATOR();
    }

    // ── Internal ─────────────────────────────────────────────────────────────

    function _validateTimeWindow(uint256 validAfter, uint256 validBefore) internal view {
        if (block.timestamp <= validAfter) revert AuthorizationNotYetValid();
        if (block.timestamp >= validBefore) revert AuthorizationExpired();
    }

    function _validateAmount(address token, uint256 value) internal view {
        uint256 min = minimumAmounts[token];
        uint256 effectiveMin = min > 0 ? min : DEFAULT_MIN;
        if (value < effectiveMin) revert InsufficientAmount(value, effectiveMin);
    }

    function _record(bytes32 paymentId, PaymentPayload calldata payload) internal {
        payments[paymentId] = PaymentRecord({
            from: payload.from,
            to: payload.to,
            token: payload.token,
            amount: payload.value,
            nonce: payload.nonce,
            timestamp: block.timestamp,
            settled: true
        });
        emit X402PaymentSettled(payload.token, payload.from, payload.to, payload.value, payload.nonce, paymentId);
    }

    function _paymentId(PaymentPayload calldata payload) internal pure returns (bytes32) {
        return keccak256(abi.encode(payload.from, payload.to, payload.token, payload.value, payload.nonce));
    }
}
