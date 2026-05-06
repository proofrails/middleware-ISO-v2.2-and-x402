/**
 * Tests for X402Facilitator contract.
 *
 * Run:  npx hardhat test contracts/test/X402Facilitator.test.js
 *
 * Uses MockEIP3009Token — no real USDT0 or Flare RPC needed.
 */

import { expect } from "chai";
import hardhat from "hardhat";
const { ethers } = hardhat;

describe("X402Facilitator", function () {
  let facilitator;
  let token;
  let owner, payer, recipient, other;
  const AMOUNT = 1000n; // 0.001 USDT0 (6 decimals)

  // Helper: build a valid PaymentPayload for the mock token.
  // MockEIP3009Token skips signature verification, so v/r/s can be dummy values.
  async function makePayload(overrides = {}) {
    const now = BigInt(Math.floor(Date.now() / 1000));
    return {
      from: payer.address,
      to: recipient.address,
      token: await token.getAddress(),
      value: AMOUNT,
      validAfter: 0n,
      validBefore: now + 3600n,
      nonce: ethers.randomBytes(32),
      v: 27,
      r: ethers.ZeroHash,
      s: ethers.ZeroHash,
      ...overrides,
    };
  }

  beforeEach(async function () {
    [owner, payer, recipient, other] = await ethers.getSigners();

    // Deploy mock token
    const TokenFactory = await ethers.getContractFactory("MockEIP3009Token");
    token = await TokenFactory.deploy();

    // Mint tokens to payer
    await token.mint(payer.address, AMOUNT * 100n);

    // Deploy facilitator — owner is the recipient wallet
    const FacilitatorFactory = await ethers.getContractFactory("X402Facilitator");
    facilitator = await FacilitatorFactory.deploy(recipient.address);

    // Register token (called by owner = recipient)
    await facilitator.connect(recipient).addSupportedToken(await token.getAddress());
  });

  // ── settlePaymentAsPayee ────────────────────────────────────────────────────

  describe("settlePaymentAsPayee", function () {
    it("settles a valid receiveWithAuthorization and emits X402PaymentSettled", async function () {
      const payload = await makePayload();

      const tx = await facilitator.connect(recipient).settlePaymentAsPayee(payload);
      const receipt = await tx.wait();

      const iface = facilitator.interface;
      const event = receipt.logs
        .map((log) => { try { return iface.parseLog(log); } catch { return null; } })
        .find((e) => e?.name === "X402PaymentSettled");

      expect(event).to.not.be.undefined;
      expect(event.args.token.toLowerCase()).to.equal((await token.getAddress()).toLowerCase());
      expect(event.args.payer.toLowerCase()).to.equal(payer.address.toLowerCase());
      expect(event.args.recipient.toLowerCase()).to.equal(recipient.address.toLowerCase());
      expect(event.args.amount).to.equal(AMOUNT);
    });

    it("transfers tokens from payer to recipient", async function () {
      const payerBefore = await token.balanceOf(payer.address);
      const recipientBefore = await token.balanceOf(recipient.address);

      await facilitator.connect(recipient).settlePaymentAsPayee(await makePayload());

      expect(await token.balanceOf(payer.address)).to.equal(payerBefore - AMOUNT);
      expect(await token.balanceOf(recipient.address)).to.equal(recipientBefore + AMOUNT);
    });

    it("stores nonce in PaymentRecord", async function () {
      const nonce = ethers.randomBytes(32);
      const payload = await makePayload({ nonce });
      await facilitator.connect(recipient).settlePaymentAsPayee(payload);

      const id = ethers.keccak256(
        ethers.AbiCoder.defaultAbiCoder().encode(
          ["address", "address", "address", "uint256", "bytes32"],
          [payload.from, payload.to, payload.token, payload.value, payload.nonce]
        )
      );
      const record = await facilitator.getPayment(id);
      expect(record.nonce).to.equal(ethers.hexlify(nonce));
    });

    it("rejects unsupported token", async function () {
      const payload = await makePayload({ token: other.address });
      await expect(
        facilitator.connect(recipient).settlePaymentAsPayee(payload)
      ).to.be.revertedWithCustomError(facilitator, "TokenNotSupported");
    });

    it("rejects when caller is not recipient (prevents front-running)", async function () {
      await expect(
        facilitator.connect(other).settlePaymentAsPayee(await makePayload())
      ).to.be.revertedWithCustomError(facilitator, "InvalidPaymentPayload");
    });

    it("rejects expired authorization", async function () {
      const now = BigInt(Math.floor(Date.now() / 1000));
      const payload = await makePayload({ validBefore: now - 1n });
      await expect(
        facilitator.connect(recipient).settlePaymentAsPayee(payload)
      ).to.be.revertedWithCustomError(facilitator, "AuthorizationExpired");
    });

    it("rejects already-settled payment (idempotency)", async function () {
      const payload = await makePayload();
      await facilitator.connect(recipient).settlePaymentAsPayee(payload);

      await expect(
        facilitator.connect(recipient).settlePaymentAsPayee(payload)
      ).to.be.revertedWithCustomError(facilitator, "PaymentAlreadySettled");
    });

    it("rejects reused nonce (replay protection)", async function () {
      const nonce = ethers.randomBytes(32);
      const payload1 = await makePayload({ nonce });
      const payload2 = await makePayload({ nonce });

      await facilitator.connect(recipient).settlePaymentAsPayee(payload1);
      // After CEI fix, our payments record fires first → PaymentAlreadySettled.
      // For a different value/params same nonce, AuthorizationAlreadyUsed would fire.
      // Either way, replay is correctly rejected.
      await expect(
        facilitator.connect(recipient).settlePaymentAsPayee(payload2)
      ).to.be.revertedWithCustomError(facilitator, "PaymentAlreadySettled");
    });

    it("rejects zero recipient address", async function () {
      const payload = await makePayload({ to: ethers.ZeroAddress });
      await expect(
        facilitator.connect(recipient).settlePaymentAsPayee(payload)
      ).to.be.revertedWithCustomError(facilitator, "InvalidRecipient");
    });

    it("rejects zero-value payment (DEFAULT_MIN = 1)", async function () {
      const payload = await makePayload({ value: 0n });
      await expect(
        facilitator.connect(recipient).settlePaymentAsPayee(payload)
      ).to.be.revertedWithCustomError(facilitator, "InsufficientAmount");
    });

    it("rejects when per-token minimum is not met", async function () {
      await facilitator.connect(recipient).setMinimumAmount(await token.getAddress(), AMOUNT * 10n);
      await expect(
        facilitator.connect(recipient).settlePaymentAsPayee(await makePayload())
      ).to.be.revertedWithCustomError(facilitator, "InsufficientAmount");
    });

    it("accepts when amount meets per-token minimum", async function () {
      await facilitator.connect(recipient).setMinimumAmount(await token.getAddress(), AMOUNT);
      await token.mint(payer.address, AMOUNT * 10n);
      const payload = await makePayload({ value: AMOUNT });
      await expect(
        facilitator.connect(recipient).settlePaymentAsPayee(payload)
      ).to.not.be.reverted;
    });

    it("reverts when paused", async function () {
      await facilitator.connect(recipient).pause();
      await expect(
        facilitator.connect(recipient).settlePaymentAsPayee(await makePayload())
      ).to.be.revertedWithCustomError(facilitator, "EnforcedPause");
    });

    it("settles again after unpause", async function () {
      await facilitator.connect(recipient).pause();
      await facilitator.connect(recipient).unpause();
      await expect(
        facilitator.connect(recipient).settlePaymentAsPayee(await makePayload())
      ).to.not.be.reverted;
    });
  });

  // ── settlePayment ──────────────────────────────────────────────────────────

  describe("settlePayment", function () {
    it("settles via transferWithAuthorization and emits event", async function () {
      const payload = await makePayload();
      const tx = await facilitator.connect(other).settlePayment(payload);
      const receipt = await tx.wait();

      const event = receipt.logs
        .map((log) => { try { return facilitator.interface.parseLog(log); } catch { return null; } })
        .find((e) => e?.name === "X402PaymentSettled");

      expect(event).to.not.be.undefined;
      expect(event.args.amount).to.equal(AMOUNT);
    });

    it("can be called by anyone (not just recipient)", async function () {
      await expect(
        facilitator.connect(other).settlePayment(await makePayload())
      ).to.not.be.reverted;
    });

    it("rejects zero-value payment", async function () {
      const payload = await makePayload({ value: 0n });
      await expect(
        facilitator.connect(other).settlePayment(payload)
      ).to.be.revertedWithCustomError(facilitator, "InsufficientAmount");
    });
  });

  // ── verifyPayment ──────────────────────────────────────────────────────────

  describe("verifyPayment", function () {
    it("returns valid=true for a fresh unsettled payment", async function () {
      const payload = await makePayload();
      const [, valid] = await facilitator.verifyPayment(payload);
      expect(valid).to.be.true;
    });

    it("returns valid=false for unsupported token", async function () {
      const payload = await makePayload({ token: other.address });
      const [, valid] = await facilitator.verifyPayment(payload);
      expect(valid).to.be.false;
    });

    it("returns valid=false for expired authorization", async function () {
      const now = BigInt(Math.floor(Date.now() / 1000));
      const payload = await makePayload({ validBefore: now - 1n });
      const [, valid] = await facilitator.verifyPayment(payload);
      expect(valid).to.be.false;
    });

    it("returns valid=false after settlement", async function () {
      const payload = await makePayload();
      await facilitator.connect(recipient).settlePaymentAsPayee(payload);

      const [, valid] = await facilitator.verifyPayment(payload);
      expect(valid).to.be.false;
    });

    it("returns valid=false for zero-value payment", async function () {
      const payload = await makePayload({ value: 0n });
      const [, valid] = await facilitator.verifyPayment(payload);
      expect(valid).to.be.false;
    });
  });

  // ── Admin ──────────────────────────────────────────────────────────────────

  describe("admin", function () {
    it("only owner can add supported token", async function () {
      await expect(
        facilitator.connect(other).addSupportedToken(other.address)
      ).to.be.reverted;
    });

    it("addSupportedToken rejects zero address", async function () {
      await expect(
        facilitator.connect(recipient).addSupportedToken(ethers.ZeroAddress)
      ).to.be.revertedWithCustomError(facilitator, "ZeroAddress");
    });

    it("only owner can set minimum amount", async function () {
      await expect(
        facilitator.connect(other).setMinimumAmount(await token.getAddress(), 1n)
      ).to.be.reverted;
    });

    it("removeSupportedToken clears minimumAmounts", async function () {
      await facilitator.connect(recipient).setMinimumAmount(await token.getAddress(), 9999n);
      await facilitator.connect(recipient).removeSupportedToken(await token.getAddress());
      expect(await facilitator.minimumAmounts(await token.getAddress())).to.equal(0n);
    });

    it("no funds are trapped — contract holds zero balance after settlement", async function () {
      await facilitator.connect(recipient).settlePaymentAsPayee(await makePayload());
      const contractBalance = await token.balanceOf(await facilitator.getAddress());
      expect(contractBalance).to.equal(0n);
    });

    it("only owner can pause", async function () {
      await expect(facilitator.connect(other).pause()).to.be.reverted;
    });
  });

  // ── View helpers ──────────────────────────────────────────────────────────

  describe("view helpers", function () {
    it("isNonceUsed returns false before use", async function () {
      const nonce = ethers.randomBytes(32);
      expect(
        await facilitator.isNonceUsed(await token.getAddress(), payer.address, nonce)
      ).to.be.false;
    });

    it("isNonceUsed returns true after settlement", async function () {
      const nonce = ethers.randomBytes(32);
      const payload = await makePayload({ nonce });
      await facilitator.connect(recipient).settlePaymentAsPayee(payload);
      expect(
        await facilitator.isNonceUsed(await token.getAddress(), payer.address, nonce)
      ).to.be.true;
    });

    it("getPayment returns settled record with nonce", async function () {
      const nonce = ethers.randomBytes(32);
      const payload = await makePayload({ nonce });
      await facilitator.connect(recipient).settlePaymentAsPayee(payload);

      const id = ethers.keccak256(
        ethers.AbiCoder.defaultAbiCoder().encode(
          ["address", "address", "address", "uint256", "bytes32"],
          [payload.from, payload.to, payload.token, payload.value, payload.nonce]
        )
      );
      const record = await facilitator.getPayment(id);
      expect(record.settled).to.be.true;
      expect(record.amount).to.equal(AMOUNT);
      expect(record.nonce).to.equal(ethers.hexlify(nonce));
    });
  });
});
