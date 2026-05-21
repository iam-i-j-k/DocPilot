export interface Job {
  job_id: string;
  filename: string;
  status: 'queued' | 'parsing' | 'extracting_images' | 'describing_images' | 'writing' | 'completed' | 'failed';
  progress: number;
  created_at: string;
  error?: string | null;
  output_path?: string | null;
}

// Support hitting relative proxy '/api' or direct backend endpoints
const BASE_URL = (import.meta as any).env?.VITE_API_URL || '';

export async function fetchJobs(): Promise<Job[]> {
  const response = await fetch(`${BASE_URL}/api/jobs`);
  if (!response.ok) {
    throw new Error(`Failed to retrieve jobs list: ${response.statusText}`);
  }
  return response.json();
}

export async function uploadPdfFile(file: File): Promise<{ job_id: string; status: string }> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${BASE_URL}/api/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    throw new Error(errData.detail || `Upload process failed: ${response.statusText}`);
  }

  return response.json();
}

export function getDownloadUrl(jobId: string): string {
  return `${BASE_URL}/api/jobs/${jobId}/download`;
}
