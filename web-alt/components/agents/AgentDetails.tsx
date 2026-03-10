import { Bot, Copy, Check, Edit2, Send, QrCode, Download, Rocket, ExternalLink, HelpCircle } from "lucide-react";

interface Agent {
  id: string;
  name: string;
  wallet_address: string;
  xmtp_address?: string;
  status: string;
  created_at: string;
}

interface AgentDetailsProps {
  agent: Agent;
  copiedAddress: string;
  onCopy: (text: string, label: string) => void;
  onEdit: () => void;
  onTest: () => void;
  onShowQR: () => void;
  onClone: () => void;
  onDelete: () => void;
  onDownload: () => void;
  API_BASE: string;
}

export default function AgentDetails({
  agent,
  copiedAddress,
  onCopy,
  onEdit,
  onTest,
  onShowQR,
  onClone,
  onDelete,
  onDownload,
}: AgentDetailsProps) {
  return (
    <div className="space-y-6">
      {/* Instructions */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start gap-2">
          <HelpCircle className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-900">
            <div className="font-semibold mb-1">How to Deploy Your Agent</div>
            <ol className="space-y-1 ml-4 list-decimal">
              <li>Click &quot;Download Agent&quot; to get your personalized agent package</li>
              <li>Extract the ZIP and edit .env with your wallet private key</li>
              <li>Run: <code className="bg-blue-100 px-1 rounded">npm install && npm start</code></li>
              <li>Your agent will listen for XMTP messages and handle payments automatically</li>
            </ol>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-3 gap-3">
        <button
          onClick={onTest}
          className="p-4 bg-white border border-slate-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors text-left"
        >
          <Send className="h-5 w-5 text-blue-600 mb-2" />
          <div className="font-semibold text-sm">Test Agent</div>
          <div className="text-xs text-slate-600">Send test message</div>
        </button>
        
        <button
          onClick={onShowQR}
          className="p-4 bg-white border border-slate-200 rounded-lg hover:border-purple-500 hover:bg-purple-50 transition-colors text-left"
        >
          <QrCode className="h-5 w-5 text-purple-600 mb-2" />
          <div className="font-semibold text-sm">QR Code</div>
          <div className="text-xs text-slate-600">Share agent info</div>
        </button>
        
        <button
          onClick={onClone}
          className="p-4 bg-white border border-slate-200 rounded-lg hover:border-green-500 hover:bg-green-50 transition-colors text-left"
        >
          <Copy className="h-5 w-5 text-green-600 mb-2" />
          <div className="font-semibold text-sm">Clone Agent</div>
          <div className="text-xs text-slate-600">Duplicate config</div>
        </button>
      </div>

      <div className="bg-white border border-slate-200 rounded-lg p-6">
        <div className="flex justify-between items-start mb-4">
          <h3 className="text-lg font-bold">Agent Information</h3>
          <button
            onClick={onEdit}
            className="p-2 hover:bg-slate-100 rounded"
            title="Edit agent"
          >
            <Edit2 className="h-4 w-4" />
          </button>
        </div>
        <div className="space-y-3">
          <div>
            <div className="text-sm text-slate-600">Name</div>
            <div className="font-semibold">{agent.name}</div>
          </div>
          <div>
            <div className="text-sm text-slate-600 mb-1">Wallet Address</div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm">{agent.wallet_address}</span>
              <button
                onClick={() => onCopy(agent.wallet_address, "wallet")}
                className="p-1 hover:bg-slate-100 rounded"
              >
                {copiedAddress === "wallet" ? (
                  <Check className="h-4 w-4 text-green-600" />
                ) : (
                  <Copy className="h-4 w-4 text-slate-400" />
                )}
              </button>
            </div>
            <div className="text-xs text-slate-500 mt-1">This wallet will make x402 micropayments</div>
          </div>
          {agent.xmtp_address && (
            <div>
              <div className="text-sm text-slate-600 mb-1">XMTP Address</div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm">{agent.xmtp_address}</span>
                <button
                  onClick={() => onCopy(agent.xmtp_address!, "xmtp")}
                  className="p-1 hover:bg-slate-100 rounded"
                >
                  {copiedAddress === "xmtp" ? (
                    <Check className="h-4 w-4 text-green-600" />
                  ) : (
                    <Copy className="h-4 w-4 text-slate-400" />
                  )}
                </button>
              </div>
            </div>
          )}
          <div>
            <div className="text-sm text-slate-600">Status</div>
            <div className="flex items-center gap-2 mt-1">
              <span className={`w-2 h-2 rounded-full ${agent.status === "active" ? "bg-green-500 animate-pulse" : "bg-slate-400"}`}></span>
              <span className="font-semibold">{agent.status === "active" ? "Online" : "Offline"}</span>
            </div>
          </div>
          <div>
            <div className="text-sm text-slate-600">Created</div>
            <div>{new Date(agent.created_at).toLocaleString()}</div>
          </div>
        </div>
        
        {/* Deploy Buttons */}
        <div className="mt-6 space-y-3">
          <div className="text-sm font-semibold text-slate-700">Quick Deploy</div>
          <div className="grid grid-cols-2 gap-2">
            <a
              href="https://railway.app/new"
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 flex items-center justify-center gap-2 text-sm"
            >
              <Rocket className="h-4 w-4" />
              Deploy to Railway
              <ExternalLink className="h-3 w-3" />
            </a>
            <a
              href="https://heroku.com/deploy"
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 flex items-center justify-center gap-2 text-sm"
            >
              <Rocket className="h-4 w-4" />
              Deploy to Heroku
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </div>

        <div className="mt-6 flex gap-2">
          <button
            onClick={onDownload}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 flex items-center gap-2"
            title="Download complete agent package"
          >
            <Download className="h-4 w-4" />
            Download Agent
          </button>
          <button
            onClick={onDelete}
            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
            title="Delete this agent"
          >
            Delete Agent
          </button>
        </div>
      </div>
    </div>
  );
}
