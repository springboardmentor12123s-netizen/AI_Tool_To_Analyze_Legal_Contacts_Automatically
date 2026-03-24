const isBrowser = typeof window !== 'undefined';
export const API_URL = isBrowser ? `http://${window.location.hostname}:8000` : "http://localhost:8000";

export async function uploadMultipleFiles(files: File[]) {
  const formData = new FormData();
  files.forEach(file => {
    formData.append("files", file);
  });
  
  const res = await fetch(`${API_URL}/upload_bulk`, {
    method: "POST",
    body: formData,
  });
  
  if (!res.ok) throw new Error("Upload failed");
  return res.json();
}

export async function analyzeDocuments(filenames: string[], config: any) {
  const res = await fetch(`${API_URL}/analyze_bulk`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filenames, report_config: config }),
  });
  
  if (!res.ok) throw new Error("Analysis failed");
  return res.json();
}

export async function submitFeedback(filename: string, section: string, rating: string, comment: string) {
  const res = await fetch(`${API_URL}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename, section, rating, comment }),
  });
  
  if (!res.ok) throw new Error("Feedback failed");
  return res.json();
}

export async function sendChatMessage(filename: string, query: string) {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename, query }),
  });
  
  if (!res.ok) throw new Error("Chat failed");
  return res.json();
}
