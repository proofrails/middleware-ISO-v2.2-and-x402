# Use Flare AI Skills

Flare AI Skills are MCP (Model Context Protocol) servers that give Claude Code accurate, up-to-date knowledge about Flare-specific APIs, contracts, and patterns. This repo ships with a `.claude/settings.json` that configures them automatically.

## Available skills

| Skill | Purpose |
|-------|---------|
| `flare-general` | Flare network overview, RPC URLs, block explorers, chain IDs |
| `flare-ftso` | FTSO v2 price feeds — contract addresses, data feeds, update frequency |
| `flare-fdc` | Flare Data Connector — proof generation, verification contracts |
| `flare-fassets` | FAssets — FXRP/FBTC/FDOGE minting, redemption, collateral |
| `flare-smart-accounts` | Smart Accounts — XRPL-origin users interacting with Flare EVM |

## Installation

When you open this repo in Claude Code, you may be prompted to install the Flare AI Skills MCP servers. Accept the prompt, or install manually:

```bash
npx -y @flare-foundation/flare-ai-skills flare-general
```

## Example prompts

### Configure Flare RPC and chain details

```
Use flare-general to give me the correct RPC URL, chain ID, and block explorer
for Flare mainnet and Coston2 testnet so I can update .env.example.
```

### Design FDC-backed evidence verification

```
Use flare-fdc to help me design a verification flow where ProofRails uses
the Flare Data Connector to verify an external payment event before generating
a receipt. Show me which FDC contracts to call and what proof structure to expect.
```

### Add FX price context to ISO reporting

```
Use flare-ftso to add a real-time USD/FLR exchange rate to the amount fields
in camt.053 statements. Show me how to query the FTSO v2 feed and which
feed ID to use for FLR/USD.
```

### Generate evidence for FAssets activity

```
Use flare-fassets to help me add support for FXRP and FBTC flows in ProofRails.
I want to generate pain.001 and camt.054 messages when FAssets are minted or
redeemed. What events should I watch and what contract ABIs do I need?
```

### Design XRPL-to-Flare user flows

```
Use flare-smart-accounts to design a flow where XRPL users can trigger
ProofRails receipt generation through Flare Smart Accounts without needing
an EVM wallet. What is the account mapping and how do I verify XRPL signatures?
```

## Implementation status

| Skill | ProofRails integration |
|-------|----------------------|
| `flare-general` | Implemented — Flare EVM anchoring uses Flare mainnet/Coston2 |
| `flare-ftso` | Implemented — FTSO v2 feeds used for FX lookup in premium endpoints |
| `flare-fdc` | Prototype — see [Flare-Native Implementations](../concepts/flare-native-implementations.md) |
| `flare-fassets` | Proposed — not yet implemented |
| `flare-smart-accounts` | Proposed — not yet implemented |

## See also

- [Flare-Native Implementations](../concepts/flare-native-implementations.md)
- [Flare Integration Guide](../FLARE_INTEGRATION.md)
