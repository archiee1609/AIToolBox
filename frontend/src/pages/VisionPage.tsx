import React, { useState, useRef } from 'react';
import {
  Eye,
  Upload,
  Sparkles,
  Bot,
  AlertTriangle,
  CheckCircle,
  Copy,
  Check,
  Trash2,
  ZoomIn,
  X,
  FileCode,
  FileText,
  Layers,
  ArrowRight
} from 'lucide-react';
import { api } from '../services/api';
import { ModelDetails } from '../types';
import { MarkdownRenderer } from '../components/MarkdownRenderer';

interface VisionPageProps {
  selectedModel: string;
  setSelectedModel: (model: string) => void;
  models: ModelDetails[];
}

const PRESET_PROMPTS = [
  { label: 'Describe Scene', text: 'Describe this image in detail, listing all key objects, setting, colors, and spatial composition.' },
  { label: 'Extract Text (OCR)', text: 'Extract and transcribe all readable text, signs, labels, numbers, and code visible in this image verbatim.' },
  { label: 'UI / UX Audit', text: 'Analyze the UI design, visual hierarchy, typography, component layout, and usability of this interface screenshot.' },
  { label: 'Code & Error Debug', text: 'Inspect any code, terminal output, or stack traces visible in this screenshot, identify any bugs or errors, and suggest fixes.' }
];

