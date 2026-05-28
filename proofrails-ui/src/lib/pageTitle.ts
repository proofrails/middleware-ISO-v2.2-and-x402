export function getPageTitle(pathname: string): string {
  if (pathname.startsWith('/records/create')) return 'Create Proof Record';
  if (/^\/records\/[^/]+$/.test(pathname) && pathname !== '/records') return 'Proof Record Details';
  if (pathname === '/records' || pathname === '/') return 'Proof Records';
  if (pathname === '/verify') return 'Verify';
  if (pathname === '/settings') return 'Settings';
  if (pathname === '/docs') return 'Documentation';
  return 'ProofRails';
}
