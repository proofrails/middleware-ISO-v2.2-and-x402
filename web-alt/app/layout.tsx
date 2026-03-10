import type { Metadata } from "next";
import "./globals.css";

export const dynamic = "force-dynamic";
export const revalidate = false;

export const metadata: Metadata = {
  title: "ISO Middleware — Alternative UI",
  description: "Next.js UI with persistent side AI assistant for ISO 20022 Middleware",
};

import TopNavigation from "../components/TopNavigation";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-screen bg-gradient-to-b from-slate-50 to-white text-slate-900 antialiased">
        <TopNavigation />
        <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
