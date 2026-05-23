import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import React, { useEffect, useState, useRef } from 'react';
import { RefreshCcw, FileSpreadsheet, Radio } from 'lucide-react';
import { Job, fetchJobs } from '../api';
import { JobCard } from './JobCard';
export const JobList = ({ refreshTrigger }) => {
    const [jobs, setJobs] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);
    const [isPolling, setIsPolling] = useState(false);
    const pollingIntervalRef = useRef(null);
    const loadJobsAndVerifyPolling = async (showLoading = false) => {
        if (showLoading) {
            setIsLoading(true);
        }
        setError(null);
        try {
            const data = await fetchJobs();
            setJobs(data);
            // Check if there are active jobs that require polling
            const hasActive = data.some((job) => job.status !== 'completed' && job.status !== 'failed');
            setIsPolling(hasActive);
        }
        catch (err) {
            setError(err.message || 'Failed to list background jobs.');
        }
        finally {
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
        }
        else {
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
    return (_jsxs("div", { className: "w-full bg-white rounded-xl border border-gray-100 shadow-xs p-6 space-y-4", children: [_jsxs("div", { className: "flex justify-between items-center pb-2 border-b border-gray-50", children: [_jsxs("div", { className: "flex items-center gap-2", children: [_jsx(FileSpreadsheet, { className: "w-5 h-5 text-indigo-500" }), _jsx("h2", { className: "text-lg font-semibold text-gray-800", children: "Job Directory" }), isPolling && (_jsxs("span", { className: "flex items-center gap-1.5 text-[10px] font-bold tracking-wider uppercase text-blue-600 bg-blue-50 border border-blue-100 px-2 py-0.5 rounded-full animate-pulse-slow", children: [_jsx(Radio, { className: "w-2.5 h-2.5" }), "Live Polling"] }))] }), _jsx("button", { id: "manual-refresh-btn", onClick: handleManualRefresh, className: "p-1.5 hover:bg-gray-50 border border-gray-100 text-gray-400 hover:text-gray-600 rounded-lg transition-all", title: "Refresh Job list", children: _jsx(RefreshCcw, { className: `w-4 h-4 ${isLoading ? 'animate-spin' : ''}` }) })] }), isLoading && jobs.length === 0 ? (_jsxs("div", { className: "flex flex-col items-center justify-center py-12 text-gray-400 space-y-2", children: [_jsx(RefreshCcw, { className: "w-8 h-8 animate-spin text-indigo-500" }), _jsx("p", { className: "text-xs", children: "Loading jobs directory..." })] })) : error ? (_jsxs("div", { className: "text-center py-8 text-rose-600", children: [_jsx("p", { className: "text-sm font-semibold", children: "Could not reach DocPilot backend" }), _jsx("p", { className: "text-xs text-gray-400 mt-1 max-w-xs mx-auto", children: error })] })) : jobs.length === 0 ? (_jsxs("div", { className: "text-center py-12 text-gray-400 border-2 border-dashed border-gray-50 rounded-lg", children: [_jsx(FileSpreadsheet, { className: "w-12 h-12 text-gray-200 mx-auto mb-2" }), _jsx("p", { className: "text-sm font-medium", children: "No conversion jobs found" }), _jsx("p", { className: "text-xs mt-1", children: "Select and submit a PDF above to launch the pipeline." })] })) : (_jsx("div", { className: "space-y-4 max-h-[500px] overflow-y-auto pr-1", children: jobs.map((job) => (_jsx(JobCard, { job: job }, job.job_id))) }))] }));
};
//# sourceMappingURL=JobList.js.map