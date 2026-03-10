import { Bot, Plus, X, Zap } from "lucide-react";

interface Agent {
  id: string;
  name: string;
  wallet_address: string;
  xmtp_address?: string;
  status: string;
  created_at: string;
}

interface AgentsListProps {
  agents: Agent[];
  selectedAgent: Agent | null;
  onSelectAgent: (agent: Agent) => void;
  loading: boolean;
  showGuide: boolean;
  onHideGuide: () => void;
  showNewAgentForm: boolean;
  onToggleNewAgentForm: () => void;
  onToggleTemplateModal: () => void;
  onCreateAgent: (formData: { name: string; wallet_address: string; xmtp_address?: string }) => void;
  selectedTemplate: any;
}

export default function AgentsList({
  agents,
  selectedAgent,
  onSelectAgent,
  loading,
  showGuide,
  onHideGuide,
  showNewAgentForm,
  onToggleNewAgentForm,
  onToggleTemplateModal,
  onCreateAgent,
  selectedTemplate,
}: AgentsListProps) {
  return (
    <div className="w-80 border-r border-slate-200 bg-slate-50 overflow-y-auto">
      <div className="p-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-slate-900">AI Agents</h2>
          <div className="flex gap-2">
            <button
              onClick={onToggleTemplateModal}
              className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              title="Create from template"
            >
              <Zap className="h-4 w-4" />
            </button>
            <button
              onClick={onToggleNewAgentForm}
              className="p-2 bg-slate-900 text-white rounded-lg hover:bg-slate-700"
              title="Create new agent"
            >
              <Plus className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Quick Guide */}
        {showGuide && (
          <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm">
            <div className="flex justify-between items-start mb-2">
              <div className="font-semibold text-blue-900">Quick Guide</div>
              <button onClick={onHideGuide} className="text-blue-600">
                <X className="h-3 w-3" />
              </button>
            </div>
            <div className="text-blue-800 space-y-1">
              <div>1️⃣ Create agent (+ button)</div>
              <div>2️⃣ Configure AI (optional)</div>
              <div>3️⃣ Download agent package</div>
              <div>4️⃣ Run: npm install && npm start</div>
            </div>
          </div>
        )}

        {/* New Agent Form */}
        {showNewAgentForm && (
          <div className="mb-4 p-3 bg-white border border-slate-200 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold">New Agent</h3>
              {selectedTemplate && (
                <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs font-medium flex items-center gap-1">
                  <Zap className="h-3 w-3" />
                  {selectedTemplate.name}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-600 mb-3">
              {selectedTemplate 
                ? `Creating from template: ${selectedTemplate.description}` 
                : "Register a new XMTP agent that will handle commands and payments automatically."
              }
            </p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const formData = new FormData(e.currentTarget);
                onCreateAgent({
                  name: formData.get("name") as string,
                  wallet_address: formData.get("wallet") as string,
                  xmtp_address: formData.get("xmtp") as string || undefined,
                });
              }}
            >
              <input
                name="name"
                placeholder="Agent Name (e.g., My ISO Agent)"
                className="w-full px-3 py-2 border border-slate-300 rounded mb-2 text-sm"
                required
              />
              <input
                name="wallet"
                placeholder="Wallet Address (0x...)"
                className="w-full px-3 py-2 border border-slate-300 rounded mb-2 text-sm"
                required
              />
              <input
                name="xmtp"
                placeholder="XMTP Address (optional)"
                className="w-full px-3 py-2 border border-slate-300 rounded mb-2 text-sm"
              />
              <div className="flex gap-2">
                <button
                  type="submit"
                  className="flex-1 px-3 py-2 bg-slate-900 text-white rounded hover:bg-slate-700 text-sm"
                >
                  Create
                </button>
                <button
                  type="button"
                  onClick={onToggleNewAgentForm}
                  className="px-3 py-2 bg-slate-200 rounded hover:bg-slate-300 text-sm"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Agent List */}
        {loading ? (
          <div className="text-center py-8 text-slate-500">Loading...</div>
        ) : agents.length === 0 ? (
          <div className="text-center py-8 text-slate-500">
            No agents yet. Create one to get started.
          </div>
        ) : (
          <div className="space-y-2">
            {agents.map((agent) => (
              <div
                key={agent.id}
                onClick={() => onSelectAgent(agent)}
                className={`p-3 rounded-lg cursor-pointer transition-colors ${
                  selectedAgent?.id === agent.id
                    ? "bg-slate-900 text-white"
                    : "bg-white hover:bg-slate-100"
                }`}
              >
                <div className="flex items-start gap-2">
                  <Bot className="h-5 w-5 mt-0.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold truncate">{agent.name}</div>
                    <div className="text-xs opacity-70 truncate">
                      {agent.wallet_address.slice(0, 8)}...{agent.wallet_address.slice(-6)}
                    </div>
                    <div className="text-xs opacity-60 mt-1 flex items-center gap-1">
                      {agent.status === "active" ? (
                        <>
                          <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                          Online
                        </>
                      ) : (
                        <>
                          <span className="w-2 h-2 bg-slate-400 rounded-full"></span>
                          Offline
                        </>
                      )}
                    </div>
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
