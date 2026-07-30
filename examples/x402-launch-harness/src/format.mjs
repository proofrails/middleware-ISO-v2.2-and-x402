const RESET = '\u001b[0m';
const BOLD = '\u001b[1m';
const DIM = '\u001b[2m';
const GREEN = '\u001b[32m';
const RED = '\u001b[31m';
const CYAN = '\u001b[36m';

export function title(text) {
  console.log(`\n${BOLD}${text}${RESET}`);
}

export function field(label, value) {
  console.log(`${CYAN}${label.padEnd(20)}${RESET}${value}`);
}

export function note(text) {
  console.log(`${DIM}${text}${RESET}`);
}

export function check(label, ok, detail = '') {
  const mark = ok ? `${GREEN}PASS${RESET}` : `${RED}FAIL${RESET}`;
  console.log(`${label.padEnd(34)}${mark}${detail ? `  ${DIM}${detail}${RESET}` : ''}`);
}

export function short(hex, lead = 6, tail = 4) {
  if (typeof hex !== 'string' || hex.length <= lead + tail + 1) return String(hex);
  return `${hex.slice(0, lead)}\u2026${hex.slice(-tail)}`;
}

export function rule() {
  console.log(`${DIM}${'\u2500'.repeat(58)}${RESET}`);
}
