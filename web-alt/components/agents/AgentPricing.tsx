import { HelpCircle, DollarSign } from "lucide-react";

interface PricingEndpoint {
  path: string;
  price: string;
  currency: string;
  recipient: string;
}

interface AgentPricingProps {
  pricing: PricingEndpoint[];
}

export default function AgentPricing({ pricing }: AgentPricingProps) {
  return (
    <div className="space-y-4">
      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
        <div className="flex items-start gap-2">
          <HelpCircle className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-green-900">
            <div className="font-semibold mb-1">About Endpoint Pricing</div>
            <div>These are the micropayment amounts agents will pay to access premium features. Agents automatically handle these payments via x402 protocol using USDC on Base chain.</div>
          </div>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-lg p-6">
        <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
          <DollarSign className="h-5 w-5" />
          Endpoint Pricing
        </h3>
        {pricing.length === 0 ? (
          <div className="text-center py-8 text-slate-500">
            No pricing configured yet. Configure endpoint pricing to enable x402 micropayments.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-2 px-3">Endpoint</th>
                  <th className="text-left py-2 px-3">Price</th>
                  <th className="text-left py-2 px-3">Currency</th>
                  <th className="text-left py-2 px-3">Recipient</th>
                </tr>
              </thead>
              <tbody>
                {pricing.map((item, idx) => (
                  <tr key={idx} className="border-b border-slate-100">
                    <td className="py-2 px-3 font-mono text-sm">{item.path}</td>
                    <td className="py-2 px-3">{item.price}</td>
                    <td className="py-2 px-3">{item.currency}</td>
                    <td className="py-2 px-3 font-mono text-xs">
                      {item.recipient.slice(0, 8)}...{item.recipient.slice(-6)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
