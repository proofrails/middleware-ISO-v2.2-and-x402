#!/usr/bin/env node
import { readFileSync } from 'node:fs';
import { preflight } from './src/preflight.mjs';
import { record } from './src/record.mjs';
import { verify } from './src/verify.mjs';

const [mode, ...args] = process.argv.slice(2);

const usage = `ProofRails x402 launch harness

  node harness.mjs preflight            read-only checks, never signs
  node harness.mjs record               ONE approved payment, then follow the receipt
  node harness.mjs verify <receipt_id> [--settlement-tx=0x..] [--run=runs/run-x.json]
                                        independent bundle + Flare anchor verification
`;

try {
  if (mode === 'preflight') {
    const result = await preflight();
    process.exit(result.ready_for_record ? 0 : 1);
  } else if (mode === 'record') {
    const result = await record({ approvalToken: process.env.APPROVED_PAYMENT_ID });
    process.exit(result.ok ? 0 : 1);
  } else if (mode === 'verify') {
    const flag = (name) => args.find((a) => a.startsWith(`--${name}=`))?.split('=')[1];
    const runFile = flag('run');
    const runData = runFile
      ? JSON.parse(readFileSync(runFile, 'utf8'))
      : flag('settlement-tx')
        ? { settlement_tx: flag('settlement-tx') }
        : null;
    const result = await verify(args[0], { runData });
    process.exit(result.ok ? 0 : 1);
  } else {
    console.log(usage);
    process.exit(mode ? 1 : 0);
  }
} catch (error) {
  console.error(`\nHARNESS ERROR  ${error.message}`);
  process.exit(1);
}
