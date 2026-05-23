import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import React, { useState } from 'react';
import { Download, AlertCircle, Clock, CheckCircle, FileText, Loader2, X } from 'lucide-react';
import { Job, getDownloadUrl, cancelJob } from '../api';
export const JobCard = ({ job }) => {
    const [isCancelling, setIsCancelling] = useState(false);
    // Format the ISO creation date cleanly
    const formatDateTime = (isoString) => {
        try {
            const date = new Date(isoString);
            return date.toLocaleDateString(undefined, {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
            });
        }
        catch {
            return isoString;
        }
    };
    const statusConfig = {
        queued: {
            color: 'bg-gray-100 text-gray-700 border-gray-200',
            label: 'Queued',
            icon: Clock,
        },
        parsing: {
            color: 'bg-blue-50 text-blue-700 border-blue-200 animate-pulse',
            label: 'Parsing Native Text',
            icon: Loader2,
        },
        extracting_images: {
            color: 'bg-blue-50 text-blue-700 border-blue-200 animate-pulse',
            label: 'Extracting Images',
            icon: Loader2,
        },
        describing_images: {
            color: 'bg-blue-50 text-blue-700 border-blue-200',
            label: 'Visualizing Images',
            icon: Loader2,
        },
        writing: {
            color: 'bg-blue-50 text-blue-700 border-blue-200 animate-pulse',
            label: 'Assembling Markdown',
            icon: Loader2,
        },
        completed: {
            color: 'bg-emerald-50 text-emerald-700 border-emerald-200',
            label: 'Completed Output',
            icon: CheckCircle,
        },
        failed: {
            color: 'bg-rose-50 text-rose-700 border-rose-200',
            label: 'Failed Convert',
            icon: AlertCircle,
        },
    };
    const currentStatus = statusConfig[job.status] || statusConfig.queued;
    const StatusIcon = currentStatus.icon;
    const handleDownload = () => {
        // Open standard native download context
        const downloadUrl = getDownloadUrl(job.job_id);
        window.location.href = downloadUrl;
    };
    const handleCancel = async () => {
        if (!window.confirm('Are you sure you want to cancel this job?')) {
            return;
        }
        setIsCancelling(true);
        try {
            await cancelJob(job.job_id);
            // Job will be updated on next poll
        }
        catch (err) {
            alert('Failed to cancel job. Please try again.');
        }
        finally {
            setIsCancelling(false);
        }
    };
    const isCancellable = ['queued', 'parsing', 'extracting_images', 'describing_images', 'writing'].includes(job.status);
    return (_jsxs("div", { id: `job-card-${job.job_id}`, className: `border rounded-xl p-5 bg-white transition-all shadow-xs hover:shadow-md ${job.status === 'failed'
            ? 'border-red-100 hover:border-red-200'
            : job.status === 'completed'
                ? 'border-emerald-100 hover:border-emerald-200'
                : 'border-gray-100 hover:border-gray-200'}`, children: [_jsxs("div", { className: "flex flex-col sm:flex-row sm:items-center justify-between gap-4", children: [_jsxs("div", { className: "flex items-start gap-3 min-w-0", children: [_jsx("div", { className: `p-2 rounded-lg shrink-0 ${job.status === 'completed' ? 'bg-emerald-50 text-emerald-600' :
                                    job.status === 'failed' ? 'bg-rose-50 text-rose-600' : 'bg-indigo-50 text-indigo-600'}`, children: _jsx(FileText, { className: "w-6 h-6" }) }), _jsxs("div", { className: "min-w-0", children: [_jsx("h3", { className: "text-sm font-semibold text-gray-800 truncate", title: job.filename, children: job.filename }), _jsxs("p", { className: "text-xs text-gray-400 flex items-center gap-1 mt-1", children: [_jsx(Clock, { className: "w-3.5 h-3.5" }), formatDateTime(job.created_at)] })] })] }), _jsxs("div", { className: "flex items-center gap-2", children: [_jsxs("span", { className: `inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-full border ${currentStatus.color}`, children: [_jsx(StatusIcon, { className: `w-3 h-3 ${job.status !== 'queued' && job.status !== 'completed' && job.status !== 'failed' ? 'animate-spin' : ''}` }), currentStatus.label] }), _jsxs("span", { className: "text-xs font-mono text-gray-400 bg-gray-50 border border-gray-100 px-1.5 py-0.5 rounded", children: ["ID: ", job.job_id.substring(0, 8), "..."] })] })] }), _jsx("div", { className: "mt-4", children: job.status === 'failed' ? (_jsxs("div", { id: `job-error-${job.job_id}`, className: "p-3 bg-red-50 rounded-lg text-red-700 text-xs flex items-start gap-2 border border-red-100", children: [_jsx(AlertCircle, { className: "w-4 h-4 shrink-0 mt-0.5" }), _jsxs("div", { className: "break-all", children: [_jsx("span", { className: "font-semibold", children: "Err details: " }), job.error || 'Unknown conversion pipeline process crash.'] })] })) : (_jsxs("div", { className: "space-y-1.5", children: [_jsxs("div", { className: "flex justify-between items-center text-xs font-medium text-gray-500", children: [_jsx("span", { children: "Progressing" }), _jsxs("span", { id: `job-progress-txt-${job.job_id}`, className: "font-mono", children: [job.progress, "%"] })] }), _jsx("div", { className: "relative w-full h-2 bg-gray-100 rounded-full overflow-hidden", children: _jsx("div", { id: `job-progress-bar-${job.job_id}`, className: `h-full rounded-full transition-all duration-500 ${job.status === 'completed' ? 'bg-emerald-500' : 'bg-indigo-600'}`, style: { width: `${job.progress}%` } }) })] })) }), _jsxs("div", { className: "mt-4 flex justify-end gap-2", children: [job.status === 'completed' && (_jsxs("button", { id: `download-zip-btn-${job.job_id}`, onClick: handleDownload, className: "inline-flex items-center gap-2 text-xs font-semibold px-4 py-2 bg-emerald-600 text-white hover:bg-emerald-700 active:scale-98 rounded-lg shadow-xs transition-all cursor-pointer", children: [_jsx(Download, { className: "w-3.5 h-3.5" }), "Download Markdown ZIP"] })), isCancellable && (_jsxs("button", { id: `cancel-job-btn-${job.job_id}`, onClick: handleCancel, disabled: isCancelling, className: "inline-flex items-center gap-2 text-xs font-semibold px-4 py-2 bg-red-600 text-white hover:bg-red-700 disabled:bg-red-400 disabled:cursor-not-allowed active:scale-98 rounded-lg shadow-xs transition-all", children: [_jsx(X, { className: "w-3.5 h-3.5" }), isCancelling ? 'Cancelling...' : 'Cancel Job'] }))] })] }));
};
//# sourceMappingURL=JobCard.js.map