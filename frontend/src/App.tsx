import React, { useState } from 'react';
import { UploadZone } from './components/UploadZone';
import { JobList } from './components/JobList';
import { FileStack, HelpCircle, Hammer, BadgeHelp, CheckCircle } from 'lucide-react';

export const App: React.FC = () => {
  const [refreshTrigger, setRefreshTrigger] = useState<number>(0);

  const triggerRefresh = () => {
    setRefreshTrigger((prev) => prev + 1);
  };

  return (
    <div className="min-h-screen bg-gray-50/50 py-10 px-4 sm:px-6 lg:px-8 font-sans antialiased text-gray-800">
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Header Branding */}
        <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-4 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-600 text-white rounded-xl shadow-md shadow-indigo-200">
              <FileStack className="w-8 h-8" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 tracking-tight">DocPilot</h1>
              <p className="text-xs text-gray-500 font-medium">PDF to Markdown conversion with Visual AI descriptions</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-lg border border-gray-100 text-[11px] font-semibold text-gray-500">
            <Hammer className="w-3.5 h-3.5 text-indigo-500 animate-pulse" />
            <span>Developer Mode Active</span>
          </div>
        </header>

        {/* Feature Highlights Grid */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 bg-white border border-gray-100 rounded-xl space-y-1">
            <h3 className="text-xs font-bold text-indigo-600 uppercase tracking-widest">Acoustic OCR Parsing</h3>
            <p className="text-sm font-semibold text-gray-800">Scanned vs Native</p>
            <p className="text-xs text-gray-400">Autodetects text layouts on the fly, falling back to Tesseract OCR when scans are identified.</p>
          </div>
          <div className="p-4 bg-white border border-gray-100 rounded-xl space-y-1">
            <h3 className="text-xs font-bold text-indigo-600 uppercase tracking-widest">Optical AI Descriptions</h3>
            <p className="text-sm font-semibold text-gray-800">Groq Vision LLM</p>
            <p className="text-xs text-gray-400">Extracts images larger than 300x300, sending visual contexts to Llama 3.2 for descriptions.</p>
          </div>
          <div className="p-4 bg-white border border-gray-100 rounded-xl space-y-1">
            <h3 className="text-xs font-bold text-indigo-600 uppercase tracking-widest">Complete MD Bundles</h3>
            <p className="text-sm font-semibold text-gray-800">ZIP Archives</p>
            <p className="text-xs text-gray-400">Assembles complete page indices, markdown tables, visual layouts, and asset folders inside a single ZIP.</p>
          </div>
        </section>

        {/* Action components layout */}
        <main className="grid grid-cols-1 md:grid-cols-12 gap-6 items-start">
          <div className="md:col-span-5 space-y-6">
            <UploadZone onUploadSuccess={triggerRefresh} />
            
            {/* Guide Card */}
            <div className="bg-indigo-50/50 rounded-xl border border-indigo-100/30 p-5 space-y-2">
              <h4 className="text-xs font-bold text-indigo-700 flex items-center gap-1.5 uppercase tracking-wider">
                <BadgeHelp className="w-4 h-4" />
                Pipeline Stages
              </h4>
              <ul className="text-xs text-indigo-900/80 space-y-1.5 list-disc pl-4 leading-relaxed">
                <li><strong className="text-indigo-900">parsing:</strong> Evaluates native layouts. Fallback to full OCR rastering.</li>
                <li><strong className="text-indigo-900">extracting_images:</strong> pdfimages maps embed files & filters shapes.</li>
                <li><strong className="text-indigo-900">describing_images:</strong> Runs vision calls to formulate blockquotes.</li>
                <li><strong className="text-indigo-900">writing:</strong> Builds YAML frontend & compile.</li>
              </ul>
            </div>
          </div>
          
          <div className="md:col-span-7">
            <JobList refreshTrigger={refreshTrigger} />
          </div>
        </main>
        
        <footer className="text-center text-[11px] text-gray-400 py-6">
          DocPilot Internal Productivity Suite — Local Sandbox Environment
        </footer>
      </div>
    </div>
  );
};

export default App;
