// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// @title FactoryRegistry
/// @notice Central registry for tracking all EvidenceAnchorFactory deployments
/// @dev Provides discovery, validation, and governance for factory contracts
contract FactoryRegistry {
    struct FactoryInfo {
        address factoryAddress;
        address deployer;
        uint256 deployedAt;
        string version;
        bool deprecated;
    }

    // Events
    event FactoryRegistered(
        address indexed factory,
        address indexed deployer,
        string version,
        uint256 timestamp
    );
    
    event FactoryDeprecated(
        address indexed factory,
        string reason,
        uint256 timestamp
    );
    
    event FactoryReactivated(
        address indexed factory,
        uint256 timestamp
    );

    // Storage
    address public owner;
    mapping(address => FactoryInfo) public factories;
    address[] public factoryList;
    mapping(address => address[]) public factoriesByDeployer;

    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "FactoryRegistry: not owner");
        _;
    }

    modifier onlyRegisteredFactory() {
        require(factories[msg.sender].factoryAddress != address(0), "FactoryRegistry: not registered factory");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /// @notice Register a new factory contract
    /// @param factory Address of the factory contract
    /// @param version Version string (e.g., "v1", "v2-create2", "multisig")
    function registerFactory(address factory, string calldata version) external {
        require(factory != address(0), "FactoryRegistry: invalid factory address");
        require(factories[factory].factoryAddress == address(0), "FactoryRegistry: factory already registered");

        FactoryInfo memory info = FactoryInfo({
            factoryAddress: factory,
            deployer: msg.sender,
            deployedAt: block.timestamp,
            version: version,
            deprecated: false
        });

        factories[factory] = info;
        factoryList.push(factory);
        factoriesByDeployer[msg.sender].push(factory);

        emit FactoryRegistered(factory, msg.sender, version, block.timestamp);
    }

    /// @notice Mark a factory as deprecated (governance)
    /// @param factory Address of the factory to deprecate
    /// @param reason Reason for deprecation
    function deprecateFactory(address factory, string calldata reason) external onlyOwner {
        require(factories[factory].factoryAddress != address(0), "FactoryRegistry: factory not found");
        require(!factories[factory].deprecated, "FactoryRegistry: already deprecated");

        factories[factory].deprecated = true;
        emit FactoryDeprecated(factory, reason, block.timestamp);
    }

    /// @notice Reactivate a deprecated factory (governance)
    /// @param factory Address of the factory to reactivate
    function reactivateFactory(address factory) external onlyOwner {
        require(factories[factory].factoryAddress != address(0), "FactoryRegistry: factory not found");
        require(factories[factory].deprecated, "FactoryRegistry: not deprecated");

        factories[factory].deprecated = false;
        emit FactoryReactivated(factory, block.timestamp);
    }

    /// @notice Check if a factory is valid and active
    /// @param factory Address to check
    /// @return isValid true if factory is registered and not deprecated
    function isValidFactory(address factory) external view returns (bool isValid) {
        FactoryInfo memory info = factories[factory];
        return info.factoryAddress != address(0) && !info.deprecated;
    }

    /// @notice Get all registered factories
    /// @return Array of factory addresses
    function getAllFactories() external view returns (address[] memory) {
        return factoryList;
    }

    /// @notice Get all factories deployed by a specific address
    /// @param deployer Address of the deployer
    /// @return Array of factory addresses
    function getFactoriesByDeployer(address deployer) external view returns (address[] memory) {
        return factoriesByDeployer[deployer];
    }

    /// @notice Get active (non-deprecated) factories
    /// @return active Array of active factory addresses
    function getActiveFactories() external view returns (address[] memory active) {
        uint256 count = 0;
        for (uint256 i = 0; i < factoryList.length; i++) {
            if (!factories[factoryList[i]].deprecated) {
                count++;
            }
        }

        active = new address[](count);
        uint256 idx = 0;
        for (uint256 i = 0; i < factoryList.length; i++) {
            if (!factories[factoryList[i]].deprecated) {
                active[idx++] = factoryList[i];
            }
        }
    }

    /// @notice Get detailed info about a factory
    /// @param factory Factory address
    /// @return info Struct with factory details
    function getFactoryInfo(address factory) external view returns (FactoryInfo memory info) {
        return factories[factory];
    }

    /// @notice Transfer registry ownership (governance)
    /// @param newOwner New owner address
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "FactoryRegistry: invalid new owner");
        owner = newOwner;
    }
}
