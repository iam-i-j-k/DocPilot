import React, { useEffect, useState, useRef } from 'react';
import { RefreshCcw, FileSpreadsheet, Radio } from 'lucide-react';
import { type Job, fetchJobs } from '../api';
import { JobCard } from './JobCard';

interface JobListProps {
  refreshTrigger: number;
}

export const JobList: React.FC<JobListProps> = ({ refreshTrigger }) => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const pollingIntervalRef = useRef<number | null>(null);

  const loadJobsAndVerifyPolling = async (showLoading = false) => {
    if (showLoading) {
      setIsLoading(true);
    }
    setError(null);
    try {
      const data = await fetchJobs();
      setJobs(data);

      // Check if there are active jobs that require polling
      const hasActive = data.some(
        (job: Job) => job.status !== 'completed' && job.status !== 'failed'
      );
      setIsPolling(hasActive);
    } catch (err: any) {
      setError(err.message || 'Failed to list background jobs.');
    } finally {
      setIsLoading(false);
    }
  };

  // Load initially and whenever refreshTrigger transitions (triggered from UploadZone submit)
  useEffect(() => {
    loadJobsAndVerifyPolling(true);
  }, [refreshTrigger]);

  // Dynamic polling coordinator
  useEffect(() => {
    // If isPolling is true, run interval every 3 seconds
    if (isPolling) {
      pollingIntervalRef.current = setInterval(() => {
        loadJobsAndVerifyPolling(false);
      }, 3000);
    } else {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    }

    // Clean up interval on unmount or when polling value updates
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, [isPolling]);

  const handleManualRefresh = () => {
    loadJobsAndVerifyPolling(true);
  };

  return (
    <div className="w-full bg-white rounded-xl border border-gray-100 shadow-xs p-6 space-y-4">
      <div className="flex justify-between items-center pb-2 border-b border-gray-50">
        <div className="flex items-center gap-2">
          <FileSpreadsheet className="w-5 h-5 text-indigo-500" />
          <h2 className="text-lg font-semibold text-gray-800">Job Directory</h2>
          {isPolling && (
            <span className="flex items-center gap-1.5 text-[10px] font-bold tracking-wider uppercase text-blue-600 bg-blue-50 border border-blue-100 px-2 py-0.5 rounded-full animate-pulse-slow">
              <Radio className="w-2.5 h-2.5" />
              Live Polling
            </span>
          )}
        </div>

        <button
          id="manual-refresh-btn"
          onClick={handleManualRefresh}
          className="p-1.5 hover:bg-gray-50 border border-gray-100 text-gray-400 hover:text-gray-600 rounded-lg transition-all"
          title="Refresh Job list"
        >
          <RefreshCcw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {isLoading && jobs.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-gray-400 space-y-2">
          <RefreshCcw className="w-8 h-8 animate-spin text-indigo-500" />
          <p className="text-xs">Loading jobs directory...</p>
        </div>
      ) : error ? (
        <div className="text-center py-8 text-rose-600">
          <p className="text-sm font-semibold">Could not reach DocPilot backend</p>
          <p className="text-xs text-gray-400 mt-1 max-w-xs mx-auto">{error}</p>
        </div>
      ) : jobs.length === 0 ? (
        <div className="text-center py-12 text-gray-400 border-2 border-dashed border-gray-50 rounded-lg">
          <FileSpreadsheet className="w-12 h-12 text-gray-200 mx-auto mb-2" />
          <p className="text-sm font-medium">No conversion jobs found</p>
          <p className="text-xs mt-1">Select and submit a PDF above to launch the pipeline.</p>
        </div>
      ) : (
        <div className="space-y-4 max-h-[500px] overflow-y-auto pr-1">
          {jobs.map((job) => (
            <JobCard key={job.job_id} job={job} />
          ))}
        </div>
      )}
    </div>
  );
};
