import React, { useState, useEffect } from 'react';
import {
  Cpu,
  Plus,
  Play,
  Eye,
  CheckCircle,
  AlertTriangle,
  Clock,
  Trash2,
  List,
  FileText,
  FileCode,
  ArrowDown,
  Terminal,
  ShieldCheck,
  RefreshCw,
  X
} from 'lucide-react';
import { api } from '../services/api';
import { Workflow, WorkflowDryRunPreview, WorkflowRun, WorkflowStep } from '../types';

export const AutomationPage: React.FC = () => {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(null);
  const [preview, setPreview] = useState<WorkflowDryRunPreview | null>(null);
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [currentRun, setCurrentRun] = useState<WorkflowRun | null>(null);

  // Form for creating new workflow
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newName, setNewName] = useState('Workspace Data Summary Pipeline');
  const [newDesc, setNewDesc] = useState('Scans workspace text files, transforms summaries with Ollama, and records output.');
  const [templateType, setTemplateType] = useState<'summary' | 'tests' | 'custom'>('summary');

  const loadWorkflows = async () => {
    try {
      const list = await api.listWorkflows();
      setWorkflows(list);
      if (list.length > 0 && !selectedWorkflow) {
        setSelectedWorkflow(list[0]);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const loadRuns = async () => {
    try {
      const r = await api.listWorkflowRuns();
      setRuns(r);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadWorkflows();
    loadRuns();
  }, []);

  const handleCreateWorkflow = async () => {
    try {
      let steps: WorkflowStep[] = [];

      if (templateType === 'summary') {
        steps = [
          {
            id: 'step_1',
            action_type: 'read_files',
            parameters: { folder: '', pattern: '*.txt' },
            require_confirmation: false
          },
          {
            id: 'step_2',
            action_type: 'llm_transform',
            parameters: { prompt: 'Extract key points and format as a bulleted summary.', model: 'gemma4:12b' },
            require_confirmation: false
          },
          {
            id: 'step_3',
            action_type: 'write_file',
            parameters: { output_path: 'automated_summary.txt' },
            require_confirmation: true
          }
        ];
      } else if (templateType === 'tests') {
        steps = [
          {
            id: 'step_1',
            action_type: 'run_test',
            parameters: { test_path: 'backend/tests' },
            require_confirmation: false
          },
          {
            id: 'step_2',
            action_type: 'llm_transform',
            parameters: { prompt: 'Analyze test outputs and produce a health report.', model: 'gemma4:12b' },
            require_confirmation: false
          },
          {
            id: 'step_3',
            action_type: 'write_file',
            parameters: { output_path: 'test_audit_report.md' },
            require_confirmation: false
          }
        ];
      } else {
        steps = [
          {
            id: 'step_1',
            action_type: 'read_files',
            parameters: { folder: '', pattern: '*.py' },
            require_confirmation: false
          },
          {
            id: 'step_2',
            action_type: 'write_file',
            parameters: { output_path: 'custom_pipeline_output.txt' },
            require_confirmation: true
          }
        ];
      }

      const wf = await api.createWorkflow({
        name: newName,
        description: newDesc,
        steps,
        enabled: true
      });

      setShowCreateModal(false);
      await loadWorkflows();
      setSelectedWorkflow(wf);
      setPreview(null);
    } catch (e) {
      console.error(e);
    }
  };

  const handlePreview = async (wf: Workflow) => {
    try {
      const p = await api.previewWorkflow(wf.id);
      setPreview(p);
    } catch (e) {
      console.error(e);
    }
  };

  const handleRun = async (wf: Workflow) => {
    setIsRunning(true);
    setCurrentRun(null);
    try {
      const runRes = await api.runWorkflow(wf.id, true);
      setCurrentRun(runRes);
      loadRuns();
    } catch (err: any) {
      alert(`Workflow execution error: ${err.message}`);
    } finally {
      setIsRunning(false);
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this workflow?')) return;
    try {
      await api.deleteWorkflow(id);
      await loadWorkflows();
      if (selectedWorkflow?.id === id) {
        setSelectedWorkflow(null);
        setPreview(null);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const getActionIcon = (actionType: string) => {
    switch (actionType) {
      case 'read_files': return <FileText size={15} className="text-accent" />;
      case 'llm_transform': return <Cpu size={15} className="text-warning" />;
      case 'write_file': return <FileCode size={15} className="text-success" />;
      default: return <Cpu size={15} className="text-accent" />;
    }
  };

  return (
    <div className="flex h-full overflow-hidden">
      {/* Workflow Definitions Sidebar */}
      <div className="w-80 border-r flex flex-col bg-sidebar overflow-hidden shrink-0">
        <div className="p-3.5 border-b flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Cpu size={16} className="text-accent" />
            <span className="text-xs font-bold text-main uppercase tracking-wider">
              Pipelines ({workflows.length})
            </span>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn btn-primary text-xs py-1 px-2.5 flex items-center gap-1"
          >
            <Plus size={13} />
            <span>New</span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2.5 flex flex-col gap-2">
          {workflows.length === 0 ? (
            <div className="p-8 text-center text-xs text-muted flex flex-col items-center gap-2">
              <Cpu size={24} className="text-dim" />
              <span>No workflows defined. Click "New" to create a pipeline.</span>
            </div>
          ) : (
            workflows.map(wf => {
              const isSelected = selectedWorkflow?.id === wf.id;
              return (
                <div
                  key={wf.id}
                  onClick={() => {
                    setSelectedWorkflow(wf);
                    handlePreview(wf);
                  }}
                  className={`p-3 rounded-xl cursor-pointer border transition text-xs flex flex-col gap-1.5 ${
                    isSelected
                      ? 'bg-card border-accent shadow-sm'
                      : 'bg-panel border-subtle hover:border-main hover:bg-card-hover'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-main truncate pr-2">{wf.name}</span>
                    <button
                      onClick={e => handleDelete(wf.id, e)}
                      title="Delete workflow"
                      className="text-muted hover:text-danger p-1 transition"
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                  <p className="text-2xs text-muted line-clamp-2">{wf.description}</p>
                  <div className="flex items-center justify-between mt-1 pt-1.5 border-t border-subtle text-2xs font-mono text-muted">
                    <span className="badge badge-accent text-2xs">{wf.steps.length} Steps</span>
                    <span className={wf.enabled ? 'text-success font-semibold' : 'text-dim'}>
                      {wf.enabled ? 'ACTIVE' : 'DISABLED'}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Main Workspace Area */}
      <div className="flex-1 flex flex-col h-full bg-canvas overflow-y-auto p-6 gap-6">
        {selectedWorkflow ? (
          <div className="max-w-4xl flex flex-col gap-5">
            {/* Workflow Header Banner */}
            <div className="card p-5 flex items-center justify-between gap-4">
              <div className="flex flex-col gap-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-bold text-main truncate">{selectedWorkflow.name}</h2>
                  <span className={`badge ${selectedWorkflow.enabled ? 'badge-success' : 'badge-danger'}`}>
                    {selectedWorkflow.enabled ? 'ENABLED' : 'PAUSED'}
                  </span>
                </div>
                <p className="text-xs text-muted">{selectedWorkflow.description}</p>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => handlePreview(selectedWorkflow)}
                  className="btn btn-secondary text-xs py-2 px-3 flex items-center gap-1.5"
                >
                  <Eye size={14} />
                  <span>Dry-Run Check</span>
                </button>

                <button
                  onClick={() => handleRun(selectedWorkflow)}
                  disabled={isRunning || !selectedWorkflow.enabled}
                  className="btn btn-primary text-xs py-2 px-4 flex items-center gap-1.5 font-semibold"
                >
                  <Play size={14} className={isRunning ? 'animate-spin' : ''} />
                  <span>{isRunning ? 'Executing Pipeline...' : 'Run Pipeline'}</span>
                </button>
              </div>
            </div>

            {/* Visual Pipeline Steps Flow */}
            <div className="card p-5 flex flex-col gap-4">
              <div className="flex items-center justify-between border-b pb-2.5">
                <span className="text-xs font-bold text-main uppercase tracking-wider">
                  Pipeline Steps Execution Graph
                </span>
                <span className="text-2xs font-mono text-muted">
                  {selectedWorkflow.steps.length} Sequential Steps
                </span>
              </div>

              <div className="flex flex-col gap-2">
                {selectedWorkflow.steps.map((step, idx) => (
                  <React.Fragment key={step.id}>
                    <div className="p-3.5 bg-panel rounded-xl border flex items-center justify-between gap-3 hover:border-main transition">
                      <div className="flex items-center gap-3">
                        <div className="w-7 h-7 rounded-lg bg-card border flex items-center justify-center font-mono text-xs font-bold text-main">
                          {idx + 1}
                        </div>
                        <div className="w-8 h-8 rounded-lg bg-accent-soft flex items-center justify-center">
                          {getActionIcon(step.action_type)}
                        </div>
                        <div className="flex flex-col gap-0.5">
                          <span className="text-xs font-semibold font-mono text-main">
                            {step.action_type}
                          </span>
                          <span className="text-2xs font-mono text-muted">
                            {JSON.stringify(step.parameters)}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        {step.require_confirmation ? (
                          <span className="badge badge-warning text-2xs flex items-center gap-1">
                            <AlertTriangle size={11} /> Confirm Required
                          </span>
                        ) : (
                          <span className="badge badge-success text-2xs flex items-center gap-1">
                            <ShieldCheck size={11} /> Auto Executed
                          </span>
                        )}
                      </div>
                    </div>

                    {idx < selectedWorkflow.steps.length - 1 && (
                      <div className="flex justify-center py-0.5 text-muted">
                        <ArrowDown size={14} />
                      </div>
                    )}
                  </React.Fragment>
                ))}
              </div>
            </div>

            {/* Dry Run Preview Box */}
            {preview && (
              <div className="card p-5 flex flex-col gap-3 border-accent/40 bg-panel">
                <div className="flex items-center justify-between border-b pb-2.5">
                  <div className="flex items-center gap-2">
                    <ShieldCheck size={16} className="text-accent" />
                    <span className="text-xs font-bold uppercase tracking-wider text-main">
                      Dry-Run Security & Path Validation
                    </span>
                  </div>
                  <span className={`badge ${preview.valid ? 'badge-success' : 'badge-danger'}`}>
                    {preview.valid ? 'PASS - ALL CHECKS PASSED' : 'FAIL - PATH ERROR'}
                  </span>
                </div>

                <div className="flex flex-col gap-2">
                  {preview.action_previews.map((step, idx) => (
                    <div key={idx} className="flex items-center gap-3 p-2.5 bg-canvas rounded-lg border text-xs">
                      <span className="w-5 h-5 rounded-full bg-panel border flex items-center justify-center font-mono text-2xs text-muted font-bold">
                        {step.step_index}
                      </span>
                      <span className="font-mono text-accent text-2xs">{step.action_type}</span>
                      <span className="flex-1 text-muted text-xs truncate">{step.summary}</span>
                      {step.requires_confirmation && (
                        <span className="badge badge-warning text-2xs flex items-center gap-1">
                          <AlertTriangle size={10} /> Approval Flagged
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Live Run Audit Logs Console */}
            {currentRun && (
              <div className="card p-5 flex flex-col gap-3">
                <div className="flex items-center justify-between border-b pb-2.5">
                  <div className="flex items-center gap-2">
                    <Terminal size={16} className="text-accent" />
                    <span className="text-xs font-bold uppercase tracking-wider text-main">
                      Live Execution Terminal
                    </span>
                  </div>
                  <span className={`badge ${currentRun.status === 'completed' ? 'badge-success' : 'badge-danger'}`}>
                    {currentRun.status.toUpperCase()} ({currentRun.duration_ms}ms)
                  </span>
                </div>

                <div className="flex flex-col gap-1.5 max-h-64 overflow-y-auto font-mono text-xs p-3 bg-canvas rounded-xl border select-text">
                  {currentRun.logs.map((log, i) => (
                    <div key={i} className="flex gap-2 text-muted hover:text-main">
                      <span className="text-dim text-2xs shrink-0">{new Date(log.timestamp).toLocaleTimeString()}</span>
                      <span className="text-accent font-semibold shrink-0">[{log.step}]</span>
                      <span className="text-main">{log.message}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Past Execution History */}
            <div className="card p-5 flex flex-col gap-3">
              <div className="flex items-center justify-between border-b pb-2.5">
                <span className="text-xs font-bold text-main uppercase tracking-wider">Execution Audit History</span>
                <button
                  onClick={loadRuns}
                  className="btn btn-ghost text-2xs py-1 px-2 flex items-center gap-1"
                >
                  <RefreshCw size={12} />
                  <span>Refresh</span>
                </button>
              </div>

              {runs.length === 0 ? (
                <p className="text-xs text-muted italic py-2">No past pipeline executions recorded.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="border-b border-subtle text-muted text-2xs">
                      <tr>
                        <th className="py-2 px-1">Date & Time</th>
                        <th className="py-2 px-1">Triggered By</th>
                        <th className="py-2 px-1">Status</th>
                        <th className="py-2 px-1">Duration</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-subtle">
                      {runs.slice(0, 6).map(r => (
                        <tr key={r.id} className="hover:bg-card-hover transition">
                          <td className="py-2.5 px-1 text-muted">{new Date(r.created_at).toLocaleString()}</td>
                          <td className="py-2.5 px-1 text-main font-semibold">{r.triggered_by}</td>
                          <td className="py-2.5 px-1">
                            <span className={`badge ${r.status === 'completed' ? 'badge-success' : 'badge-danger'} text-2xs`}>
                              {r.status}
                            </span>
                          </td>
                          <td className="py-2.5 px-1 text-muted">{r.duration_ms}ms</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center gap-2 text-xs text-muted">
            <Cpu size={32} className="text-dim" />
            <span>Select a workflow on the left or create a new automated pipeline.</span>
          </div>
        )}
      </div>

      {/* Create Workflow Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="card max-w-lg w-full p-6 flex flex-col gap-4 bg-card shadow-2xl border">
            <div className="flex items-center justify-between border-b pb-3">
              <h3 className="text-sm font-bold text-main">Create Automation Pipeline</h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-muted hover:text-main p-1 transition"
              >
                <X size={16} />
              </button>
            </div>

            {/* Template Selector */}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-main">Pipeline Template</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setTemplateType('summary');
                    setNewName('Workspace Text Summarizer');
                    setNewDesc('Scans text files, extracts key points with Ollama, writes automated_summary.txt');
                  }}
                  className={`p-3 rounded-xl border text-left flex flex-col gap-1 transition ${
                    templateType === 'summary'
                      ? 'border-accent bg-accent-soft text-main'
                      : 'border-subtle bg-panel text-muted hover:border-main'
                  }`}
                >
                  <span className="text-xs font-bold text-main">Workspace Summary</span>
                  <span className="text-2xs text-muted">Read files → LLM summarize → Save report</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setTemplateType('tests');
                    setNewName('Automated Test & Report');
                    setNewDesc('Runs pytest suite, summarizes failures/passes with Ollama, writes markdown report');
                  }}
                  className={`p-3 rounded-xl border text-left flex flex-col gap-1 transition ${
                    templateType === 'tests'
                      ? 'border-accent bg-accent-soft text-main'
                      : 'border-subtle bg-panel text-muted hover:border-main'
                  }`}
                >
                  <span className="text-xs font-bold text-main">Test & Report</span>
                  <span className="text-2xs text-muted">Run pytest → LLM review → Save audit</span>
                </button>
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-main">Workflow Name</label>
              <input
                type="text"
                value={newName}
                onChange={e => setNewName(e.target.value)}
                className="input-text text-xs"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-main">Description</label>
              <textarea
                value={newDesc}
                onChange={e => setNewDesc(e.target.value)}
                rows={2}
                className="input-textarea text-xs resize-none"
              />
            </div>

            <div className="flex justify-end gap-2 mt-2 pt-3 border-t">
              <button
                onClick={() => setShowCreateModal(false)}
                className="btn btn-secondary text-xs py-2 px-3.5"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateWorkflow}
                className="btn btn-primary text-xs py-2 px-4"
              >
                Create Pipeline
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
