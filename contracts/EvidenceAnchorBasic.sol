// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// @title EvidenceAnchorBasic
/// @notice Basic evidence anchoring contract (same as original EvidenceAnchor)
/// @dev Simple, gas-efficient design for single-signer anchoring
contract EvidenceAnchorBasic {
    event EvidenceAnchored(bytes32 bundleHash, address indexed sender, uint256 ts);

    function anchorEvidence(bytes32 bundleHash) external {
        emit EvidenceAnchored(bundleHash, msg.sender, block.timestamp);
    }

    /// @notice Get contract version
    /// @return Version identifier
    function version() external pure returns (string memory) {
        return "basic-v1";
    }
}
