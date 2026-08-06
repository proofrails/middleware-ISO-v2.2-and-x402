"use client";
import { useEffect, useState } from "react";
import EvidenceBundleCard from "../../../components/receipt/EvidenceBundleCard";
import IsoArtifactsList from "../../../components/receipt/IsoArtifactsList";
import ReceiptSummaryCard from "../../../components/receipt/ReceiptSummaryCard";
import VerificationResultCard from "../../../components/receipt/VerificationResultCard";
import { getReceipt, listIsoArtifacts, verifyEvidence, type ISOArtifact, type Receipt, type VerificationResult } from "../../../lib/proofrails";

export default function PublicVerifyPage({ params }: { params: { id: string } }) {
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [artifacts, setArtifacts] = useState<ISOArtifact[]>([]);
  const [result, setResult] = useState<VerificationResult | null>(null);
  useEffect(() => {
    getReceipt(params.id).then((r) => {
      setReceipt(r.receipt);
      if (r.receipt) verifyEvidence({ receipt_id: r.receipt.id, bundle_hash: r.receipt.bundle_hash, bundle_url: r.receipt.bundle_url }).then(setResult);
    });
    listIsoArtifacts(params.id).then((r) => setArtifacts(r.items));
  }, [params.id]);
  if (!receipt) return <div className="rounded-3xl border border-slate-200 bg-white p-8">Receipt not found.</div>;
  return <div className="space-y-6"><div className="rounded-3xl border border-slate-200 bg-white p-6"><div className="text-sm font-bold uppercase tracking-wide text-slate-500">Public verification page</div><p className="mt-2 text-slate-600">This page explains what ProofRails verified and what remains outside the claim.</p></div>{result && <VerificationResultCard result={result} />}<ReceiptSummaryCard receipt={receipt}/><div className="grid gap-6 lg:grid-cols-2"><EvidenceBundleCard receipt={receipt}/><IsoArtifactsList artifacts={artifacts}/></div></div>;
}
