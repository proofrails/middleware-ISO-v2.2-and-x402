"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Code2, FileCheck2, PlusCircle, Receipt, Settings, ShieldCheck } from "lucide-react";

export default function TopNavigation() {
  const pathname = usePathname();
  const tabs = [
    { path: "/create", label: "Create receipt", icon: PlusCircle },
    { path: "/receipts", label: "Receipts", icon: Receipt },
    { path: "/verify", label: "Verify", icon: ShieldCheck },
    { path: "/developers", label: "Developers", icon: Code2 },
    { path: "/settings", label: "Settings", icon: Settings },
  ];
  const isActive = (path: string) => pathname === path || pathname.startsWith(`${path}/`);
  return (
    <nav className="sticky top-0 z-40 border-b border-slate-200 bg-white/85 backdrop-blur-xl">
      <div className="mx-auto max-w-7xl px-4 py-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Link href="/" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-950 text-white"><FileCheck2 className="h-5 w-5" /></div>
            <div><div className="text-lg font-black tracking-tight">ProofRails</div><div className="hidden text-xs text-slate-500 sm:block">Verifiable receipts for onchain payments</div></div>
          </Link>
          <div className="flex max-w-full gap-1 overflow-x-auto">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const active = isActive(tab.path);
              return (
                <Link key={tab.path} href={tab.path as any} className={`inline-flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-sm font-bold transition ${active ? "bg-slate-950 text-white" : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"}`}>
                  <Icon className="h-4 w-4" />
                  <span>{tab.label}</span>
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </nav>
  );
}
