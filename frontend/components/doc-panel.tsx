"use client";
import { useState, useRef, useEffect } from "react";
import { BookOpen, X } from "lucide-react";

export default function DocPanel() {
  const [open, setOpen] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Prevent body scroll when panel is open
  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => { document.body.style.overflow = ""; };
  }, [open]);

  if (!open) return (
    <button onClick={() => setOpen(true)}
      className="fixed bottom-6 left-6 z-50 w-12 h-12 rounded-full flex items-center justify-center shadow-lg transition-all hover:scale-105"
      style={{ background: "#19105B" }}>
      <BookOpen className="w-5 h-5 text-white" />
    </button>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="relative w-[92vw] h-[90vh] bg-white shadow-2xl flex flex-col overflow-hidden" style={{ borderRadius: 0 }}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-3 shrink-0 border-b border-gray-100" style={{ background: "#19105B" }}>
          <div className="flex items-center gap-3">
            <BookOpen className="w-4 h-4 text-white" />
            <span className="text-sm font-bold text-white">AI Recommendation Engine — How It Works</span>
          </div>
          <button onClick={() => setOpen(false)} className="w-8 h-8 flex items-center justify-center text-white opacity-70 hover:opacity-100 transition-all">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content — iframe loads the static HTML */}
        <iframe
          ref={iframeRef}
          src="/ai-pipeline.html"
          className="flex-1 w-full border-none"
          title="AI Pipeline Documentation"
        />
      </div>
    </div>
  );
}
