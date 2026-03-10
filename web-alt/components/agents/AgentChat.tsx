import { MessageCircle, X, Send } from "lucide-react";
import { useState } from "react";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface AgentChatProps {
  show: boolean;
  onToggle: () => void;
  onSendMessage: (message: string) => Promise<string>;
}

export default function AgentChat({ show, onToggle, onSendMessage }: AgentChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMsg: ChatMessage = {
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const response = await onSendMessage(userMsg.content);
      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: response,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err) {
      const errorMsg: ChatMessage = {
        role: "assistant",
        content: "Sorry, I encountered an error. Please try again.",
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const quickQuestions = [
    "How do I set up my first agent?",
    "What's the difference between AI modes?",
    "How does x402 payment work?",
    "How do I deploy to Railway?",
  ];

  return (
    <div className="fixed bottom-4 right-4 z-50">
      {show ? (
        <div className="bg-white border-2 border-slate-300 rounded-lg shadow-2xl w-96 h-[500px] flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between p-3 border-b border-slate-200 bg-slate-50">
            <div className="flex items-center gap-2">
              <MessageCircle className="h-5 w-5 text-slate-700" />
              <span className="font-semibold">AI Assistant</span>
            </div>
            <div className="flex gap-1">
              {messages.length > 0 && (
                <button
                  onClick={() => setMessages([])}
                  className="p-1 hover:bg-slate-200 rounded text-xs text-slate-600"
                  title="Clear chat"
                >
                  Clear
                </button>
              )}
              <button onClick={onToggle} className="p-1 hover:bg-slate-200 rounded">
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 p-4 overflow-y-auto space-y-3">
            {messages.length === 0 ? (
              <div className="text-sm text-slate-600">
                <div className="mb-3">
                  <strong>Ask me anything about:</strong>
                </div>
                <ul className="space-y-1 ml-4 list-disc mb-4">
                  <li>How to set up agents</li>
                  <li>AI mode differences</li>
                  <li>Deployment options</li>
                  <li>x402 payment system</li>
                  <li>Troubleshooting</li>
                </ul>
                
                <div className="space-y-2">
                  <div className="text-xs font-semibold text-slate-700 mb-2">Quick questions:</div>
                  {quickQuestions.map((question, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        setInput(question);
                        setTimeout(handleSend, 100);
                      }}
                      className="w-full text-left px-3 py-2 bg-blue-50 hover:bg-blue-100 rounded text-xs text-blue-900 transition-colors"
                    >
                      {question}
                    </button>
                  ))}
                </div>

                <div className="mt-4 p-3 bg-blue-50 rounded text-xs">
                  💡 <strong>Tip:</strong> This AI assistant helps you configure and deploy agents. Once your agent is running, users will interact with <em>your</em> agent via XMTP messaging.
                </div>
              </div>
            ) : (
              <>
                {messages.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                        msg.role === "user"
                          ? "bg-blue-600 text-white"
                          : "bg-slate-100 text-slate-900"
                      }`}
                    >
                      <div className="whitespace-pre-wrap">{msg.content}</div>
                      <div
                        className={`text-xs mt-1 ${
                          msg.role === "user" ? "text-blue-100" : "text-slate-500"
                        }`}
                      >
                        {msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </div>
                    </div>
                  </div>
                ))}
                {loading && (
                  <div className="flex justify-start">
                    <div className="bg-slate-100 rounded-lg px-3 py-2 text-sm">
                      <div className="flex gap-1">
                        <span className="animate-bounce">●</span>
                        <span className="animate-bounce" style={{ animationDelay: "0.1s" }}>●</span>
                        <span className="animate-bounce" style={{ animationDelay: "0.2s" }}>●</span>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          {/* Input */}
          <div className="border-t border-slate-200 p-3">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSend();
              }}
              className="flex gap-2"
            >
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask me anything..."
                className="flex-1 px-3 py-2 border border-slate-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={loading}
              />
              <button
                type="submit"
                disabled={!input.trim() || loading}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium transition-colors"
              >
                <Send className="h-4 w-4" />
              </button>
            </form>
          </div>
        </div>
      ) : (
        <button
          onClick={onToggle}
          className="bg-slate-900 text-white p-4 rounded-full shadow-lg hover:bg-slate-700 transition-all"
          title="Open AI Assistant"
        >
          <MessageCircle className="h-6 w-6" />
        </button>
      )}
    </div>
  );
}
