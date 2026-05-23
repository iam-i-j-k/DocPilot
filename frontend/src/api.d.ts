export interface Job {
    job_id: string;
    filename: string;
    status: 'queued' | 'parsing' | 'extracting_images' | 'describing_images' | 'writing' | 'completed' | 'failed';
    progress: number;
    created_at: string;
    error?: string | null;
    output_path?: string | null;
}
export declare function fetchJobs(): Promise<Job[]>;
export declare function uploadPdfFile(file: File): Promise<{
    job_id: string;
    status: string;
}>;
export declare function getDownloadUrl(jobId: string): string;
export declare function cancelJob(jobId: string): Promise<void>;
//# sourceMappingURL=api.d.ts.map