import React, { useState, useRef } from 'react';
import { Upload, FileText, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { uploadPdfFile } from '../api';

interface UploadZoneProps {
  onUploadSuccess: () => void;
}

export const UploadZone: React.FC<UploadZoneProps> = ({ onUploadSuccess }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null);
    setSuccess(false);
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      if (!file) return;
      if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
        setError('Only standard educational PDF files (.pdf) are allowed.');
        setSelectedFile(null);
        return;
      }
      setSelectedFile(file);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    setError(null);
    setSuccess(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      if (!file) return;
      if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
        setError('Only standard PDF files are allowed.');
        return;
      }
      setSelectedFile(file);
    }
  };

  const handleZoneClick = () => {
    if (!isUploading && fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || isUploading) return;

    setIsUploading(true);
    setError(null);
    setSuccess(false);

    try {
      await uploadPdfFile(selectedFile);
      setSuccess(true);
      setSelectedFile(null);
      onUploadSuccess(); // triggers parent job list lookup
    } catch (err: any) {
      setError(err.message || 'File upload failed. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="w-full bg-white rounded-xl border border-gray-100 shadow-xs p-6">
      <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
        <Upload className="w-5 h-5 text-indigo-500" />
        Upload PDF Document
      </h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div
          id="dropzone-container"
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={handleZoneClick}
          className={`flex flex-col items-center justify-center border-2 border-dashed rounded-lg p-8 cursor-pointer transition-all ${
            isDragging
              ? 'border-indigo-500 bg-indigo-50/50'
              : selectedFile
              ? 'border-emerald-400 bg-emerald-50/10'
              : 'border-gray-200 hover:border-gray-300 bg-gray-50/20'
          } ${isUploading ? 'pointer-events-none opacity-60' : ''}`}
        >
          <input
            id="pdf-file-input"
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".pdf,application/pdf"
            className="hidden"
          />

          <div className="p-3 bg-white rounded-full shadow-xs border border-gray-50 mb-3 text-gray-400">
            {selectedFile ? (
              <FileText className="w-8 h-8 text-emerald-500" />
            ) : (
              <Upload className="w-8 h-8 text-gray-400" />
            )}
          </div>

          {selectedFile ? (
            <div className="text-center">
              <p className="text-sm font-medium text-gray-800 max-w-xs truncate" title={selectedFile.name}>
                {selectedFile.name}
              </p>
              <p className="text-xs text-gray-400 mt-1">{formatBytes(selectedFile.size)}</p>
            </div>
          ) : (
            <div className="text-center">
              <p className="text-sm font-medium text-gray-600">
                Drag and drop your PDF here, or <span className="text-indigo-600 font-semibold">browse</span>
              </p>
              <p className="text-xs text-gray-400 mt-1">Accepts standard PDF documents up to 50MB</p>
            </div>
          )}
        </div>

        {error && (
          <div id="upload-error-banner" className="flex items-start gap-2 text-sm p-3 bg-red-50 text-red-700 rounded-lg">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <div>
              <p className="font-semibold">Conversion Error</p>
              <p className="text-xs">{error}</p>
            </div>
          </div>
        )}

        {success && (
          <div id="upload-success-banner" className="flex items-center gap-2 text-sm p-3 bg-emerald-50 text-emerald-700 rounded-lg">
            <CheckCircle2 className="w-5 h-5 shrink-0" />
            <p className="font-medium">File successfully submitted and queued for conversion!</p>
          </div>
        )}

        <button
          id="upload-submit-btn"
          type="submit"
          disabled={!selectedFile || isUploading}
          className={`w-full py-2.5 px-4 rounded-lg font-semibold text-sm shadow-xs transition-all flex items-center justify-center gap-2 ${
            selectedFile && !isUploading
              ? 'bg-indigo-600 text-white hover:bg-indigo-700 active:scale-98 cursor-pointer'
              : 'bg-gray-100 text-gray-400 cursor-not-allowed'
          }`}
        >
          {isUploading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Uploading and Parsing...
            </>
          ) : (
            'Start Conversion'
          )}
        </button>
      </form>
    </div>
  );
};
