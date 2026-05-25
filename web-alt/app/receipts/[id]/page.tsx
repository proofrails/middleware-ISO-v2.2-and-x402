"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import EvidenceBundleCard from "../../../components/receipt/EvidenceBundleCard";
import IsoArtifactsList from "../../../components/receipt/IsoArtifactsList";
import ReceiptSummaryCard from "../../../components/receipt/ReceiptSummaryCard";
import ReceiptTimeline from "../../../components/receipt/ReceiptTimeline";
import ShareReceiptPanel from "../../../components/receipt/ShareReceiptPanel";
import VerificationResultCard from "../../../components/receipt/VerificationResultCard";
import { getReceipt, listIsoArtifacts, verifyEvidence, type ISOArtifact, type Receipt, type VerificationResult } from "../../../lib/proofrails";

export default function ReceiptDetailPage({ params }: { params: { id: string } }) {
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [artifacts, setArtifacts] = useState<ISOArtifact[]>([]);
  const [verification, setVerification] = useState<VerificationResult | null>(null);
  useEffect(() => {
    getReceipt(params.id).then((r) => {
      setReceipt(r.receipt);
      if (r.receipt) verifyEvidence({ receipt_id: r.receipt.id, bundle_hash: r.receipt.bundle_hash, bundle_url: r.receipt.bundle_url }).then(setVerification);
    });
    listIsoArtifacts(params.id).then((r) => setArtifacts(r.items));
  }, [params.id]);
  if (!receipt) return <div className="rounded-3xl border border-slate-200 bg-white p-8">Receipt not found. <Link href="/create" className="underline">Create a demo receipt</Link>.</div>;
  return (
    <div className="space-y-6">
      <ReceiptSummaryCard receipt={receipt} />
      <ReceiptTimeline status={receipt.status} />
      <div className="grid gap-6 lg:grid-cols-2">
        {verification && <VerificationResultCard result={verification} />}
        <ShareReceiptPanel receipt={receipt} />
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <EvidenceBundleCard receipt={receipt} />
        <IsoArtifactsList artifacts={artifacts} />
      </div>
    </div>
  );
}
