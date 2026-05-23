// Direct backend URL
const BASE_URL = 'https://docpilot-zncb.onrender.com';
export async function fetchJobs() {
    const response = await fetch(`${BASE_URL}/jobs`);
    if (!response.ok) {
        throw new Error(`Failed to retrieve jobs list: ${response.statusText}`);
    }
    return response.json();
}
export async function uploadPdfFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${BASE_URL}/upload`, {
        method: 'POST',
        body: formData,
    });
    if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Upload process failed: ${response.statusText}`);
    }
    return response.json();
}
export function getDownloadUrl(jobId) {
    return `${BASE_URL}/jobs/${jobId}/download`;
}
export async function cancelJob(jobId) {
    const response = await fetch(`${BASE_URL}/jobs/${jobId}/cancel`, {
        method: 'POST',
    });
    if (!response.ok) {
        throw new Error(`Failed to cancel job: ${response.statusText}`);
    }
}
//# sourceMappingURL=api.js.map