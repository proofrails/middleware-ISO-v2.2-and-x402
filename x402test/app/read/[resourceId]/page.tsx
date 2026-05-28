import { verifyResourceToken } from '@/lib/token';
import { readResource } from '@/lib/resources';
import Link from 'next/link';

interface Props {
  params: { resourceId: string };
  searchParams: { token?: string };
}

export default function ReadPage({ params, searchParams }: Props) {
  const { token } = searchParams;

  if (!token) {
    return <AccessDenied reason="No access token provided." />;
  }

  const paymentId = verifyResourceToken(token);
  if (!paymentId) {
    return <AccessDenied reason="Access token is invalid or has expired. Download links are valid for 24 hours." />;
  }

  const filename = `${params.resourceId}.md`;
  const raw = readResource(filename);

  if (!raw) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center space-y-4">
        <h1 className="text-xl font-bold text-slate-100">Resource not yet available</h1>
        <p className="text-slate-400 text-sm">
          The Markdown file has not been added to the server yet.
          Please download the PDF instead.
        </p>
        <Link href="/unlock" className="btn-secondary inline-block">Back to unlock</Link>
      </div>
    );
  }

  const content = raw.toString('utf-8');

  return (
    <div className="max-w-3xl mx-auto px-4 py-10">
      <div className="flex items-center justify-between mb-8 gap-4">
        <p className="text-xs text-green-400 flex items-center gap-2">
          <span className="status-dot bg-green-400" />
          Unlocked via Coston2 x402 payment
        </p>
        <a
          href={`/api/resource/${params.resourceId}.pdf?token=${token}`}
          className="btn-secondary text-sm py-2 px-4"
        >
          Download PDF
        </a>
      </div>

      <article className="prose prose-invert prose-sm max-w-none space-y-4">
        <pre className="whitespace-pre-wrap text-sm text-slate-300 leading-relaxed font-sans bg-transparent p-0 border-0">
          {content}
        </pre>
      </article>

      <div className="mt-12 pt-6 border-t border-navy-700 flex gap-3">
        <a
          href={`/api/resource/${params.resourceId}.pdf?token=${token}`}
          className="btn-primary text-sm"
        >
          Download PDF
        </a>
        <a href="https://app.proofrails.com/verify" target="_blank" rel="noopener noreferrer"
          className="btn-ghost text-sm">
          Verify receipt ↗
        </a>
      </div>
    </div>
  );
}

function AccessDenied({ reason }: { reason: string }) {
  return (
    <div className="max-w-2xl mx-auto px-4 py-16 text-center space-y-4">
      <div className="text-4xl">🔒</div>
      <h1 className="text-2xl font-bold text-slate-100">Access denied</h1>
      <p className="text-slate-400">{reason}</p>
      <Link href="/unlock" className="btn-primary inline-block">
        Complete payment to unlock
      </Link>
    </div>
  );
}
