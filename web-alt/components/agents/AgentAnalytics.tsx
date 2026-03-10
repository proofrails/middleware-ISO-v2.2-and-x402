import { BarChart3, TrendingUp, Zap, DollarSign } from "lucide-react";

interface AgentAnalyticsProps {
  stats: {
    messagesProcessed: number;
    averageResponseTime: number;
    successRate: number;
    totalCost: number;
    topCommands: Array<{ command: string; count: number }>;
  };
}

export default function AgentAnalytics({ stats }: AgentAnalyticsProps) {
  return (
    <div className="space-y-4">
      {/* Stats Grid */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-lg p-6">
          <div className="flex items-center gap-2 mb-2">
            <BarChart3 className="h-5 w-5 text-blue-600" />
            <div className="text-sm text-slate-600">Messages Processed</div>
          </div>
          <div className="text-2xl font-bold">{stats.messagesProcessed.toLocaleString()}</div>
        </div>
        
        <div className="bg-white border border-slate-200 rounded-lg p-6">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="h-5 w-5 text-yellow-600" />
            <div className="text-sm text-slate-600">Avg Response Time</div>
          </div>
          <div className="text-2xl font-bold">{stats.averageResponseTime}ms</div>
        </div>
        
        <div className="bg-white border border-slate-200 rounded-lg p-6">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="h-5 w-5 text-green-600" />
            <div className="text-sm text-slate-600">Success Rate</div>
          </div>
          <div className="text-2xl font-bold">{stats.successRate}%</div>
        </div>
        
        <div className="bg-white border border-slate-200 rounded-lg p-6">
          <div className="flex items-center gap-2 mb-2">
            <DollarSign className="h-5 w-5 text-purple-600" />
            <div className="text-sm text-slate-600">Total Cost</div>
          </div>
          <div className="text-2xl font-bold">${stats.totalCost.toFixed(2)}</div>
        </div>
      </div>

      {/* Top Commands */}
      <div className="bg-white border border-slate-200 rounded-lg p-6">
        <h3 className="text-lg font-bold mb-4">Top Commands</h3>
        <div className="space-y-3">
          {stats.topCommands.length === 0 ? (
            <div className="text-center py-8 text-slate-500">
              No command data yet. Commands will be tracked as your agent processes messages.
            </div>
          ) : (
            stats.topCommands.map((cmd, idx) => (
              <div key={idx} className="flex justify-between items-center">
                <div className="flex items-center gap-3">
                  <div className="text-2xl font-bold text-slate-300">#{idx + 1}</div>
                  <div className="font-mono text-sm">{cmd.command}</div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-sm text-slate-600">{cmd.count} uses</div>
                  <div className="w-32 bg-slate-200 rounded-full h-2">
                    <div 
                      className="bg-blue-600 h-2 rounded-full"
                      style={{ 
                        width: `${(cmd.count / Math.max(...stats.topCommands.map(c => c.count))) * 100}%` 
                      }}
                    ></div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Performance Info */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="text-sm text-blue-900">
          <div className="font-semibold mb-1">💡 Analytics Info</div>
          <div>Analytics are updated in real-time as your agent processes messages. Costs include x402 micropayments and AI API usage (if applicable).</div>
        </div>
      </div>
    </div>
  );
}
