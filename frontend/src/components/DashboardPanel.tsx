"use client";
import React, { useState } from "react";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { submitFeedback } from "@/lib/api";
import { FileText, Loader2, CheckCircle2, AlertCircle, ThumbsUp, ThumbsDown } from "lucide-react";

interface DashboardPanelProps {
  documents: string[];
  results: any[];
  selectedDoc: string | null;
  setSelectedDoc: (doc: string) => void;
  isProcessing: boolean;
}

export default function DashboardPanel({ documents, results, selectedDoc, setSelectedDoc, isProcessing }: DashboardPanelProps) {
  const [feedbackComment, setFeedbackComment] = useState("");
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);

  const getDocStatus = (doc: string) => {
    if (isProcessing && !results.find(r => r.filename === doc)) return "processing";
    const res = results.find(r => r.filename === doc);
    if (!res) return "pending";
    return res.status; // "success" or "error"
  };

  const handleFeedback = async (rating: string) => {
    if (!selectedDoc) return;
    try {
      await submitFeedback(selectedDoc, "overall", rating, feedbackComment);
      setFeedbackSubmitted(true);
      setTimeout(() => setFeedbackSubmitted(false), 3000);
      setFeedbackComment("");
    } catch (err) {
      alert("Failed to save feedback.");
    }
  };

  const selectedResult = results.find(r => r.filename === selectedDoc);

  return (
    <>
      {/* Col 1: Live Status & Document List */}
      <div className="col-span-1 flex flex-col gap-6">
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
          <h3 className="font-bold text-slate-800 text-lg mb-4 flex items-center gap-2">
            <FileText className="w-5 h-5 text-indigo-500" />
            Analyzed Documents
          </h3>
          
          {documents.length === 0 ? (
            <div className="text-slate-400 text-sm text-center py-8 bg-slate-50 rounded-xl border border-dashed border-slate-200">
              No documents listed. Upload to begin.
            </div>
          ) : (
            <ul className="space-y-3">
              {documents.map((doc) => {
                const status = getDocStatus(doc);
                let StatusIcon = Loader2;
                let statusColor = "text-indigo-500 bg-indigo-50 animate-pulse";
                
                if (status === "success") {
                  StatusIcon = CheckCircle2;
                  statusColor = "text-emerald-500 bg-emerald-50";
                } else if (status === "error") {
                  StatusIcon = AlertCircle;
                  statusColor = "text-red-500 bg-red-50";
                } else if (status === "pending") {
                  StatusIcon = FileText;
                  statusColor = "text-slate-400 bg-slate-50";
                }

                return (
                  <li 
                    key={doc} 
                    onClick={() => setSelectedDoc(doc)}
                    className={`flex items-center justify-between p-3 rounded-xl cursor-pointer transition-all border ${selectedDoc === doc ? 'bg-indigo-50 border-indigo-200 shadow-sm' : 'bg-white border-slate-100 hover:bg-slate-50'}`}
                  >
                    <span className="font-medium text-slate-700 truncate mr-3">{doc}</span>
                    <div className={`p-1.5 rounded-lg ${statusColor}`}>
                      <StatusIcon className={`w-4 h-4 ${status === 'processing' ? 'animate-spin' : ''}`} />
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>

      {/* Col 2 & 3: Report Viewer */}
      <div className="col-span-1 lg:col-span-2">
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 h-full flex flex-col overflow-hidden">
          {selectedDoc ? (
            <>
              <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex justify-between items-center">
                <h3 className="font-bold text-slate-800 flex items-center gap-2">
                  Results for <span className="text-indigo-600 bg-indigo-100 px-2 py-0.5 rounded-md">{selectedDoc}</span>
                </h3>
              </div>
              
              <div className="p-6 flex-1 overflow-y-auto prose prose-slate prose-indigo max-w-none">
                {selectedResult ? (
                  selectedResult.status === "success" ? (
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {selectedResult.final_report}
                    </ReactMarkdown>
                  ) : (
                    <div className="text-red-500 bg-red-50 p-4 rounded-xl">Analysis failed: {selectedResult.error}</div>
                  )
                ) : (
                  <div className="flex flex-col items-center justify-center h-full text-slate-400 py-12">
                    <Loader2 className="w-8 h-8 animate-spin mb-4 text-indigo-400" />
                    <p>Processing report data...</p>
                  </div>
                )}
              </div>

              {/* Feedback Footer */}
              {selectedResult && selectedResult.status === "success" && (
                <div className="bg-slate-50 border-t border-slate-200 p-4 px-6 flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-600">Was this analysis accurate?</span>
                  
                  {feedbackSubmitted ? (
                    <span className="text-sm text-emerald-600 font-semibold flex items-center gap-1"><CheckCircle2 className="w-4 h-4"/> Thank you!</span>
                  ) : (
                    <div className="flex gap-3">
                      <input 
                        type="text" 
                        placeholder="Add a comment..." 
                        value={feedbackComment} 
                        onChange={(e) => setFeedbackComment(e.target.value)}
                        className="text-sm rounded-lg border-slate-300 focus:ring-indigo-500 focus:border-indigo-500"
                      />
                      <button onClick={() => handleFeedback("up")} className="p-2 text-emerald-600 hover:bg-emerald-100 rounded-lg transition bg-white border border-slate-200 shadow-sm"><ThumbsUp className="w-4 h-4" /></button>
                      <button onClick={() => handleFeedback("down")} className="p-2 text-rose-600 hover:bg-rose-100 rounded-lg transition bg-white border border-slate-200 shadow-sm"><ThumbsDown className="w-4 h-4" /></button>
                    </div>
                  )}
                </div>
              )}
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-slate-400">
              <FileText className="w-16 h-16 text-slate-200 mb-4" />
              <p className="text-lg font-medium text-slate-500">Select a document to view its report</p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
