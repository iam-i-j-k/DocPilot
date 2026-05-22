import React, { useState } from 'react';
import { Download, AlertCircle, Clock, CheckCircle, FileText, Loader2, X } from 'lucide-react';
import { Job, getDownloadUrl, cancelJob } from '../api';

interface JobCardProps {
  job: Job;
}

export const JobCard: React.FC<JobCardProps> = ({ job }) => {
  const [isCancelling, setIsCancelling] = useState(false);

  // Format the ISO creation date cleanly
  const formatDateTime = (isoString: string): string => {
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
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
    } catch (err) {
      alert('Failed to cancel job. Please try again.');
    } finally {
      setIsCancelling(false);
    }
  };

  const isCancellable = ['queued', 'parsing', 'extracting_images', 'describing_images', 'writing'].includes(job.status);

  return (
    <div
      id={`job-card-${job.job_id}`}
      className={`border rounded-xl p-5 bg-white transition-all shadow-xs hover:shadow-md ${
        job.status === 'failed'
          ? 'border-red-100 hover:border-red-200'
          : job.status === 'completed'
          ? 'border-emerald-100 hover:border-emerald-200'
          : 'border-gray-100 hover:border-gray-200'
      }`}
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        {/* Document meta */}
        <div className="flex items-start gap-3 min-w-0">
          <div className={`p-2 rounded-lg shrink-0 ${
            job.status === 'completed' ? 'bg-emerald-50 text-emerald-600' :
            job.status === 'failed' ? 'bg-rose-50 text-rose-600' : 'bg-indigo-50 text-indigo-600'
          }`}>
            <FileText className="w-6 h-6" />
          </div>
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-gray-800 truncate" title={job.filename}>
              {job.filename}
            </h3>
            <p className="text-xs text-gray-400 flex items-center gap-1 mt-1">
              <Clock className="w-3.5 h-3.5" />
              {formatDateTime(job.created_at)}
            </p>
          </div>
        </div>

        {/* Status indicator badge */}
        <div className="flex items-center gap-2">
          <span className={`inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-full border ${currentStatus.color}`}>
            <StatusIcon className={`w-3 h-3 ${job.status !== 'queued' && job.status !== 'completed' && job.status !== 'failed' ? 'animate-spin' : ''}`} />
            {currentStatus.label}
          </span>
          <span className="text-xs font-mono text-gray-400 bg-gray-50 border border-gray-100 px-1.5 py-0.5 rounded">
            ID: {job.job_id.substring(0, 8)}...
          </span>
        </div>
      </div>

      {/* Progress slider / Error feedback */}
      <div className="mt-4">
        {job.status === 'failed' ? (
          <div id={`job-error-${job.job_id}`} className="p-3 bg-red-50 rounded-lg text-red-700 text-xs flex items-start gap-2 border border-red-100">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <div className="break-all">
              <span className="font-semibold">Err details: </span>
              {job.error || 'Unknown conversion pipeline process crash.'}
            </div>
          </div>
        ) : (
          <div className="space-y-1.5">
            <div className="flex justify-between items-center text-xs font-medium text-gray-500">
              <span>Progressing</span>
              <span id={`job-progress-txt-${job.job_id}`} className="font-mono">{job.progress}%</span>
            </div>
            <div className="relative w-full h-2 bg-gray-100 rounded-full overflow-hidden">
              <div
                id={`job-progress-bar-${job.job_id}`}
                className={`h-full rounded-full transition-all duration-500 ${
                  job.status === 'completed' ? 'bg-emerald-500' : 'bg-indigo-600'
                }`}
                style={{ width: `${job.progress}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Primary actions */}
      <div className="mt-4 flex justify-end gap-2">
        {job.status === 'completed' && (
          <button
            id={`download-zip-btn-${job.job_id}`}
            onClick={handleDownload}
            className="inline-flex items-center gap-2 text-xs font-semibold px-4 py-2 bg-emerald-600 text-white hover:bg-emerald-700 active:scale-98 rounded-lg shadow-xs transition-all cursor-pointer"
          >
            <Download className="w-3.5 h-3.5" />
            Download Markdown ZIP
          </button>
        )}
        {isCancellable && (
          <button
            id={`cancel-job-btn-${job.job_id}`}
            onClick={handleCancel}
            disabled={isCancelling}
            className="inline-flex items-center gap-2 text-xs font-semibold px-4 py-2 bg-red-600 text-white hover:bg-red-700 disabled:bg-red-400 disabled:cursor-not-allowed active:scale-98 rounded-lg shadow-xs transition-all"
          >
            <X className="w-3.5 h-3.5" />
            {isCancelling ? 'Cancelling...' : 'Cancel Job'}
          </button>
        )}
      </div>
    </div>
  );
};
