import { X, Send, QrCode, Zap } from "lucide-react";
import { useState } from "react";

interface Agent {
  id: string;
  name: string;
  wallet_address: string;
  xmtp_address?: string;
}

interface AgentModalsProps {
  selectedAgent: Agent | null;
  showEditModal: boolean;
  showTestModal: boolean;
  showQRModal: boolean;
  showTemplateModal: boolean;
  onCloseEdit: () => void;
  onCloseTest: () => void;
  onCloseQR: () => void;
  onCloseTemplate: () => void;
  onUpdateAgent: (formData: { name: string; wallet_address: string; xmtp_address?: string }) => void;
  onSendTest: (message: string) => Promise<string>;
  onSelectTemplate: (template: any) => void;
  testResponse: string;
}

const TEMPLATES = [
  { 
    id: "basic", 
    name: "Basic Receipt Agent", 
    description: "Simple agent for viewing receipts", 
    ai_mode: "simple",
    system_prompt: ""
  },
  { 
    id: "advanced", 
    name: "Advanced Payment Agent", 
    description: "Full-featured with AI", 
    ai_mode: "shared",
    system_prompt: "You are a professional payment assistant. Help users manage their ISO 20022 transactions efficiently."
  },
  { 
    id: "support", 
    name: "Customer Support Agent", 
    description: "Specialized for support", 
    ai_mode: "shared",
    system_prompt: "You are a friendly customer support agent. Help users understand their payments and resolve issues."
  },
];

export default function AgentModals({
  selectedAgent,
  showEditModal,
  showTestModal,
  showQRModal,
  showTemplateModal,
  onCloseEdit,
  onCloseTest,
  onCloseQR,
  onCloseTemplate,
  onUpdateAgent,
  onSendTest,
  onSelectTemplate,
  testResponse,
}: AgentModalsProps) {
  const [testMessage, setTestMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSendTest = async () => {
    setLoading(true);
    await onSendTest(testMessage);
    setLoading(false);
  };

  return (
    <>
      {/* Edit Modal */}
      {showEditModal && selectedAgent && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold">Edit Agent</h3>
              <button onClick={onCloseEdit} className="p-1 hover:bg-slate-100 rounded">
                <X className="h-4 w-4" />
              </button>
            </div>
            <form onSubmit={(e) => {
              e.preventDefault();
              const formData = new FormData(e.currentTarget);
              onUpdateAgent({
                name: formData.get("name") as string,
                wallet_address: formData.get("wallet") as string,
                xmtp_address: formData.get("xmtp") as string || undefined,
              });
            }}>
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium mb-1">Agent Name</label>
                  <input
                    name="name"
                    defaultValue={selectedAgent.name}
                    className="w-full px-3 py-2 border border-slate-300 rounded text-sm"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Wallet Address</label>
                  <input
                    name="wallet"
                    defaultValue={selectedAgent.wallet_address}
                    className="w-full px-3 py-2 border border-slate-300 rounded text-sm"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">XMTP Address (Optional)</label>
                  <input
                    name="xmtp"
                    defaultValue={selectedAgent.xmtp_address || ""}
                    className="w-full px-3 py-2 border border-slate-300 rounded text-sm"
                  />
                </div>
              </div>
              <div className="flex gap-2 mt-6">
                <button type="submit" className="flex-1 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                  Save Changes
                </button>
                <button type="button" onClick={onCloseEdit} className="px-4 py-2 bg-slate-200 rounded hover:bg-slate-300">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Test Modal */}
      {showTestModal && selectedAgent && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold">Test Agent</h3>
              <button onClick={onCloseTest} className="p-1 hover:bg-slate-100 rounded">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Test Message</label>
                <input
                  type="text"
                  value={testMessage}
                  onChange={(e) => setTestMessage(e.target.value)}
                  placeholder="e.g., show me my receipts"
                  className="w-full px-3 py-2 border border-slate-300 rounded text-sm"
                />
              </div>
              <button
                onClick={handleSendTest}
                disabled={loading || !testMessage.trim()}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                <Send className="h-4 w-4" />
                {loading ? "Processing..." : "Send Test"}
              </button>
              {testResponse && (
                <div className="p-3 bg-slate-50 rounded text-sm whitespace-pre-wrap">{testResponse}</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* QR Modal */}
      {showQRModal && selectedAgent && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md text-center">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold">QR Code</h3>
              <button onClick={onCloseQR} className="p-1 hover:bg-slate-100 rounded">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="mb-4">
              <img
                src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(
                  JSON.stringify({
                    name: selectedAgent.name,
                    wallet: selectedAgent.wallet_address,
                    xmtp: selectedAgent.xmtp_address,
                  })
                )}`}
                alt="Agent QR Code"
                className="mx-auto"
              />
            </div>
            <p className="text-sm text-slate-600">Scan to share agent information</p>
          </div>
        </div>
      )}

      {/* Template Modal */}
      {showTemplateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-2xl">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold">Choose Agent Template</h3>
              <button onClick={onCloseTemplate} className="p-1 hover:bg-slate-100 rounded">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="grid grid-cols-1 gap-3">
              {TEMPLATES.map((template) => (
                <button
                  key={template.id}
                  onClick={() => onSelectTemplate(template)}
                  className="p-4 border border-slate-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 text-left transition-colors"
                >
                  <div className="flex items-start gap-3">
                    <Zap className="h-5 w-5 text-blue-600 flex-shrink-0 mt-1" />
                    <div>
                      <div className="font-semibold">{template.name}</div>
                      <div className="text-sm text-slate-600">{template.description}</div>
                      <div className="text-xs text-slate-500 mt-1">Mode: {template.ai_mode}</div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
