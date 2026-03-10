import { HelpCircle, TrendingUp, Download } from "lucide-react";

interface RevenueData {
  total_revenue: string;
  payment_count: number;
  days: number;
  by_endpoint: Array<{
    endpoint: string;
    count: number;
    revenue: string;
  }>;
}

interface AgentRevenueProps {
  revenue: RevenueData | null;
  days: number;
  onDaysChange: (days: number) => void;
}

export default function AgentRevenue({ revenue, days, onDaysChange }: AgentRevenueProps) {
  return (
    <div className="space-y-4">
      <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
        <div className="flex items-start gap-2">
          <HelpCircle className="h-5 w-5 text-purple-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-purple-900">
            <div className="font-semibold mb-1">Revenue Analytics</div>
            <div>Track micropayments received from agents accessing your premium endpoints. Revenue is in USDC on Base chain.</div>
          </div>
        </div>
      </div>

      {/* Date Range Selector */}
      <div className="flex items-center gap-2">
        <label className="text-sm font-medium">Time Period:</label>
        <select
          value={days}
          onChange={(e) => onDaysChange(Number(e.target.value))}
          className="px-3 py-2 border border-slate-300 rounded text-sm"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {revenue ? (
        <>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-white border border-slate-200 rounded-lg p-6">
              <div className="text-sm text-slate-600 mb-1">Total Revenue ({days} days)</div>
              <div className="text-2xl font-bold flex items-center gap-2">
                <TrendingUp className="h-6 w-6 text-green-600" />
                {revenue.total_revenue} USDC
              </div>
            </div>
            <div className="bg-white border border-slate-200 rounded-lg p-6">
              <div className="text-sm text-slate-600 mb-1">Payments</div>
              <div className="text-2xl font-bold">{revenue.payment_count}</div>
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-lg p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold">Revenue by Endpoint</h3>
              <button
                onClick={() => {
                  // Export to CSV logic
                  const csv = `Endpoint,Payments,Revenue\n${revenue.by_endpoint.map(e => `${e.endpoint},${e.count},${e.revenue}`).join('\n')}`;
                  const blob = new Blob([csv], { type: 'text/csv' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `revenue-${days}days.csv`;
                  a.click();
                }}
                className="px-3 py-1 bg-slate-100 hover:bg-slate-200 rounded text-sm flex items-center gap-2"
              >
                <Download className="h-4 w-4" />
                Export CSV
              </button>
            </div>
            {revenue.by_endpoint.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                No revenue data yet. Revenue will appear as agents make x402 payments.
              </div>
            ) : (
              <div className="space-y-2">
                {revenue.by_endpoint.map((item, idx) => (
                  <div key={idx} className="flex justify-between items-center py-2 border-b border-slate-100">
                    <div className="font-mono text-sm">{item.endpoint}</div>
                    <div className="flex gap-4">
                      <span className="text-slate-600">{item.count} payments</span>
                      <span className="font-semibold">{item.revenue} USDC</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      ) : (
        <div className="text-center py-12 text-slate-500">
          No revenue data available. Check back after agents start making payments.
        </div>
      )}
    </div>
  );
}
