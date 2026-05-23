import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import React, { useState, useRef } from 'react';
import { Upload, FileText, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { uploadPdfFile } from '../api';
export const UploadZone = ({ onUploadSuccess }) => {
    const [selectedFile, setSelectedFile] = useState(null);
    const [isDragging, setIsDragging] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(false);
    const fileInputRef = useRef(null);
    const formatBytes = (bytes) => {
        if (bytes === 0)
            return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };
    const handleFileChange = (e) => {
        setError(null);
        setSuccess(false);
        if (e.target.files && e.target.files.length > 0) {
            const file = e.target.files[0];
            if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
                setError('Only standard educational PDF files (.pdf) are allowed.');
                setSelectedFile(null);
                return;
            }
            setSelectedFile(file);
        }
    };
    const handleDragOver = (e) => {
        e.preventDefault();
        setIsDragging(true);
    };
    const handleDragLeave = () => {
        setIsDragging(false);
    };
    const handleDrop = (e) => {
        e.preventDefault();
        setIsDragging(false);
        setError(null);
        setSuccess(false);
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            const file = e.dataTransfer.files[0];
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
    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!selectedFile || isUploading)
            return;
        setIsUploading(true);
        setError(null);
        setSuccess(false);
        try {
            await uploadPdfFile(selectedFile);
            setSuccess(true);
            setSelectedFile(null);
            onUploadSuccess(); // triggers parent job list lookup
        }
        catch (err) {
            setError(err.message || 'File upload failed. Please try again.');
        }
        finally {
            setIsUploading(false);
        }
    };
    return (_jsxs("div", { className: "w-full bg-white rounded-xl border border-gray-100 shadow-xs p-6", children: [_jsxs("h2", { className: "text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2", children: [_jsx(Upload, { className: "w-5 h-5 text-indigo-500" }), "Upload PDF Document"] }), _jsxs("form", { onSubmit: handleSubmit, className: "space-y-4", children: [_jsxs("div", { id: "dropzone-container", onDragOver: handleDragOver, onDragLeave: handleDragLeave, onDrop: handleDrop, onClick: handleZoneClick, className: `flex flex-col items-center justify-center border-2 border-dashed rounded-lg p-8 cursor-pointer transition-all ${isDragging
                            ? 'border-indigo-500 bg-indigo-50/50'
                            : selectedFile
                                ? 'border-emerald-400 bg-emerald-50/10'
                                : 'border-gray-200 hover:border-gray-300 bg-gray-50/20'} ${isUploading ? 'pointer-events-none opacity-60' : ''}`, children: [_jsx("input", { id: "pdf-file-input", type: "file", ref: fileInputRef, onChange: handleFileChange, accept: ".pdf,application/pdf", className: "hidden" }), _jsx("div", { className: "p-3 bg-white rounded-full shadow-xs border border-gray-50 mb-3 text-gray-400", children: selectedFile ? (_jsx(FileText, { className: "w-8 h-8 text-emerald-500" })) : (_jsx(Upload, { className: "w-8 h-8 text-gray-400" })) }), selectedFile ? (_jsxs("div", { className: "text-center", children: [_jsx("p", { className: "text-sm font-medium text-gray-800 max-w-xs truncate", title: selectedFile.name, children: selectedFile.name }), _jsx("p", { className: "text-xs text-gray-400 mt-1", children: formatBytes(selectedFile.size) })] })) : (_jsxs("div", { className: "text-center", children: [_jsxs("p", { className: "text-sm font-medium text-gray-600", children: ["Drag and drop your PDF here, or ", _jsx("span", { className: "text-indigo-600 font-semibold", children: "browse" })] }), _jsx("p", { className: "text-xs text-gray-400 mt-1", children: "Accepts standard PDF documents up to 50MB" })] }))] }), error && (_jsxs("div", { id: "upload-error-banner", className: "flex items-start gap-2 text-sm p-3 bg-red-50 text-red-700 rounded-lg", children: [_jsx(AlertCircle, { className: "w-5 h-5 shrink-0" }), _jsxs("div", { children: [_jsx("p", { className: "font-semibold", children: "Conversion Error" }), _jsx("p", { className: "text-xs", children: error })] })] })), success && (_jsxs("div", { id: "upload-success-banner", className: "flex items-center gap-2 text-sm p-3 bg-emerald-50 text-emerald-700 rounded-lg", children: [_jsx(CheckCircle2, { className: "w-5 h-5 shrink-0" }), _jsx("p", { className: "font-medium", children: "File successfully submitted and queued for conversion!" })] })), _jsx("button", { id: "upload-submit-btn", type: "submit", disabled: !selectedFile || isUploading, className: `w-full py-2.5 px-4 rounded-lg font-semibold text-sm shadow-xs transition-all flex items-center justify-center gap-2 ${selectedFile && !isUploading
                            ? 'bg-indigo-600 text-white hover:bg-indigo-700 active:scale-98 cursor-pointer'
                            : 'bg-gray-100 text-gray-400 cursor-not-allowed'}`, children: isUploading ? (_jsxs(_Fragment, { children: [_jsx(Loader2, { className: "w-4 h-4 animate-spin" }), "Uploading and Parsing..."] })) : ('Start Conversion') })] })] }));
};
//# sourceMappingURL=UploadZone.js.map