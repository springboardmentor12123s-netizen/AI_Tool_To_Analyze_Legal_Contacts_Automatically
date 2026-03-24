"use client";
import React, { useState } from "react";
import { sendChatMessage } from "@/lib/api";
import { MessageSquare, Send, X, Bot, User } from "lucide-react";

interface ChatbotProps {
  selectedDoc: string;
}

interface Message {
  role: "user" | "bot";
  content: string;
}

export default function Chatbot({ selectedDoc }: ChatbotProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    { role: "bot", content: `Hello! I'm ready to answer specific questions about **${selectedDoc}**.` }
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);

  // Reset chat if document changes
  React.useEffect(() => {
    setMessages([{ role: "bot", content: `Focus switched to **${selectedDoc}**. What do you want to know?` }]);
  }, [selectedDoc]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const query = input.trim();
    setMessages(prev => [...prev, { role: "user", content: query }]);
    setInput("");
    setIsTyping(true);

    try {
      const res = await sendChatMessage(selectedDoc, query);
      setMessages(prev => [...prev, { role: "bot", content: res.answer }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: "bot", content: "Sorry, I encountered an error answering that." }]);
    } finally {
      setIsTyping(false);
    }
  };

  if (!isOpen) {
    return (
      <button 
        onClick={() => setIsOpen(true)}
        className="bg-indigo-600 hover:bg-indigo-700 text-white p-4 rounded-full shadow-2xl transition hover:scale-110 flex items-center justify-center"
      >
        <MessageSquare className="w-6 h-6" />
      </button>
    );
  }

  return (
    <div className="w-80 md:w-96 h-[32rem] bg-white rounded-2xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden animate-in slide-in-from-bottom-5">
      {/* Header */}
      <div className="bg-indigo-600 p-4 flex items-center justify-between text-white">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5" />
          <h3 className="font-semibold">ClauseAI Assist</h3>
        </div>
        <button onClick={() => setIsOpen(false)} className="hover:bg-indigo-500 p-1 rounded transition">
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] rounded-2xl p-3 text-sm shadow-sm ${msg.role === 'user' ? 'bg-indigo-600 text-white rounded-tr-sm' : 'bg-white text-slate-700 border border-slate-100 rounded-tl-sm'}`}>
              <div 
                  className="prose prose-sm prose-slate max-w-none break-words" 
                  dangerouslySetInnerHTML={{ __html: msg.content.replace(/\n/g, '<br/>') }} 
              />
            </div>
          </div>
        ))}
        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-white border border-slate-200 rounded-2xl p-4 rounded-tl-sm flex gap-1 items-center">
              <span className="w-2 h-2 rounded-full bg-slate-400 animate-bounce"></span>
              <span className="w-2 h-2 rounded-full bg-slate-400 animate-bounce delay-75"></span>
              <span className="w-2 h-2 rounded-full bg-slate-400 animate-bounce delay-150"></span>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <form onSubmit={handleSend} className="p-3 bg-white border-t border-slate-100 flex items-center gap-2">
        <input 
          type="text" 
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question..."
          className="flex-1 py-2 px-3 bg-slate-100 border-none rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
        />
        <button 
          type="submit" 
          disabled={!input.trim()}
          className="p-2 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:opacity-50 transition drop-shadow-sm"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
}
