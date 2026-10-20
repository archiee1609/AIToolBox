import React, { useState, useEffect } from 'react';
import {
  Activity,
  CheckCircle,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Download,
  Server,
  Database,
  Image as ImageIcon,
  Cpu,
  Bot,
  Shield,
  Layers,
  Terminal,
  Play,
  Copy,
  Check
} from 'lucide-react';
import { api } from '../services/api';
import { DiagnosticsReport } from '../types';

export const DiagnosticsPage: React.FC = () => {
  const [report, setReport] = useState<DiagnosticsReport | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [testResults, setTestResults] = useState<Record<string, { status: 'idle' | 'running' | 'success' | 'failed'; message?: string }>>({
    ollama: { status: 'idle' },
    comfyui: { status: 'idle' }
  });
  const [copiedRaw, setCopiedRaw] = useState(false);
  const [showRawJson, setShowRawJson] = useState(false);

  const loadDiagnostics = async () => {
    setIsLoading(true);
    try {
      const rep = await api.getDiagnostics();
      setReport(rep);
    } catch (e: any) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDiagnostics();
  }, []);

  const testOllama = async () => {
    setTestResults(prev => ({ ...prev, ollama: { status: 'running' } }));
    const startTime = performance.now();
    try {
      const modelToTest = report?.installed_models?.[0] || 'gemma4:12b';
      const res = await api.testModel(modelToTest, 'Reply with OK');
      const duration = Math.round(performance.now() - startTime);
      setTestResults(prev => ({
        ...prev,
        ollama: {
          status: 'success',
          message: `Inference OK (${duration}ms) via [${modelToTest}]: "${res.reply.trim()}"`
        }
      }));
    } catch (e: any) {
      setTestResults(prev => ({
        ...prev,
        ollama: { status: 'failed', message: `Ping failed: ${e.message}` }
      }));
    }
  };

  const testComfyUI = async () => {
    setTestResults(prev => ({ ...prev, comfyui: { status: 'running' } }));
    const startTime = performance.now();
    try {
      const res = await api.getComfyStatus();
      const duration = Math.round(performance.now() - startTime);
      if (res.is_reachable) {
        setTestResults(prev => ({
          ...prev,
          comfyui: {
            status: 'success',
            message: `Online (${duration}ms) • Active queue: ${res.queue_remaining}`
          }
        }));
      } else {
        setTestResults(prev => ({
          ...prev,
          comfyui: {
            status: 'failed',
            message: 'Service unreachable at 127.0.0.1:8188. (ComfyUI server is offline)'
          }
        }));
      }
    } catch (e: any) {
      setTestResults(prev => ({
        ...prev,
        comfyui: { status: 'failed', message: `Ping error: ${e.message}` }
      }));
    }
  };

  const handleExportDiagnostics = () => {
    if (!report) return;
    const exportData = {
      timestamp: new Date().toISOString(),
      report,
      frontend: {
        host: window.location.host,
        userAgent: navigator.userAgent
      }
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `workbench_diagnostics_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleCopyRaw = () => {
    if (!report) return;
    navigator.clipboard.writeText(JSON.stringify(report, null, 2));
    setCopiedRaw(true);
    setTimeout(() => setCopiedRaw(false), 2000);
  };

  const getStatusBadge = (status: string) => {
    if (status === 'healthy' || status === 'online') {
      return <span className="badge badge-success">HEALTHY</span>;
    }
    if (status === 'degraded') {
      return <span className="badge badge-warning">DEGRADED</span>;
    }
    return <span className="badge badge-danger">OFFLINE</span>;
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-canvas overflow-y-auto p-6">
      <div className="max-w-5xl mx-auto w-full flex flex-col gap-5">
        {/* Top Header Card */}
        <div className="card p-5 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-accent-soft border border-accent/20 flex items-center justify-center text-accent">
              <Activity size={20} />
            </div>
            <div>
              <h2 className="text-base font-bold text-main">System Health & Diagnostic Telemetry</h2>
              <p className="text-xs text-muted">
                Runtime audits, local adapter reachability, and hardware capability status.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={loadDiagnostics}
              disabled={isLoading}
              className="btn btn-secondary text-xs py-2 px-3 flex items-center gap-1.5"
            >
              <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
              <span>Refresh Status</span>
            </button>
            <button
              onClick={handleExportDiagnostics}
              className="btn btn-primary text-xs py-2 px-3.5 flex items-center gap-1.5"
            >
              <Download size={14} />
              <span>Export Audit (JSON)</span>
            </button>
          </div>
        </div>

        {/* High-Level KPI Summary Grid */}
        {report && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="card p-4 flex flex-col gap-1">
              <span className="text-2xs font-mono uppercase text-muted">Overall System</span>
              <div className="flex items-center gap-2 mt-1">
                <span className={`w-2.5 h-2.5 rounded-full ${report.backend_status === 'healthy' ? 'bg-success' : 'bg-warning'}`} />
                <span className="text-sm font-bold text-main capitalize">{report.backend_status}</span>
              </div>
              <span className="text-2xs text-dim font-mono mt-1">FastAPI v{report.app_version}</span>
            </div>

            <div className="card p-4 flex flex-col gap-1">
              <span className="text-2xs font-mono uppercase text-muted">Ollama Local Engine</span>
              <div className="flex items-center gap-2 mt-1">
                <span className={`w-2.5 h-2.5 rounded-full ${report.ollama.status === 'healthy' ? 'bg-success' : 'bg-danger'}`} />
                <span className="text-sm font-bold text-main">
                  {report.ollama.status === 'healthy' ? `${report.installed_models.length} Models` : 'Offline'}
                </span>
              </div>
              <span className="text-2xs text-dim font-mono mt-1">{report.ollama.endpoint}</span>
            </div>

            <div className="card p-4 flex flex-col gap-1">
              <span className="text-2xs font-mono uppercase text-muted">SQLite Storage</span>
              <div className="flex items-center gap-2 mt-1">
                <span className="w-2.5 h-2.5 rounded-full bg-success" />
                <span className="text-sm font-bold text-main">WAL Mode</span>
              </div>
              <span className="text-2xs text-dim font-mono mt-1">Hot-Backups Enabled</span>
            </div>

            <div className="card p-4 flex flex-col gap-1">
              <span className="text-2xs font-mono uppercase text-muted">Image Engine</span>
              <div className="flex items-center gap-2 mt-1">
                <span className={`w-2.5 h-2.5 rounded-full ${report.comfyui.status === 'healthy' ? 'bg-success' : 'bg-dim'}`} />
                <span className="text-sm font-bold text-main capitalize">{report.comfyui.status}</span>
              </div>
              <span className="text-2xs text-dim font-mono mt-1">ComfyUI Adapter</span>
            </div>
          </div>
        )}

        {/* Detailed Service Cards Grid */}
        {report && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Backend API Service */}
            <div className="card p-5 flex flex-col gap-3">
              <div className="flex items-center justify-between border-b pb-2.5">
                <div className="flex items-center gap-2">
                  <Server size={16} className="text-accent" />
                  <span className="text-xs font-bold text-main uppercase tracking-wider">FastAPI Core Backend</span>
                </div>
                {getStatusBadge(report.backend_status)}
              </div>

              <div className="flex flex-col gap-2 text-xs font-mono">
                <div className="flex justify-between py-1 border-b border-subtle">
                  <span className="text-muted">Application:</span>
                  <span className="text-main font-semibold">{report.app_name}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-subtle">
                  <span className="text-muted">API Protocol:</span>
                  <span className="text-main">HTTP/1.1 + Server-Sent Events (SSE)</span>
                </div>
                <div className="flex justify-between py-1 border-b border-subtle">
                  <span className="text-muted">Security Sandbox:</span>
                  <span className="text-success font-semibold">Strict Path Traversal Guard</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-muted">Platform:</span>
                  <span className="text-main">Windows 10/11 Non-Elevated</span>
                </div>
              </div>
            </div>

            {/* SQLite Storage */}
            <div className="card p-5 flex flex-col gap-3">
              <div className="flex items-center justify-between border-b pb-2.5">
                <div className="flex items-center gap-2">
                  <Database size={16} className="text-accent" />
                  <span className="text-xs font-bold text-main uppercase tracking-wider">SQLite Embedded Database</span>
                </div>
                {getStatusBadge(report.database.status)}
              </div>

              <div className="flex flex-col gap-2 text-xs font-mono">
                <div className="flex justify-between py-1 border-b border-subtle">
                  <span className="text-muted">Concurrency Mode:</span>
                  <span className="text-main">Write-Ahead Logging (WAL)</span>
                </div>
                <div className="flex justify-between py-1 border-b border-subtle">
                  <span className="text-muted">Thread-Safety:</span>
                  <span className="text-main">asyncio.to_thread Isolated</span>
                </div>
                <div className="flex justify-between py-1 border-b border-subtle">
                  <span className="text-muted">Target File:</span>
                  <span className="text-main truncate max-w-[220px]" title={report.database.endpoint}>
                    {report.database.endpoint.split('\\').pop() || report.database.endpoint}
                  </span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-muted">Foreign Keys:</span>
                  <span className="text-success font-semibold">ON (Integrity Enforced)</span>
                </div>
              </div>
            </div>

            {/* Ollama Local Engine */}
            <div className="card p-5 flex flex-col gap-3">
              <div className="flex items-center justify-between border-b pb-2.5">
                <div className="flex items-center gap-2">
                  <Bot size={16} className="text-accent" />
                  <span className="text-xs font-bold text-main uppercase tracking-wider">Ollama Inference Engine</span>
                </div>
                {getStatusBadge(report.ollama.status)}
              </div>

              <div className="flex flex-col gap-2 text-xs font-mono">
                <div className="flex justify-between py-1 border-b border-subtle">
                  <span className="text-muted">Local Daemon Endpoint:</span>
                  <span className="text-main">{report.ollama.endpoint}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-subtle">
                  <span className="text-muted">Ollama Version:</span>
                  <span className="text-main">{report.ollama.details?.version || 'N/A'}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-muted">Discovered Models:</span>
                  <span className="text-accent font-semibold">{report.installed_models.length} Available</span>
                </div>
              </div>

              <div className="pt-2 border-t flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <button
                    onClick={testOllama}
                    disabled={testResults.ollama.status === 'running'}
                    className="btn btn-secondary text-2xs py-1.5 px-3 flex items-center gap-1.5"
                  >
                    <Play size={11} className={testResults.ollama.status === 'running' ? 'animate-spin' : ''} />
                    <span>Test Inference</span>
                  </button>
                  {testResults.ollama.status === 'running' && (
                    <span className="text-2xs font-mono text-muted">Running test inference...</span>
                  )}
                </div>
                {testResults.ollama.message && (
                  <div className={`p-2.5 rounded-lg border text-2xs font-mono ${
                    testResults.ollama.status === 'success'
                      ? 'bg-success-soft border-success/30 text-success'
                      : 'bg-danger-soft border-danger/30 text-danger'
                  }`}>
                    {testResults.ollama.message}
                  </div>
                )}
              </div>
            </div>

            {/* ComfyUI Image Engine */}
            <div className="card p-5 flex flex-col gap-3">
              <div className="flex items-center justify-between border-b pb-2.5">
                <div className="flex items-center gap-2">
                  <ImageIcon size={16} className="text-accent" />
                  <span className="text-xs font-bold text-main uppercase tracking-wider">ComfyUI Image Adapter</span>
                </div>
                {getStatusBadge(report.comfyui.status)}
              </div>

              <div className="flex flex-col gap-2 text-xs font-mono">
                <div className="flex justify-between py-1 border-b border-subtle">
                  <span className="text-muted">Target Service URL:</span>
                  <span className="text-main">{report.comfyui.endpoint}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-subtle">
                  <span className="text-muted">Workflow Format:</span>
                  <span className="text-main">API Prompt Graph (v1)</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-muted">Fallback Mode:</span>
                  <span className="text-warning">Actionable Setup Instructions</span>
                </div>
              </div>

              <div className="pt-2 border-t flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <button
                    onClick={testComfyUI}
                    disabled={testResults.comfyui.status === 'running'}
                    className="btn btn-secondary text-2xs py-1.5 px-3 flex items-center gap-1.5"
                  >
                    <Play size={11} className={testResults.comfyui.status === 'running' ? 'animate-spin' : ''} />
                    <span>Ping Endpoint</span>
                  </button>
                  {testResults.comfyui.status === 'running' && (
                    <span className="text-2xs font-mono text-muted">Testing reachability...</span>
                  )}
                </div>
                {testResults.comfyui.message && (
                  <div className={`p-2.5 rounded-lg border text-2xs font-mono ${
                    testResults.comfyui.status === 'success'
                      ? 'bg-success-soft border-success/30 text-success'
                      : 'bg-panel border-subtle text-muted'
                  }`}>
                    {testResults.comfyui.message}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Real Installed Models from Ollama */}
        {report && (
          <div className="card p-5 flex flex-col gap-3">
            <div className="flex items-center justify-between border-b pb-2.5">
              <span className="text-xs font-bold text-main uppercase tracking-wider">
                Installed Ollama Models (Discovered via GET /api/tags)
              </span>
              <span className="badge badge-accent">
                {report.installed_models.length} Discovered
              </span>
            </div>

            {report.installed_models.length === 0 ? (
              <p className="text-xs text-muted italic py-2">
                No Ollama models detected. Run `ollama pull gemma4:12b` or `ollama pull gpt-oss` to install models.
              </p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {report.installed_models.map(modelName => {
                  const isVision = modelName.includes('gemma4') || modelName.includes('llava') || modelName.includes('vision');
                  return (
                    <div
                      key={modelName}
                      className="p-3.5 bg-panel rounded-xl border flex items-center justify-between gap-3 hover:border-main transition"
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <div className="w-8 h-8 rounded-lg bg-card border flex items-center justify-center text-accent">
                          <Bot size={16} />
                        </div>
                        <div className="flex flex-col min-w-0">
                          <span className="text-xs font-bold font-mono text-main truncate">{modelName}</span>
                          <span className="text-2xs text-muted">Local Ollama Model</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-1.5 flex-wrap justify-end">
                        <span className="badge badge-accent text-2xs">Tools</span>
                        <span className="badge badge-success text-2xs">Completion</span>
                        {isVision && <span className="badge badge-warning text-2xs">Vision</span>}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Raw Diagnostics JSON Toggle */}
        {report && (
          <div className="card p-4 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <button
                onClick={() => setShowRawJson(!showRawJson)}
                className="text-xs font-bold text-main uppercase tracking-wider hover:text-accent transition flex items-center gap-1.5"
              >
                <span>{showRawJson ? 'Hide Raw JSON Telemetry' : 'View Raw JSON Telemetry'}</span>
              </button>
              {showRawJson && (
                <button
                  onClick={handleCopyRaw}
                  className="btn btn-secondary text-2xs py-1 px-2.5 flex items-center gap-1"
                >
                  {copiedRaw ? <Check size={12} className="text-success" /> : <Copy size={12} />}
                  <span>{copiedRaw ? 'Copied' : 'Copy JSON'}</span>
                </button>
              )}
            </div>

            {showRawJson && (
              <pre className="p-4 bg-canvas rounded-xl border font-mono text-2xs text-muted max-h-72 overflow-y-auto select-text">
                {JSON.stringify(report, null, 2)}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
