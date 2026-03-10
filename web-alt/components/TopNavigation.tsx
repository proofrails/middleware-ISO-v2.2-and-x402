"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bot, Receipt, Settings, Workflow } from "lucide-react";

export default function TopNavigation() {
  const pathname = usePathname();

  const isActive = (path: string) => {
    if (path === "/") return pathname === "/";
    return pathname.startsWith(path);
  };

  const tabs = [
    { path: "/", label: "Receipts & Data", icon: Receipt },
    { path: "/operations", label: "Operations", icon: Workflow },
    { path: "/settings", label: "Settings", icon: Settings },
    { path: "/agents", label: "AI Agents", icon: Bot },
  ];

  return (
    <nav className="bg-white border-b border-slate-200 sticky top-0 z-40">
      <div className="px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div className="text-lg font-bold text-slate-900">ISO Middleware</div>
            <div className="hidden md:flex gap-2">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                const active = isActive(tab.path);
                return (
                  <Link
                    key={tab.path}
                    href={tab.path as any}
                    className={`
                      inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors
                      ${
                        active
                          ? "bg-slate-900 text-white"
                          : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                      }
                    `}
                  >
                    <Icon className="h-4 w-4" />
                    {tab.label}
                  </Link>
                );
              })}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <a
              href={`${process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000"}/docs`}
              target="_blank"
              rel="noreferrer"
              className="text-xs text-slate-600 hover:text-slate-900 underline"
            >
              API Docs
            </a>
          </div>
        </div>
        
        {/* Mobile navigation */}
        <div className="md:hidden flex gap-1 mt-3">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const active = isActive(tab.path);
            return (
              <Link
                key={tab.path}
                href={tab.path as any}
                className={`
                  flex-1 flex flex-col items-center gap-1 px-2 py-2 rounded-lg text-xs font-medium transition-colors
                  ${active ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"}
                `}
              >
                <Icon className="h-4 w-4" />
                <span className="truncate">{tab.label.split(" ")[0]}</span>
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
