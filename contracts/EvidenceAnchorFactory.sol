// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./EvidenceAnchor.sol";

/// @notice Simple factory that deploys a new EvidenceAnchor per request.
///         The deployer becomes the recorded owner for indexing/auditing.
contract EvidenceAnchorFactory {
    event AnchorDeployed(address indexed owner, address anchor, uint256 ts);

    function deploy() external returns (address anchor) {
        EvidenceAnchor a = new EvidenceAnchor();
        anchor = address(a);
        emit AnchorDeployed(msg.sender, anchor, block.timestamp);
    }
}
