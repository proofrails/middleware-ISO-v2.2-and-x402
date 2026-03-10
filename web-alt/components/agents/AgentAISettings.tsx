import { HelpCircle, Brain } from "lucide-react";

interface Agent {
  id: string;
  name: string;
}

interface AIConfig {
  ai_mode: string;
  ai_system_prompt: string;
  ai_provider: string;
  ai_model: string;
}

interface AgentAISettingsProps {
  agent: Agent;
  config: AIConfig;
  onConfigChange: (config: AIConfig) => void;
  onSave: () => void;
  onTest: () => void;
}

export default function AgentAISettings({
  agent,
  config,
  onConfigChange,
  onSave,
  onTest,
}: AgentAISettingsProps) {
  return (
    <div className="space-y-4">
      {/* AI Mode Instructions */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
        <div className="flex items-start gap-2">
          <HelpCircle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-amber-900">
            <div className="font-semibold mb-1">Choose Your AI Mode</div>
            <ul className="space-y-1 ml-4 list-disc">
              <li><strong>Simple:</strong> No AI - agent only understands exact commands (FREE, fast)</li>
              <li><strong>Shared:</strong> Use our OpenAI API for natural language (FREE for you!)</li>
              <li><strong>Custom:</strong> Bring your own AI API key (privacy, control, you pay)</li>
            </ul>
          </div>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-lg p-6">
        <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
          <Brain className="h-5 w-5" />
          AI Configuration
        </h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">AI Mode</label>
            <select
              value={config.ai_mode}
              onChange={(e) => onConfigChange({ ...config, ai_mode: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded"
            >
              <option value="simple">Simple - No AI (exact commands only)</option>
              <option value="shared">Shared - Use system AI (FREE)</option>
              <option value="custom">Custom - Your own AI API key</option>
            </select>
          </div>

          {(config.ai_mode === "shared" || config.ai_mode === "custom") && (
            <div>
              <label className="block text-sm font-medium mb-2">
                System Prompt (Optional)
                <span className="text-xs text-slate-500 ml-2">Customize AI behavior</span>
              </label>
              <textarea
                value={config.ai_system_prompt}
                onChange={(e) => onConfigChange({ ...config, ai_system_prompt: e.target.value })}
                placeholder="You are a helpful assistant for ABC Corp payments team..."
                className="w-full px-3 py-2 border border-slate-300 rounded h-24 text-sm"
              />
            </div>
          )}

          {config.ai_mode === "custom" && (
            <>
              <div>
                <label className="block text-sm font-medium mb-2">AI Provider</label>
                <select
                  value={config.ai_provider}
                  onChange={(e) => onConfigChange({ ...config, ai_provider: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded"
                >
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic (Claude)</option>
                  <option value="google">Google (Gemini)</option>
                  <option value="custom">Custom Endpoint</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Model</label>
                <input
                  type="text"
                  value={config.ai_model}
                  onChange={(e) => onConfigChange({ ...config, ai_model: e.target.value })}
                  placeholder="gpt-4o-mini, claude-3-haiku, gemini-pro..."
                  className="w-full px-3 py-2 border border-slate-300 rounded text-sm"
                />
              </div>
            </>
          )}

          <div className="flex gap-2">
            <button
              onClick={onSave}
              className="px-4 py-2 bg-slate-900 text-white rounded hover:bg-slate-700"
              title="Save AI configuration - will be included in downloaded agent"
            >
              Save AI Config
            </button>
            <button
              onClick={onTest}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              title="Test AI parsing with sample message"
            >
              Test AI
            </button>
          </div>

          <div className="mt-4 p-4 bg-slate-50 rounded text-sm">
            <div className="font-semibold mb-2">💰 Cost Comparison</div>
            <div className="space-y-1">
              <div><strong>Simple:</strong> FREE (no AI, exact commands)</div>
              <div><strong>Shared:</strong> FREE (included with ISO Middleware)</div>
              <div><strong>Custom:</strong> Your OpenAI bill (~$0.0001 per command)</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
