import { MessageCircle, DollarSign, AlertCircle, Clock, RefreshCw } from "lucide-react";

interface ActivityLog {
  id: string;
  type: "message" | "payment" | "error";
  content: string;
  timestamp: Date;
}

interface AgentActivityProps {
  logs: ActivityLog[];
  onRefresh: () => void;
}

export default function AgentActivity({ logs, onRefresh }: AgentActivityProps) {
  return (
    <div className="space-y-4">
      <div className="bg-white border border-slate-200 rounded-lg p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-bold">Activity Log</h3>
          <button 
            onClick={onRefresh}
            className="p-2 hover:bg-slate-100 rounded" 
            title="Refresh"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
        
        {logs.length === 0 ? (
          <div className="text-center py-8 text-slate-500">
            No activity yet. Your agent will log messages, payments, and errors here.
          </div>
        ) : (
          <div className="space-y-3">
            {logs.map((log) => (
              <div key={log.id} className="flex gap-3 p-3 bg-slate-50 rounded">
                <div className="flex-shrink-0">
                  {log.type === "message" && <MessageCircle className="h-5 w-5 text-blue-600" />}
                  {log.type === "payment" && <DollarSign className="h-5 w-5 text-green-600" />}
                  {log.type === "error" && <AlertCircle className="h-5 w-5 text-red-600" />}
                </div>
                <div className="flex-1">
                  <div className="text-sm">{log.content}</div>
                  <div className="text-xs text-slate-500 mt-1 flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {log.timestamp.toLocaleString()}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
