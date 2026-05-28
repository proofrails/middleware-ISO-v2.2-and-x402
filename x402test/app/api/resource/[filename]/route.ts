import { NextRequest, NextResponse } from 'next/server';
import { verifyResourceToken } from '@/lib/token';
import { readResource, contentType, resourceExists } from '@/lib/resources';
import { trackEvent } from '@/lib/analytics';

export async function GET(
  req: NextRequest,
  { params }: { params: { filename: string } },
) {
  const { filename } = params;
  const token = req.nextUrl.searchParams.get('token');

  if (!token) {
    return NextResponse.json({ error: 'No access token' }, { status: 401 });
  }

  const paymentId = verifyResourceToken(token);
  if (!paymentId) {
    return NextResponse.json({ error: 'Invalid or expired access token' }, { status: 401 });
  }

  if (!resourceExists(filename)) {
    return NextResponse.json(
      { error: 'Resource not yet available. Place the file in resources/private/' },
      { status: 404 },
    );
  }

  const data = readResource(filename);
  if (!data) {
    return NextResponse.json({ error: 'Resource read error' }, { status: 500 });
  }

  const ext = filename.endsWith('.pdf') ? 'pdf' : 'md';
  trackEvent(ext === 'pdf' ? 'resource_download_pdf' : 'resource_download_md');

  const disposition = ext === 'pdf'
    ? `attachment; filename="${filename}"`
    : `attachment; filename="${filename}"`;

  return new NextResponse(new Uint8Array(data), {
    headers: {
      'Content-Type': contentType(filename),
      'Content-Disposition': disposition,
      'Content-Length': data.length.toString(),
      'Cache-Control': 'private, no-store',
    },
  });
}