export const VisionPage: React.FC<VisionPageProps> = ({
  selectedModel,
  setSelectedModel,
  models
}) => {
  const [imageData, setImageData] = useState<string | null>(null);
  const [imageMeta, setImageMeta] = useState<{ name: string; size: number; type: string } | null>(null);
  const [prompt, setPrompt] = useState('Describe this image in detail and list all objects and text visible.');
  const [analysisResult, setAnalysisResult] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [isZoomed, setIsZoomed] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Check if current model supports vision
  const currentModelDetails = models.find(m => m.name === selectedModel);
  const isVisionCapable = currentModelDetails?.capabilities?.image_understanding ?? false;

  // Find a vision model (e.g. gemma4:12b)
  const visionModel = models.find(m => m.capabilities?.image_understanding)?.name || 'gemma4:12b';

  const processFile = (file: File) => {
    if (!file.type.startsWith('image/')) {
      setErrorMsg('Please select a valid image file (JPEG, PNG, WEBP, GIF).');
      return;
    }

    if (file.size > 25 * 1024 * 1024) {
      setErrorMsg('Image size exceeds 25MB limit.');
      return;
    }

    setErrorMsg(null);
    setImageMeta({ name: file.name, size: file.size, type: file.type });

    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === 'string') {
        setImageData(reader.result);
      }
    };
    reader.readAsDataURL(file);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) processFile(file);
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    const items = e.clipboardData.items;
    for (let i = 0; i < items.length; i++) {
      if (items[i].type.indexOf('image') !== -1) {
        const file = items[i].getAsFile();
        if (file) {
          processFile(file);
          break;
        }
      }
    }
  };

  const handleAnalyze = async () => {
    if (!imageData) return;
    setIsAnalyzing(true);
    setErrorMsg(null);
    setAnalysisResult(null);

    try {
      const res = await api.analyzeVision(imageData, prompt, selectedModel);
      if (!res.capability_supported) {
        setErrorMsg(res.response);
      } else {
        setAnalysisResult(res.response);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Vision analysis failed.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleCopy = () => {
    if (!analysisResult) return;
    navigator.clipboard.writeText(analysisResult);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleClearImage = () => {
    setImageData(null);
    setImageMeta(null);
    setAnalysisResult(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div
      onPaste={handlePaste}
      className="flex-1 flex flex-col h-full bg-canvas overflow-y-auto p-6"
    >
      <div className="max-w-5xl mx-auto w-full flex flex-col gap-5">
        {/* Capability Banner */}
        {!isVisionCapable && (
          <div className="card p-4 flex items-center justify-between border-warning" style={{ background: 'rgba(245, 158, 11, 0.08)' }}>
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center text-warning" style={{ background: 'rgba(245, 158, 11, 0.15)' }}>
                <AlertTriangle size={18} />
              </div>
              <div>
                <p className="text-xs font-semibold text-main">Model Vision Limitation</p>
                <p className="text-xs text-muted">
                  The selected model <span className="font-mono text-main font-semibold">[{selectedModel}]</span> does not support visual inputs.
                </p>
              </div>
            </div>
            {visionModel && (
              <button
                onClick={() => setSelectedModel(visionModel)}
                className="btn btn-primary text-xs py-1.5 px-3 whitespace-nowrap flex items-center gap-1.5"
              >
                <span>Switch to {visionModel}</span>
                <ArrowRight size={13} />
              </button>
            )}
          </div>
        )}

        {/* Workspace Layout: Split Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {/* Left Column: Image Input */}
          <div className="card p-4 flex flex-col gap-3">
            <div className="flex items-center justify-between border-b pb-2.5">
              <div className="flex items-center gap-2">
                <Eye size={16} className="text-accent" />
                <span className="text-xs font-bold text-main uppercase tracking-wider">Image Input</span>
              </div>
              {imageMeta && (
                <div className="flex items-center gap-2">
                  <span className="badge badge-accent">
                    {(imageMeta.size / 1024).toFixed(1)} KB
                  </span>
                  <button
                    onClick={handleClearImage}
                    title="Remove image"
                    className="text-muted hover:text-danger transition p-1"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              )}
            </div>

            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              accept="image/*"
              className="hidden"
            />

            {imageData ? (
              <div className="relative group rounded-xl overflow-hidden border bg-canvas flex items-center justify-center min-h-[300px] max-h-[360px]">
                <img
                  src={imageData}
                  alt="Visual target"
                  className="max-h-[340px] w-auto max-w-full object-contain p-2"
                />

                {/* Floating overlay actions */}
                <div className="absolute bottom-3 right-3 flex items-center gap-2 opacity-90 group-hover:opacity-100 transition">
                  <button
                    onClick={() => setIsZoomed(true)}
                    className="btn btn-secondary text-xs py-1.5 px-2.5 flex items-center gap-1 shadow-md backdrop-blur"
                  >
                    <ZoomIn size={13} />
                    <span>Zoom</span>
                  </button>
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="btn btn-secondary text-xs py-1.5 px-2.5 flex items-center gap-1 shadow-md backdrop-blur"
                  >
                    <Upload size={13} />
                    <span>Change</span>
                  </button>
                </div>

                {imageMeta && (
                  <div className="absolute top-3 left-3 bg-canvas/80 backdrop-blur border text-[11px] font-mono px-2 py-1 rounded-md text-muted truncate max-w-[200px]">
                    {imageMeta.name}
                  </div>
                )}
              </div>
            ) : (
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center gap-3 cursor-pointer transition text-center min-h-[300px] ${
                  isDragging
                    ? 'border-accent bg-accent-soft'
                    : 'border-subtle hover:border-accent bg-panel hover:bg-card-hover'
                }`}
              >
                <div className="w-12 h-12 rounded-xl bg-accent-soft border border-accent/20 flex items-center justify-center text-accent">
                  <Upload size={22} />
                </div>
                <div>
                  <p className="text-xs font-semibold text-main">Click to browse or drop an image</p>
                  <p className="text-xs text-muted mt-1">Or paste directly from clipboard (Ctrl+V)</p>
                  <p className="text-2xs text-dim font-mono mt-2">JPEG, PNG, WEBP, GIF (Max 25MB)</p>
                </div>
              </div>
            )}
          </div>

          {/* Right Column: Prompt & Controls */}
          <div className="card p-4 flex flex-col gap-3">
            <div className="flex items-center justify-between border-b pb-2.5">
              <span className="text-xs font-bold text-main uppercase tracking-wider">Analysis Prompt</span>
              <span className="text-2xs font-mono text-muted">Model: {selectedModel}</span>
            </div>

            {/* Quick Prompt Presets */}
            <div className="flex flex-wrap gap-1.5">
              {PRESET_PROMPTS.map((p, idx) => (
                <button
                  key={idx}
                  onClick={() => setPrompt(p.text)}
                  className={`text-2xs px-2.5 py-1 rounded-md border transition font-medium ${
                    prompt === p.text
                      ? 'bg-accent text-white border-accent'
                      : 'bg-panel text-muted border-subtle hover:text-main hover:border-main'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>

            <textarea
              value={prompt}
              onChange={e => setPrompt(e.target.value)}
              placeholder="What would you like the model to analyze in this image?"
              rows={6}
              className="input-textarea text-xs resize-none"
            />

            <button
              onClick={handleAnalyze}
              disabled={!imageData || isAnalyzing}
              className="btn btn-primary flex items-center justify-center gap-2 py-2.5 text-xs font-semibold mt-auto"
            >
              <Sparkles size={16} className={isAnalyzing ? 'animate-spin' : ''} />
              <span>{isAnalyzing ? 'Analyzing Image...' : 'Analyze with Vision Model'}</span>
            </button>

            {errorMsg && (
              <div className="p-3 bg-danger-soft border border-danger/30 rounded-lg text-xs text-danger flex items-start gap-2">
                <AlertTriangle size={15} className="shrink-0 mt-0.5" />
                <span>{errorMsg}</span>
              </div>
            )}
          </div>
        </div>

        {/* Analysis Output Section */}
        {analysisResult && (
          <div className="card p-5 flex flex-col gap-3">
            <div className="flex items-center justify-between border-b pb-3">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-md bg-accent-soft flex items-center justify-center text-accent">
                  <Bot size={14} />
                </div>
                <span className="text-xs font-bold uppercase tracking-wider text-main">Vision Insights & Analysis</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-2xs font-mono text-muted">{selectedModel}</span>
                <button
                  onClick={handleCopy}
                  className="btn btn-secondary text-2xs py-1 px-2.5 flex items-center gap-1"
                >
                  {copied ? <Check size={12} className="text-success" /> : <Copy size={12} />}
                  <span>{copied ? 'Copied' : 'Copy'}</span>
                </button>
              </div>
            </div>

            <div className="p-4 bg-canvas rounded-xl border select-text">
              <MarkdownRenderer content={analysisResult} />
            </div>
          </div>
        )}
      </div>

      {/* Image Lightbox Modal */}
      {isZoomed && imageData && (
        <div
          onClick={() => setIsZoomed(false)}
          className="fixed inset-0 bg-black/85 backdrop-blur-md flex items-center justify-center p-6 z-50 cursor-pointer"
        >
          <div className="relative max-w-5xl max-h-[90vh] flex items-center justify-center" onClick={e => e.stopPropagation()}>
            <img
              src={imageData}
              alt="Zoomed Target"
              className="max-h-[85vh] max-w-[90vw] object-contain rounded-xl shadow-2xl border"
            />
            <button
              onClick={() => setIsZoomed(false)}
              className="absolute -top-3 -right-3 w-8 h-8 rounded-full bg-card border flex items-center justify-center text-main hover:text-danger shadow-lg transition"
            >
              <X size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
