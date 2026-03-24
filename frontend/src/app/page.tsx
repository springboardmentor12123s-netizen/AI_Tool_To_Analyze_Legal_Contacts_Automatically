"use client";
import React, { useState } from "react";
import Sidebar from "@/components/Sidebar";
import DashboardPanel from "@/components/DashboardPanel";
import Chatbot from "@/components/Chatbot";

export default function Home() {
  const [documents, setDocuments] = useState<string[]>([]);
  const [results, setResults] = useState<any[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  return (
    <div className="flex bg-slate-50 min-h-screen text-slate-800 font-sans selection:bg-indigo-100 selection:text-indigo-900">
      {/* Sidebar - Fix width and provide modern glass/border styling */}
      <Sidebar 
         setDocuments={setDocuments} 
         setResults={setResults} 
         setIsProcessing={setIsProcessing}
         isProcessing={isProcessing}
      />
      
      {/* Main Content Area */}
      <main className="flex-1 flex flex-col p-8 overflow-y-auto">
        <header className="mb-8">
          <h1 className="text-4xl font-extrabold tracking-tight text-slate-900 mb-2 bg-gradient-to-r from-indigo-600 to-violet-500 bg-clip-text text-transparent w-max">
            ClauseAI Dashboard
          </h1>
          <p className="text-slate-500 text-lg">Multi-Domain Interactive Contract Intelligence</p>
        </header>

        {/* 3-Panel Layout equivalent: Document List, Status, Main Report */}
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6">
          <DashboardPanel 
            documents={documents} 
            results={results} 
            selectedDoc={selectedDoc}
            setSelectedDoc={setSelectedDoc}
            isProcessing={isProcessing}
          />
        </div>
      </main>

      {/* Floating Modern RAG Chatbot */}
      {selectedDoc && (
         <div className="fixed bottom-6 right-6 z-50">
             <Chatbot selectedDoc={selectedDoc} />
         </div>
      )}
    </div>
  );
}
