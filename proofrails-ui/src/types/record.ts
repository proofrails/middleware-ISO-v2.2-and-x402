export type RecordStatus =
  | 'Pending'
  | 'Processing'
  | 'Complete'
  | 'Failed'
  | 'Anchored'
  | 'Verified';

export type AnchorStatus = 'Pending' | 'Processing' | 'Anchored' | 'Failed';

export type VerificationStatus = 'Unverified' | 'Verified' | 'Failed';

export type SourceType = 'XRPL payment' | 'FXRP payment' | 'Programmable payment event';

export interface TimelineEvent {
  id: string;
  label: string;
  detail: string;
  at: string;
  state: 'done' | 'current' | 'pending' | 'error';
}

export interface ArtifactItem {
  id: string;
  name: string;
  description: string;
  format: string;
  updatedAt: string;
}

export interface ProofRecord {
  id: string;
  asset: 'XRP' | 'FXRP';
  amount: string;
  sourceType: SourceType;
  sourceTxHash: string;
  reference: string;
  status: RecordStatus;
  anchorStatus: AnchorStatus;
  verificationStatus: VerificationStatus;
  createdAt: string;
  sender: string;
  receiver: string;
  counterparty: string;
  purpose: string;
  invoiceOrderId: string;
  category: string;
  notes: string;
  evidenceBundleHash: string;
  bundleStatus: string;
  flareTxHash: string;
  anchoredAt: string;
  lastVerifiedAt: string;
  verificationDetails: string;
  sourceEnvironment: string;
  paymentStatus: string;
  tags: string[];
  timeline: TimelineEvent[];
  artifacts: ArtifactItem[];
}
