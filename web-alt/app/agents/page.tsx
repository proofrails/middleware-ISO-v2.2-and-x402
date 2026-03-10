"use client";

import { useEffect, useState } from "react";
import { Bot, Brain, Activity, BarChart3, DollarSign, TrendingUp, Anchor } from "lucide-react";
import AgentsList from "@/components/agents/AgentsList";
import AgentDetails from "@/components/agents/AgentDetails";
import AgentModals from "@/components/agents/AgentModals";
import AgentActivity from "@/components/agents/AgentActivity";
import AgentAnalytics from "@/components/agents/AgentAnalytics";
import AgentAISettings from "@/components/agents/AgentAISettings";
import AgentPricing from "@/components/agents/AgentPricing";
import AgentRevenue from "@/components/agents/AgentRevenue";
import AgentChat from "@/components/agents/AgentChat";
import AgentAnchoring from "@/components/agents/AgentAnchoring";

interface Agent {
  id: string;
  name: string;
  wallet_address: string;
  xmtp_address?: string;
  status: string;
  created_at: string;
}

export default function AgentsPage() {
  const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

  // State
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [activeTab, setActiveTab] = useState<"agents" | "ai" | "activity" | "analytics" | "pricing" | "revenue" | "anchoring">("agents");
  const [loading, setLoading] = useState(true);
  const [showGuide, setShowGuide] = useState(true);
  const [showNewAgentForm, setShowNewAgentForm] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showTestModal, setShowTestModal] = useState(false);
  const [showQRModal, setShowQRModal] = useState(false);
  const [showTemplateModal, setShowTemplateModal] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [copiedAddress, setCopiedAddress] = useState("");
  const [testResponse, setTestResponse] = useState("");
  const [revenueDays, setRevenueDays] = useState(7);
  const [selectedTemplate, setSelectedTemplate] = useState<any>(null);
  
  // Anchoring state
  const [anchoringConfig, setAnchoringConfig] = useState({
    auto_anchor_enabled: false,
    anchor_on_payment: false,
    anchor_wallet: undefined as string | undefined,
  });
  const [anchors, setAnchors] = useState<any[]>([]);

  // AI Config
  const [aiConfig, setAiConfig] = useState({
    ai_mode: "simple",
    ai_system_prompt: "",
    ai_provider: "openai",
    ai_model: "gpt-4o-mini",
  });

  // Data
  const [pricing, setPricing] = useState<any[]>([]);
  const [revenue, setRevenue] = useState<any>(null);
  const [activityLogs] = useState([
    { id: "1", type: "message" as const, content: "Received XMTP message: show receipts", timestamp: new Date(Date.now() - 300000) },
    { id: "2", type: "payment" as const, content: "x402 payment: 0.01 USDC to /v1/receipts", timestamp: new Date(Date.now() - 600000) },
    { id: "3", type: "message" as const, content: "Sent response with 5 receipts", timestamp: new Date(Date.now() - 900000) },
  ]);
  const [analytics] = useState({
    messagesProcessed: 1247,
    averageResponseTime: 342,
    successRate: 98.5,
    totalCost: 12.45,
    topCommands: [
      { command: "list receipts", count: 456 },
      { command: "verify bundle", count: 312 },
      { command: "get statement", count: 189 },
    ],
  });

  // Load data
  useEffect(() => {
    loadData();
  }, []);

  // Load anchors when switching to anchoring tab
  useEffect(() => {
    if (selectedAgent && activeTab === "anchoring") {
      loadAnchors();
    }
  }, [selectedAgent, activeTab]);

  const loadData = async () => {
    setLoading(true);
    try {
      const agentsRes = await fetch(`${API_BASE}/v1/agents`);
      if (agentsRes.ok) {
        setAgents(await agentsRes.json());
      }

      const pricingRes = await fetch(`${API_BASE}/v1/x402/pricing`);
      if (pricingRes.ok) {
        setPricing(await pricingRes.json());
      }

      await loadRevenue(revenueDays);
    } catch (err) {
      console.error("Failed to load data:", err);
    } finally {
      setLoading(false);
    }
  };

  const loadRevenue = async (days: number) => {
    try {
      const res = await fetch(`${API_BASE}/v1/x402/revenue?days=${days}`);
      if (res.ok) {
        setRevenue(await res.json());
      }
    } catch (err) {
      console.error("Failed to load revenue:", err);
    }
  };

  // Agent operations
  const createAgent = async (formData: { name: string; wallet_address: string; xmtp_address?: string }) => {
    try {
      const res = await fetch(`${API_BASE}/v1/agents`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });

      if (res.ok) {
        await loadData();
        setShowNewAgentForm(false);
        setShowTemplateModal(false);
      } else {
        alert("Failed to create agent");
      }
    } catch (err) {
      alert("Failed to create agent");
    }
  };

  const updateAgent = async (formData: { name: string; wallet_address: string; xmtp_address?: string }) => {
    if (!selectedAgent) return;
    
    try {
      const res = await fetch(`${API_BASE}/v1/agents/${selectedAgent.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });

      if (res.ok) {
        await loadData();
        setShowEditModal(false);
      } else {
        alert("Failed to update agent");
      }
    } catch (err) {
      alert("Failed to update agent");
    }
  };

  const deleteAgent = async () => {
    if (!selectedAgent || !confirm("Delete this agent?")) return;

    try {
      const res = await fetch(`${API_BASE}/v1/agents/${selectedAgent.id}`, {
        method: "DELETE",
      });

      if (res.ok) {
        await loadData();
        setSelectedAgent(null);
      } else {
        alert("Failed to delete agent");
      }
    } catch (err) {
      alert("Failed to delete agent");
    }
  };

  const cloneAgent = async () => {
    if (!selectedAgent) return;
    await createAgent({
      name: `${selectedAgent.name} (Copy)`,
      wallet_address: selectedAgent.wallet_address,
      xmtp_address: selectedAgent.xmtp_address,
    });
  };

  const downloadAgent = async () => {
    if (!selectedAgent) return;
    
    try {
      const res = await fetch(`${API_BASE}/v1/agents/${selectedAgent.id}/download-template`, {
        method: "POST",
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${selectedAgent.name.replace(/ /g, "-")}-agent.zip`;
        a.click();
      }
    } catch (err) {
      alert("Failed to download agent");
    }
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopiedAddress(label);
    setTimeout(() => setCopiedAddress(""), 2000);
  };

  const sendTestMessage = async (message: string) => {
    if (!selectedAgent) return "";
    
    try {
      const res = await fetch(`${API_BASE}/v1/agents/${selectedAgent.id}/test-ai`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ test_message: message }),
      });

      if (res.ok) {
        const data = await res.json();
        const response = `✅ Success!\n\nMode: ${data.mode}\nParsed: ${JSON.stringify(data.parsed_result, null, 2)}`;
        setTestResponse(response);
        return response;
      }
      return "❌ Test failed";
    } catch (err) {
      return "❌ Error sending test message";
    }
  };

  const saveAIConfig = async () => {
    if (!selectedAgent) return;
    
    try {
      const res = await fetch(`${API_BASE}/v1/agents/${selectedAgent.id}/ai-config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(aiConfig),
      });
      
      if (res.ok) {
        alert("✅ AI configuration saved!");
      } else {
        alert("❌ Failed to save AI config");
      }
    } catch (err) {
      alert("❌ Failed to save AI config");
    }
  };

  const handleChatMessage = async (message: string) => {
    try {
      const res = await fetch(`${API_BASE}/v1/ai/parse-command`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message,
          system_prompt: `You are a helpful assistant for the ISO 20022 Payment Middleware agent setup system.
Help users understand agent configuration, AI modes, deployment, x402 payments, and troubleshooting.
Be concise, friendly, and technical.`,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        return data.raw_response || "I'm here to help! Could you rephrase your question?";
      }
      return "Sorry, I encountered an error.";
    } catch (err) {
      return "Sorry, I encountered an error.";
    }
  };

  // Anchoring functions
  const loadAnchors = async () => {
    if (!selectedAgent) return;
    try {
      const res = await fetch(`${API_BASE}/v1/agents/${selectedAgent.id}/anchors`);
      if (res.ok) {
        setAnchors(await res.json());
      }
    } catch (err) {
      console.error("Failed to load anchors:", err);
    }
  };

  const saveAnchoringConfig = async () => {
    if (!selectedAgent) return;
    try {
      const res = await fetch(`${API_BASE}/v1/agents/${selectedAgent.id}/anchoring-config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(anchoringConfig),
      });
      
      if (res.ok) {
        alert("✅ Anchoring configuration saved!");
      } else {
        alert("❌ Failed to save anchoring config");
      }
    } catch (err) {
      alert("❌ Failed to save anchoring config");
    }
  };

  const tabs = [
    { id: "agents", icon: Bot, label: "Details" },
    { id: "ai", icon: Brain, label: "AI Settings" },
    { id: "activity", icon: Activity, label: "Activity" },
    { id: "analytics", icon: BarChart3, label: "Analytics" },
    { id: "anchoring", icon: Anchor, label: "Anchoring" },
    { id: "pricing", icon: DollarSign, label: "Pricing" },
    { id: "revenue", icon: TrendingUp, label: "Revenue" },
  ];

  return (
    <div className="flex h-[calc(100vh-73px)] relative">
      {/* Left Sidebar */}
      <AgentsList
        agents={agents}
        selectedAgent={selectedAgent}
        onSelectAgent={setSelectedAgent}
        loading={loading}
        showGuide={showGuide}
        onHideGuide={() => setShowGuide(false)}
        showNewAgentForm={showNewAgentForm}
        onToggleNewAgentForm={() => {
          setShowNewAgentForm(!showNewAgentForm);
          if (!showNewAgentForm) setSelectedTemplate(null);
        }}
        onToggleTemplateModal={() => setShowTemplateModal(true)}
        onCreateAgent={createAgent}
        selectedTemplate={selectedTemplate}
      />

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto pb-20">
        <div className="p-6">
          {/* Tabs */}
          <div className="flex gap-2 mb-6 border-b border-slate-200 overflow-x-auto">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`px-4 py-2 font-medium transition-colors whitespace-nowrap ${
                  activeTab === tab.id
                    ? "border-b-2 border-slate-900 text-slate-900"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                <div className="flex items-center gap-2">
                  <tab.icon className="h-4 w-4" />
                  {tab.label}
                </div>
              </button>
            ))}
          </div>

          {/* Tab Content */}
          {activeTab === "agents" && selectedAgent && (
            <AgentDetails
              agent={selectedAgent}
              copiedAddress={copiedAddress}
              onCopy={copyToClipboard}
              onEdit={() => setShowEditModal(true)}
              onTest={() => setShowTestModal(true)}
              onShowQR={() => setShowQRModal(true)}
              onClone={cloneAgent}
              onDelete={deleteAgent}
              onDownload={downloadAgent}
              API_BASE={API_BASE}
            />
          )}

          {activeTab === "agents" && !selectedAgent && (
            <div className="text-center py-12 text-slate-500">
              <Bot className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <div>Select an agent from the left sidebar to view details</div>
            </div>
          )}

          {activeTab === "activity" && selectedAgent && (
            <AgentActivity logs={activityLogs} onRefresh={loadData} />
          )}

          {activeTab === "analytics" && selectedAgent && (
            <AgentAnalytics stats={analytics} />
          )}

          {activeTab === "ai" && selectedAgent && (
            <AgentAISettings
              agent={selectedAgent}
              config={aiConfig}
              onConfigChange={setAiConfig}
              onSave={saveAIConfig}
              onTest={() => setShowTestModal(true)}
            />
          )}

          {activeTab === "pricing" && (
            <AgentPricing pricing={pricing} />
          )}

          {activeTab === "revenue" && (
            <AgentRevenue
              revenue={revenue}
              days={revenueDays}
              onDaysChange={(days) => {
                setRevenueDays(days);
                loadRevenue(days);
              }}
            />
          )}

          {activeTab === "anchoring" && selectedAgent && (
            <AgentAnchoring
              agent={selectedAgent}
              config={anchoringConfig}
              anchors={anchors}
              onConfigChange={(newConfig) => setAnchoringConfig({ ...anchoringConfig, ...newConfig })}
              onSaveConfig={saveAnchoringConfig}
              API_BASE={API_BASE}
            />
          )}
        </div>
      </div>

      {/* Modals */}
      <AgentModals
        selectedAgent={selectedAgent}
        showEditModal={showEditModal}
        showTestModal={showTestModal}
        showQRModal={showQRModal}
        showTemplateModal={showTemplateModal}
        onCloseEdit={() => setShowEditModal(false)}
        onCloseTest={() => setShowTestModal(false)}
        onCloseQR={() => setShowQRModal(false)}
        onCloseTemplate={() => setShowTemplateModal(false)}
        onUpdateAgent={updateAgent}
        onSendTest={sendTestMessage}
        onSelectTemplate={(template) => {
          setShowTemplateModal(false);
          setShowNewAgentForm(true);
          setSelectedTemplate(template);
          // Apply template AI configuration
          setAiConfig({
            ai_mode: template.ai_mode,
            ai_system_prompt: template.system_prompt || "",
            ai_provider: "openai",
            ai_model: "gpt-4o-mini",
          });
        }}
        testResponse={testResponse}
      />

      {/* AI Chat */}
      <AgentChat
        show={showChat}
        onToggle={() => setShowChat(!showChat)}
        onSendMessage={handleChatMessage}
      />
    </div>
  );
}
