"use client";
import { useState, useRef, useEffect } from "react";
import { MessageCircle, X, Send, Loader2, Sparkles } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import api from "@/lib/api";

interface Message { role: "user" | "assistant"; content: string }

export default function ChatPanel() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const userMsg: Message = { role: "user", content: input.trim() };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    try {
      const res = await api.post("/api/chat", { message: userMsg.content, history: messages.slice(-10) });
      setMessages(prev => [...prev, { role: "assistant", content: res.data.reply }]);
    } catch {
      setMessages(prev => [...prev, { role: "assistant", content: "Sorry, something went wrong. Please try again." }]);
    }
    setLoading(false);
  };

  if (!open) return (
    <button onClick={() => setOpen(true)}
      className="fixed bottom-6 right-6 z-50 w-12 h-12 rounded-full flex items-center justify-center shadow-lg transition-all hover:scale-105"
      style={{ background: "#19105B" }}>
      <MessageCircle className="w-5 h-5 text-white" />
    </button>
  );

  return (
    <div className="fixed bottom-6 right-6 z-50 w-[380px] h-[520px] flex flex-col bg-white border border-gray-200 shadow-2xl" style={{ borderRadius: 0 }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 shrink-0" style={{ background: "#19105B" }}>
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-white" />
          <span className="text-sm font-bold text-white">RMG Assistant</span>
        </div>
        <button onClick={() => setOpen(false)} className="w-6 h-6 flex items-center justify-center text-white opacity-70 hover:opacity-100">
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {messages.length === 0 && (
          <div className="text-center py-8">
            <Sparkles className="w-8 h-8 mx-auto mb-3 opacity-20" style={{ color: "#19105B" }} />
            <p className="text-xs font-semibold" style={{ color: "#19105B" }}>Ask me anything about resources</p>
            <div className="mt-3 space-y-1.5">
              {["Who's available for Data Engineering?", "Show capacity gap", "What's EMP11's status?"].map(q => (
                <button key={q} onClick={() => { setInput(q); }} className="block w-full text-left text-[11px] px-3 py-1.5 rounded bg-gray-50 border border-gray-100 hover:border-gray-200 transition-all" style={{ color: "#19105B" }}>{q}</button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[85%] px-3 py-2 text-xs leading-relaxed ${m.role === "user" ? "text-white" : "bg-gray-50 border border-gray-100 overflow-x-auto"}`}
              style={m.role === "user" ? { background: "#19105B", color: "#fff" } : { color: "#19105B" }}>
              {m.role === "user" ? m.content : (
                <div className="[&_table]:w-full [&_table]:text-[10px] [&_table]:border-collapse [&_table]:my-2 [&_th]:bg-gray-100 [&_th]:px-2 [&_th]:py-1 [&_th]:text-left [&_th]:font-bold [&_th]:border [&_th]:border-gray-200 [&_td]:px-2 [&_td]:py-1 [&_td]:border [&_td]:border-gray-200 [&_strong]:font-bold [&_ul]:ml-3 [&_ul]:list-disc [&_ol]:ml-3 [&_ol]:list-decimal [&_li]:mb-1 [&_p]:mb-2 [&_h1]:font-bold [&_h1]:text-sm [&_h2]:font-bold [&_h2]:text-xs [&_h3]:font-bold">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="px-3 py-2 bg-gray-50 border border-gray-100 rounded">
              <Loader2 className="w-3.5 h-3.5 animate-spin" style={{ color: "#19105B" }} />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="shrink-0 px-3 py-3 border-t border-gray-100">
        <div className="flex items-center gap-2">
          <input value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && send()}
            placeholder="Ask about resources, projects, availability..."
            className="flex-1 text-xs px-3 py-2 border border-gray-200 rounded focus:outline-none focus:border-gray-400" style={{ color: "#19105B" }} />
          <button onClick={send} disabled={!input.trim() || loading}
            className="w-8 h-8 flex items-center justify-center rounded disabled:opacity-30 transition-all"
            style={{ background: "#19105B" }}>
            <Send className="w-3.5 h-3.5 text-white" />
          </button>
        </div>
      </div>
    </div>
  );
}
