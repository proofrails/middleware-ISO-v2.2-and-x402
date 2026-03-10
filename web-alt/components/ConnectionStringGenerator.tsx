"use client";

import React, { useState } from "react";
import { Copy, QrCode, Code } from "lucide-react";

type Format = "env" | "json" | "uri" | "shell" | "python" | "typescript";

interface Props {
  apiKey: string;
  apiUrl?: string;
  projectName?: string;
}

export default function ConnectionStringGenerator({ apiKey, apiUrl, projectName }: Props) {
  const [format, setFormat] = useState<Format>("env");
  const [copied, setCopied] = useState(false);
  const baseUrl = apiUrl || process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

  function generateString(): string {
    switch (format) {
      case "env":
        return `# .env file for ISO Middleware integration
ISO_MIDDLEWARE_URL=${baseUrl}
ISO_MIDDLEWARE_API_KEY=${apiKey}
${projectName ? `ISO_PROJECT_NAME=${projectName}` : ""}`;

      case "json":
        return JSON.stringify(
          {
            url: baseUrl,
            apiKey: apiKey,
            ...(projectName && { project: projectName }),
          },
          null,
          2
        );

      case "uri":
        const params = projectName ? `?project=${encodeURIComponent(projectName)}` : "";
        return `iso-mw://${apiKey}@${baseUrl.replace(/^https?:\/\//, "")}${params}`;

      case "shell":
        return `# Shell export commands
export ISO_MIDDLEWARE_URL="${baseUrl}"
export ISO_MIDDLEWARE_API_KEY="${apiKey}"
${projectName ? `export ISO_PROJECT_NAME="${projectName}"` : ""}`;

      case "python":
        return `# Python SDK example
from iso_middleware_sdk import ISOClient

client = ISOClient(
    base_url="${baseUrl}",
    api_key="${apiKey}"
)

# Example: List receipts
receipts = client.list_receipts(scope="mine")
print(f"Found {receipts['total']} receipts")`;

      case "typescript":
        return `// TypeScript SDK example
import IsoMiddlewareClient from "iso-middleware-sdk";

const client = new IsoMiddlewareClient({
  baseUrl: "${baseUrl}",
  apiKey: "${apiKey}"
});

// Example: List receipts
const receipts = await client.listReceipts({ scope: "mine" });
console.log(\`Found \${receipts.total} receipts\`);`;

      default:
        return "";
    }
  }

  async function copyToClipboard() {
    try {
      await navigator.clipboard.writeText(generateString());
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
    }
  }

  const formats: Array<{ value: Format; label: string; icon?: any }> = [
    { value: "env", label: ".env File" },
    { value: "json", label: "JSON Config" },
    { value: "uri", label: "Connection URI" },
    { value: "shell", label: "Shell Export" },
    { value: "python", label: "Python Code", icon: Code },
    { value: "typescript", label: "TypeScript Code", icon: Code },
  ];

  return (
    <div className="rounded border p-3 bg-emerald-50 space-y-3">
      <div className="flex items-center justify-between">
        <div className="text-sm font-medium text-emerald-900">Connection String Generator</div>
        <button
          onClick={() => {/* QR code modal could be added here */}}
          className="rounded border border-emerald-200 px-2 py-1 text-xs hover:bg-emerald-100"
          title="Show QR Code (coming soon)"
        >
          <QrCode className="h-4 w-4" />
        </button>
      </div>

      <div>
        <label className="text-xs text-emerald-800 mb-1 block">Format</label>
        <select
          className="w-full border border-emerald-200 rounded px-3 py-2 text-sm bg-white"
          value={format}
          onChange={(e) => setFormat(e.target.value as Format)}
        >
          {formats.map((f) => (
            <option key={f.value} value={f.value}>
              {f.label}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="text-xs text-emerald-800 mb-1 block">Generated String</label>
        <div className="relative">
          <pre className="text-xs bg-slate-950 text-slate-100 p-3 rounded-lg overflow-auto max-h-48 font-mono">
{generateString()}
          </pre>
          <button
            onClick={copyToClipboard}
            className="absolute top-2 right-2 rounded bg-slate-800/80 hover:bg-slate-700 text-white px-2 py-1 text-xs flex items-center gap-1"
          >
            <Copy className="h-3 w-3" />
            {copied ? "Copied!" : "Copy"}
          </button>
        </div>
      </div>

      <div className="text-xs text-emerald-800">
        <strong>Usage:</strong> Copy this configuration to integrate external services with your ISO Middleware project.
        {format === "python" || format === "typescript" ? (
          <span> The code snippet shows how to use the SDK with your credentials.</span>
        ) : null}
      </div>
    </div>
  );
}
