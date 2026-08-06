import type { Metadata } from "next";
import "./globals.css";
import TopNavigation from "../components/TopNavigation";

export const dynamic = "force-dynamic";
export const revalidate = false;

export const metadata: Metadata = {
  title: "ProofRails",
  description: "Verifiable receipts for onchain payments",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-screen bg-[radial-gradient(circle_at_top_left,#ffe7fb,transparent_32rem),linear-gradient(to_bottom,#f8fafc,#ffffff)] text-slate-950 antialiased">
        <TopNavigation />
        <main className="mx-auto max-w-7xl px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
