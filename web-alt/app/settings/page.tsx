"use client";

import React, { useState } from "react";
import { Code, Settings as SettingsIcon, Key, FolderGit } from "lucide-react";
import AssistantPanel from "../../components/AssistantPanel";
import ProjectsPanel from "../../components/ProjectsPanel";
import APIKeysPanel from "../../components/APIKeysPanel";
import ProjectConfigPanel from "../../components/ProjectConfigPanel";
import { buildSdk, downloadOpenApi, getConfig, putConfig } from "../../lib/api";

type Tab = "sdk" | "config" | "keys" | "projects";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("projects");
  const apiBase = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

  // SDK Builder state
  const [sdkLang, setSdkLang] = useState<"ts" | "python">("ts");
  const [sdkPackaging, setSdkPackaging] = useState<"none" | "npm" | "pypi">("none");
  const [sdkBase, setSdkBase] = useState(apiBase);
  const [sdkMessage, setSdkMessage] = useState<string | null>(null);

  // Config state
  const [cfg, setCfg] = useState<any>(null);
  const [cfgJson, setCfgJson] = useState("");

  function downloadBlob(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  const tabs: Array<{ id: Tab; label: string; icon: any }> = [
    { id: "projects", label: "Projects", icon: FolderGit },
    { id: "keys", label: "API Keys", icon: Key },
    { id: "config", label: "Configuration", icon: SettingsIcon },
    { id: "sdk", label: "SDK Builder", icon: Code },
  ];

  return (
    <div className="grid grid-cols-12 gap-4">
      {/* Left sidebar - Tab navigation */}
      <aside className="col-span-12 lg:col-span-3 space-y-4">
        <div className="card p-4">
          <div className="text-base font-semibold mb-3">Settings</div>
          <div className="space-y-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                    w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors text-left
                    ${activeTab === tab.id ? "bg-slate-900 text-white" : "text-slate-700 hover:bg-slate-100"}
                  `}
                >
                  <Icon className="h-4 w-4" />
                  {tab.label}
                </button>
              );
            })}
          </div>
        </div>

        <div className="card p-4 bg-slate-50">
          <div className="text-sm font-medium mb-2">Current Section</div>
          <div className="text-sm text-slate-600">
            {activeTab === "projects" && "Manage projects and SIWE authentication"}
            {activeTab === "keys" && "Create and manage API keys with connection strings"}
            {activeTab === "config" && "Configure anchoring, storage, and FX policies"}
            {activeTab === "sdk" && "Build SDKs and download OpenAPI spec"}
          </div>
        </div>
      </aside>

      {/* Center content - Tab panels */}
      <section className="col-span-12 lg:col-span-6 space-y-4">
        <div className="card p-4">
          <div className="text-lg font-bold mb-1">
            {tabs.find((t) => t.id === activeTab)?.label}
          </div>
          <div className="text-sm text-slate-600">
            {activeTab === "projects" && "Register projects using SIWE wallet authentication"}
            {activeTab === "keys" && "Manage API keys for programmatic access"}
            {activeTab === "config" && "System configuration and policies"}
            {activeTab === "sdk" && "Generate client SDKs for integration"}
          </div>
        </div>

        {/* Projects Tab */}
        {activeTab === "projects" && (
          <div className="space-y-4">
            <ProjectsPanel />
            <ProjectConfigPanel />
          </div>
        )}

        {/* API Keys Tab */}
        {activeTab === "keys" && (
          <div className="space-y-4">
            <APIKeysPanel />
          </div>
        )}

        {/* Configuration Tab */}
        {activeTab === "config" && (
          <div className="card p-4">
            <div className="text-base font-semibold mb-3">Configuration Editor</div>
            <div className="flex gap-2 mb-3">
              <button
                className="inline-flex items-center rounded border px-3 py-2 text-sm hover:bg-slate-50"
                onClick={async () => {
                  try {
                    const c = await getConfig();
                    setCfg(c);
                    setCfgJson(JSON.stringify(c, null, 2));
                  } catch (e: any) {
                    setCfg(null);
                    setCfgJson(`// Load failed: ${String(e?.message || e)}`);
                  }
                }}
              >
                Load Config
              </button>
              <button
                className="inline-flex items-center rounded border px-3 py-2 text-sm hover:bg-slate-50"
                onClick={async () => {
                  try {
                    let toSave = cfg;
                    try {
                      const parsed = JSON.parse(cfgJson);
                      toSave = parsed;
                    } catch {
                      // ignore
                    }
                    const res = await putConfig(toSave);
                    setCfg(res);
                    setCfgJson(JSON.stringify(res, null, 2));
                  } catch (e: any) {
                    alert(`Save failed: ${String(e?.message || e)}`);
                  }
                }}
              >
                Save Config
              </button>
            </div>

            <div className="grid md:grid-cols-2 gap-3">
              <div className="rounded border p-3 bg-white/60 space-y-2">
                <div className="text-xs text-slate-600 mb-1">Quick Editors</div>
                <div className="grid gap-2">
                  <div>
                    <div className="text-xs text-slate-600">Security.anchor_mode</div>
                    <select
                      className="w-full border rounded px-2 py-2"
                      value={cfg?.security?.anchor_mode ?? "managed"}
                      onChange={(e) => setCfg((prev: any) => ({ ...prev, security: { ...(prev?.security || {}), anchor_mode: e.target.value } }))}
                    >
                      <option value="managed">managed</option>
                      <option value="self">self</option>
                    </select>
                  </div>
                  <div>
                    <div className="text-xs text-slate-600">Evidence.store.mode</div>
                    <select
                      className="w-full border rounded px-2 py-2"
                      value={cfg?.evidence?.store?.mode ?? "local"}
                      onChange={(e) =>
                        setCfg((prev: any) => ({
                          ...prev,
                          evidence: { ...(prev?.evidence || {}), store: { ...(prev?.evidence?.store || {}), mode: e.target.value } },
                        }))
                      }
                    >
                      <option value="local">local</option>
                      <option value="ipfs">ipfs</option>
                      <option value="arweave">arweave</option>
                    </select>
                  </div>
                </div>
              </div>

              <div className="rounded border p-3 bg-white/60">
                <div className="text-xs text-slate-600 mb-1">Raw Config JSON</div>
                <textarea
                  className="w-full h-64 border rounded px-3 py-2 font-mono text-xs"
                  value={cfgJson}
                  onChange={(e) => setCfgJson(e.target.value)}
                  placeholder="// Load config to edit"
                />
              </div>
            </div>
          </div>
        )}

        {/* SDK Builder Tab */}
        {activeTab === "sdk" && (
          <div className="card p-4">
            <div className="text-base font-semibold mb-3">SDK Builder + OpenAPI</div>
            <div className="grid md:grid-cols-3 gap-2">
              <div>
                <div className="text-xs text-slate-600 mb-1">Language</div>
                <div className="flex gap-2">
                  <label className="text-sm flex items-center gap-1">
                    <input type="radio" name="sdk_lang" checked={sdkLang === "ts"} onChange={() => setSdkLang("ts")} />
                    TS
                  </label>
                  <label className="text-sm flex items-center gap-1">
                    <input type="radio" name="sdk_lang" checked={sdkLang === "python"} onChange={() => setSdkLang("python")} />
                    Python
                  </label>
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-600 mb-1">Packaging</div>
                <select className="w-full border rounded px-2 py-2" value={sdkPackaging} onChange={(e) => setSdkPackaging(e.target.value as any)}>
                  <option value="none">none</option>
                  <option value="npm">npm</option>
                  <option value="pypi">pypi</option>
                </select>
              </div>
              <div>
                <div className="text-xs text-slate-600 mb-1">Base URL override</div>
                <input className="w-full border rounded px-3 py-2" value={sdkBase} onChange={(e) => setSdkBase(e.target.value)} placeholder={apiBase} />
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                className="inline-flex items-center rounded border px-3 py-2 text-sm hover:bg-slate-50"
                onClick={async () => {
                  try {
                    const { blob, filename } = await buildSdk({
                      lang: sdkLang,
                      base_url: sdkBase || undefined,
                      packaging: sdkPackaging,
                    });
                    downloadBlob(blob, filename);
                    setSdkMessage("SDK built successfully.");
                  } catch (e: any) {
                    setSdkMessage(`Build failed: ${String(e?.message || e)}`);
                  }
                }}
              >
                Build SDK
              </button>
              <button
                className="inline-flex items-center rounded border px-3 py-2 text-sm hover:bg-slate-50"
                onClick={async () => {
                  try {
                    const blob = await downloadOpenApi();
                    downloadBlob(blob, "openapi.json");
                  } catch (e: any) {
                    setSdkMessage(`OpenAPI download failed: ${String(e?.message || e)}`);
                  }
                }}
              >
                Download OpenAPI JSON
              </button>
              <a className="inline-flex items-center rounded border px-3 py-2 text-sm hover:bg-slate-50" href={`${apiBase}/docs`} target="_blank" rel="noreferrer">
                Open Swagger UI
              </a>
            </div>
            {sdkMessage && <div className="mt-2 text-xs text-slate-600">{sdkMessage}</div>}
          </div>
        )}
      </section>

      {/* Right sidebar - AI Assistant */}
      <aside className="col-span-12 lg:col-span-3">
        <AssistantPanel />
      </aside>
    </div>
  );
}
