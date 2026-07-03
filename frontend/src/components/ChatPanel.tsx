import { useEffect, useRef, useState } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
  used_tools?: string[];
}

const PRESETS = [
  "Show my recurring subscriptions.",
  "What is my biggest expense?",
  "Get a category breakdown of my spending.",
  "Show details on Food spending.",
];

export default function ChatPanel({ sessionId }: { sessionId: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Load chat history
  useEffect(() => {
    async function loadHistory() {
      try {
        const res = await fetch(`/api/chat/${sessionId}`);
        if (res.ok) {
          const body = await res.json();
          setMessages(body);
        }
      } catch (err) {
        console.error("Failed to load chat history:", err);
      }
    }
    loadHistory();
  }, [sessionId]);

  // Scroll to bottom on new message
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSend(text: string) {
    if (!text.trim() || loading) return;

    const userMessage: Message = { role: "user", content: text };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, message: text }),
      });

      if (!res.ok) {
        throw new Error(`Failed to send message: ${res.status}`);
      }

      const body = await res.json();
      const assistantMessage: Message = {
        role: "assistant",
        content: body.answer,
        used_tools: body.used_tools,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "I'm sorry, I'm having trouble connecting right now. Please try again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col rounded-2xl bg-white shadow-sm ring-1 ring-slate-100 h-[600px]">
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-slate-100 p-4">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-50 text-base shadow-xs ring-1 ring-indigo-100">
          🤖
        </span>
        <div>
          <h2 className="text-sm font-semibold text-slate-800">Financial Analyst Buddy</h2>
          <p className="text-xs text-slate-400">Ask questions, search merchants, or analyze trends</p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center p-6">
            <span className="text-3xl mb-3">💬</span>
            <h3 className="text-sm font-semibold text-slate-700">No messages yet</h3>
            <p className="text-xs text-slate-400 max-w-[260px] mt-1.5 leading-relaxed font-medium">
              Ask your analyst buddy to find details, list subscriptions, or filter transactions.
            </p>
          </div>
        )}

        {messages.map((m, i) => {
          const isUser = m.role === "user";
          return (
            <div key={i} className={`flex items-start gap-2.5 ${isUser ? "justify-end" : "justify-start"}`}>
              {!isUser && (
                <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-slate-100 text-xs shadow-xs flex-shrink-0 mt-0.5 select-none">
                  🤖
                </span>
              )}
              <div
                className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm shadow-xs ${
                  isUser
                    ? "bg-indigo-600 text-white rounded-br-none"
                    : "bg-slate-100 text-slate-800 rounded-bl-none"
                }`}
              >
                <div className="whitespace-pre-wrap leading-relaxed font-medium">{m.content}</div>

                {/* Developer metadata: used tools list */}
                {!isUser && m.used_tools && m.used_tools.length > 0 && (
                  <div className="mt-2.5 pt-2 border-t border-slate-200/50 flex flex-wrap gap-1">
                    {m.used_tools.map((t) => (
                      <span
                        key={t}
                        className="inline-flex items-center rounded bg-slate-200 px-1.5 py-0.5 text-[9px] font-bold tracking-wider text-slate-500 uppercase"
                      >
                        🔧 {t}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              {isUser && (
                <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-50 text-xs shadow-xs flex-shrink-0 mt-0.5 select-none font-bold text-indigo-600">
                  👤
                </span>
              )}
            </div>
          );
        })}

        {loading && (
          <div className="flex items-start gap-2.5 justify-start">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-slate-100 text-xs flex-shrink-0 mt-0.5 select-none">
              🤖
            </span>
            <div className="bg-slate-100 text-slate-400 rounded-2xl rounded-bl-none px-4 py-2.5 text-sm flex items-center gap-1.5 shadow-xs">
              <span className="h-1.5 w-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
              <span className="h-1.5 w-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
              <span className="h-1.5 w-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
            </div>
          </div>
        )}
        <div ref={scrollRef} />
      </div>

      {/* Suggested Quick Presets */}
      {messages.length === 0 && (
        <div className="px-4 py-3 border-t border-slate-50">
          <p className="text-[10px] uppercase font-bold tracking-wider text-slate-400 mb-2">Suggested Queries</p>
          <div className="flex flex-wrap gap-1.5">
            {PRESETS.map((p) => (
              <button
                key={p}
                onClick={() => handleSend(p)}
                className="text-xs text-left bg-slate-50 hover:bg-indigo-50 border border-slate-200 hover:border-indigo-200 rounded-xl px-3 py-1.5 text-slate-600 font-semibold transition-colors cursor-pointer"
              >
                {p}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input Box */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend(input);
        }}
        className="flex items-center gap-2 border-t border-slate-100 p-4"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask anything about your statement..."
          disabled={loading}
          className="flex-1 bg-slate-50 hover:bg-slate-100/50 focus:bg-white text-sm outline-none border border-slate-100 focus:border-indigo-400 rounded-xl px-4 py-2.5 transition-colors disabled:opacity-50 font-medium"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="bg-indigo-600 disabled:bg-slate-200 text-white disabled:text-slate-400 font-bold text-sm rounded-xl px-4.5 py-2.5 hover:bg-indigo-700 transition-colors shadow-sm cursor-pointer"
        >
          Send
        </button>
      </form>
    </div>
  );
}
