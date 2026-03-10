// Wallet provider discovery helpers.
//
// Goal: reliably find an EIP-1193 provider in environments with:
// - MetaMask
// - multiple injected wallets (ethereum.providers)
// - legacy window.web3
// - EIP-6963 provider discovery

export type EthereumProvider = any;

export type DetectProviderOptions = {
  /**
   * Max time to wait for provider injection / discovery.
   * Some browsers (notably Brave) and extensions can inject later than initial page load.
   */
  timeoutMs?: number;
  /** Prefer MetaMask when multiple injected providers exist. */
  preferMetaMask?: boolean;
};

function selectProvider(eth: any, preferMetaMask: boolean): any {
  if (!eth) return null;

  // Multiple wallet injection (MetaMask + others)
  if (Array.isArray(eth.providers) && eth.providers.length > 0) {
    if (preferMetaMask) {
      const mm = eth.providers.find((p: any) => p?.isMetaMask);
      return mm || eth.providers[0];
    }
    return eth.providers[0];
  }

  return eth;
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

/**
 * Best-effort EIP-1193 provider detection.
 *
 * Supports:
 * - MetaMask / other injected wallets (window.ethereum)
 * - multiple injected wallets (ethereum.providers)
 * - legacy window.web3
 * - EIP-6963 provider discovery
 * - late injection (polling + ethereum#initialized event)
 */
export async function detectEthereumProvider(opts: DetectProviderOptions = {}): Promise<EthereumProvider | null> {
  if (typeof window === "undefined") return null;

  const w = window as any;

  const timeoutMs = Math.max(0, Number(opts.timeoutMs ?? 1500));
  const preferMetaMask = opts.preferMetaMask ?? true;

  // Standard injection
  const eth0 = w.ethereum;
  if (eth0) return selectProvider(eth0, preferMetaMask);

  // Legacy injection
  if (w.web3?.currentProvider) return w.web3.currentProvider;

  // Some wallets dispatch this event once injection is done.
  // MetaMask documents this as a way to detect late injection.
  const waitForEthereumInitialized = new Promise<void>((resolve) => {
    const onInit = () => {
      try {
        window.removeEventListener("ethereum#initialized", onInit as any);
      } catch {
        // ignore
      }
      resolve();
    };
    window.addEventListener("ethereum#initialized", onInit as any, { once: true } as any);
  });

  // EIP-6963 (multi-provider discovery)
  const providers: any[] = [];
  const handler = (event: any) => {
    const p = event?.detail?.provider;
    if (p) providers.push(p);
  };

  window.addEventListener("eip6963:announceProvider", handler as any);
  try {
    // Ask wallets to announce themselves.
    window.dispatchEvent(new Event("eip6963:requestProvider"));

    // Wait for either ethereum injection, ethereum#initialized, or timeout.
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      if (w.ethereum) return selectProvider(w.ethereum, preferMetaMask);
      if (providers.length) {
        const mm = preferMetaMask ? providers.find((p) => p?.isMetaMask) : null;
        return mm || providers[0];
      }

      // Give the event loop time; also allow the ethereum#initialized event path.
      await Promise.race([sleep(75), waitForEthereumInitialized]);
    }
  } finally {
    window.removeEventListener("eip6963:announceProvider", handler as any);
  }

  // Final fallback: some environments inject without EIP-6963 announcements.
  if (w.ethereum) return selectProvider(w.ethereum, preferMetaMask);
  return null;
}
