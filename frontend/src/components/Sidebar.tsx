"use client";
import React, { useState } from "react";
import { uploadMultipleFiles, analyzeDocuments } from "@/lib/api";
import { FileUp, Settings2, ShieldCheck, FileCheck2, Loader2 } from "lucide-react";

interface SidebarProps {
  setDocuments: (docs: string[]) => void;
  setResults: (res: any[]) => void;
  setIsProcessing: (b: boolean) => void;
  isProcessing: boolean;
}

export default function Sidebar({ setDocuments, setResults, setIsProcessing, isProcessing }: SidebarProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [tone, setTone] = useState("formal");
  const [structure, setStructure] = useState<string[]>(["summary", "risks", "clauses"]);
  const [focus, setFocus] = useState<string[]>(["liability", "payment_terms"]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
    }
  };

  const handleAnalyze = async () => {
    if (files.length === 0) return alert("Please upload a file.");
    setIsProcessing(true);
    setResults([]);
    
    try {
      const uploadRes = await uploadMultipleFiles(files);
      const uploadedDocs = uploadRes.filenames || [];
      setDocuments(uploadedDocs);

      const analyzeRes = await analyzeDocuments(uploadedDocs, {
        tone, structure, focus
      });
      setResults(analyzeRes.results || []);
    } catch (err) {
      console.error(err);
      alert("An error occurred during processing.");
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <aside className="w-80 bg-white border-r border-slate-200 p-6 flex flex-col h-screen sticky top-0 shadow-sm z-10">
      <div className="flex items-center gap-3 mb-8">
        <div className="bg-indigo-600 p-2 rounded-xl shadow-lg shadow-indigo-200">
          <ShieldCheck className="w-6 h-6 text-white" />
        </div>
        <h2 className="text-xl font-bold text-slate-900 tracking-tight">ClauseAI Base</h2>
      </div>

      <div className="flex-1 overflow-y-auto pr-2 space-y-8">
        {/* Upload Section */}
        <section>
          <div className="flex items-center gap-2 mb-3">
            <FileUp className="w-5 h-5 text-slate-500" />
            <h3 className="font-semibold text-slate-700">1. Upload Contracts</h3>
          </div>
          <label className="flex justify-center w-full h-32 px-4 transition bg-white border-2 border-slate-300 border-dashed rounded-xl appearance-none cursor-pointer hover:border-indigo-400 focus:outline-none">
            <span className="flex items-center space-x-2">
              <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <span className="font-medium text-slate-500">
                {files.length > 0 ? `${files.length} files selected` : "Drop files to Select"}
              </span>
            </span>
            <input type="file" multiple name="file_upload" className="hidden" onChange={handleFileChange} />
          </label>
        </section>

        {/* Configuration Section */}
        <section>
          <div className="flex items-center gap-2 mb-3">
            <Settings2 className="w-5 h-5 text-slate-500" />
            <h3 className="font-semibold text-slate-700">2. Report Config</h3>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">Tone</label>
              <select 
                value={tone} onChange={e => setTone(e.target.value)}
                className="w-full rounded-lg border-slate-200 text-sm focus:ring-indigo-500 focus:border-indigo-500 shadow-sm"
              >
                <option value="formal">Formal</option>
                <option value="executive">Executive Summary</option>
                <option value="concise">Concise</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">Structure</label>
              <div className="flex flex-col gap-2">
                {["summary", "risks", "clauses", "recommendations"].map((s) => (
                  <label key={s} className="inline-flex items-center">
                    <input type="checkbox" className="rounded text-indigo-600 border-slate-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50" 
                      checked={structure.includes(s)}
                      onChange={(e) => {
                        if (e.target.checked) setStructure([...structure, s]);
                        else setStructure(structure.filter(x => x !== s));
                      }}
                    />
                    <span className="ml-2 text-sm text-slate-600 capitalize">{s}</span>
                  </label>
                ))}
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">Focus Areas</label>
              <div className="flex flex-col gap-2">
                {["liability", "payment_terms", "termination", "data_privacy"].map((f) => (
                  <label key={f} className="inline-flex items-center">
                    <input type="checkbox" className="rounded text-indigo-600 border-slate-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50" 
                      checked={focus.includes(f)}
                      onChange={(e) => {
                        if (e.target.checked) setFocus([...focus, f]);
                        else setFocus(focus.filter(x => x !== f));
                      }}
                    />
                    <span className="ml-2 text-sm text-slate-600 capitalize">{f.replace("_", " ")}</span>
                  </label>
                ))}
              </div>
            </div>

          </div>
        </section>
      </div>

      <div className="mt-auto pt-6 border-t border-slate-100">
        <button 
          onClick={handleAnalyze} 
          disabled={isProcessing}
          className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 px-4 rounded-xl transition-all shadow-md hover:shadow-lg disabled:opacity-70 disabled:cursor-not-allowed"
        >
          {isProcessing ? <><Loader2 className="w-5 h-5 animate-spin" /> Analyzing...</> : <><FileCheck2 className="w-5 h-5" /> Extract & Analyze</>}
        </button>
      </div>
    </aside>
  );
}
