import React, { useState, useEffect } from 'react';
import {
  Wrench,
  Play,
  CheckCircle2,
  AlertCircle,
  Clock,
  Shield,
  Globe,
  Terminal,
  Folder,
  Calculator,
  FileText,
  Sparkles,
  Search
} from 'lucide-react';
import { api } from '../services/api';
import { ToolDefinition, ToolExecutionResponse } from '../types';

export const ToolsPage: React.FC = () => {
  const [tools, setTools] = useState<ToolDefinition[]>([]);
  const [selectedTool, setSelectedTool] = useState<ToolDefinition | null>(null);
  const [paramInputs, setParamInputs] = useState<Record<string, string>>({});
  const [executionResult, setExecutionResult] = useState<ToolExecutionResponse | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [history, setHistory] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    api.listTools().then(list => {
      setTools(list);
      if (list.length > 0) {
        handleToolSelect(list[0]);
      }
    }).catch(console.error);

    loadHistory();
  }, []);

  const loadHistory = () => {
    api.getToolHistory().then(setHistory).catch(console.error);
  };

  const handleToolSelect = (tool: ToolDefinition) => {
    setSelectedTool(tool);
    setExecutionResult(null);
    const defaults: Record<string, string> = {};
    if (tool.parameters?.properties) {
      Object.keys(tool.parameters.properties).forEach(k => {
        if (k === 'expression') defaults[k] = '25 * 4 + 15';
        else if (k === 'path') defaults[k] = 'README.md';
        else if (k === 'pattern') defaults[k] = '*.py';
        else if (k === 'content') defaults[k] = '# Generated from AI Tools';
        else if (k === 'json_string') defaults[k] = '{"service": "workbench", "status": "active"}';
        else if (k === 'test_framework') defaults[k] = 'pytest';
        else defaults[k] = '';
      });
    }
    setParamInputs(defaults);
  };

  const handleExecute = async () => {
    if (!selectedTool) return;
    setIsExecuting(true);
    setExecutionResult(null);
    try {
      const parsedArgs: Record<string, any> = {};
      Object.entries(paramInputs).forEach(([k, v]) => {
        try {
          if (v.startsWith('{') || v.startsWith('[')) {
            parsedArgs[k] = JSON.parse(v);
          } else {
            parsedArgs[k] = v;
          }
        } catch {
          parsedArgs[k] = v;
        }
      });

      const res = await api.executeTool(selectedTool.name, parsedArgs, true);
      setExecutionResult(res);
      loadHistory();
    } catch (err: any) {
      setExecutionResult({
        tool_name: selectedTool.name,
        status: 'error',
        error: err.message || 'Execution failed',
        execution_time_ms: 0
      });
    } finally {
      setIsExecuting(false);
    }
  };

  const filteredTools = tools.filter(t =>
    t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    t.category.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex h-full overflow-hidden" style={{ backgroundColor: 'var(--bg-canvas)' }}>
      {/* Tool Browser Sidebar */}
      <div
        className="flex flex-col border-r select-none"
        style={{
          width: '280px',
          backgroundColor: 'var(--bg-sidebar)',
          borderColor: 'var(--border-subtle)'
        }}
      >
        <div className="p-3 border-b border-subtle flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="text-2xs font-bold font-mono uppercase tracking-wider text-muted">
              Registry ({tools.length})
            </span>
          </div>
          <div className="relative">
            <Search size={13} className="absolute left-2.5 top-2.5 text-dim pointer-events-none" />
            <input
              type="text"
              placeholder="Filter tools..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="input-text text-2xs pl-8 py-1 font-mono"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-1.5 flex flex-col gap-1">
          {filteredTools.map(tool => {
            const isSelected = selectedTool?.name === tool.name;
            return (
              <div
                key={tool.name}
                onClick={() => handleToolSelect(tool)}
                className={`p-2.5 rounded-xl cursor-pointer transition text-xs flex flex-col gap-1 border ${
                  isSelected
                    ? 'bg-white border-indigo-200 text-indigo-900 font-semibold shadow-2xs'
                    : 'border-transparent hover:bg-slate-100 text-slate-600'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-xs">{tool.name}</span>
                  <span className="badge badge-neutral text-2xs">{tool.category}</span>
                </div>
                <p className="text-2xs text-slate-400 line-clamp-2 leading-relaxed">{tool.description}</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Main Execution Workspace */}
      <div className="flex-1 flex flex-col h-full overflow-y-auto p-6 gap-6 bg-slate-50/50">
        {selectedTool ? (
          <div className="max-w-4xl mx-auto w-full flex flex-col gap-5">
            {/* Tool Detail Card */}
            <div className="bg-white border border-slate-200 rounded-2xl shadow-xs p-5 flex flex-col gap-3">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="flex items-center gap-2.5">
                  <div className="w-9 h-9 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center border border-indigo-100 shadow-2xs">
                    <Wrench size={16} />
                  </div>
                  <div>
                    <h2 className="text-sm font-bold text-slate-900">{selectedTool.name}</h2>
                    <span className="text-2xs text-slate-400 font-mono">Category: {selectedTool.category}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {selectedTool.requires_approval && (
                    <span className="badge badge-warning text-2xs flex items-center gap-1">
                      <Shield size={11} /> Confirmation Required
                    </span>
                  )}
                  {selectedTool.is_external && (
                    <span className="badge badge-accent text-2xs flex items-center gap-1">
                      <Globe size={11} /> External Network
                    </span>
                  )}
                </div>
              </div>
              <p className="text-xs text-muted leading-relaxed">{selectedTool.description}</p>
            </div>

            {/* Parameter Inputs Card */}
            <div className="card p-4 flex flex-col gap-3.5">
              <div className="flex items-center justify-between">
                <h4 className="text-2xs font-bold font-mono uppercase tracking-wider text-muted">Parameters</h4>
              </div>

              {selectedTool.parameters?.properties && Object.keys(selectedTool.parameters.properties).length > 0 ? (
                <div className="flex flex-col gap-3">
                  {Object.entries(selectedTool.parameters.properties).map(([paramName, paramProp]: [string, any]) => (
                    <div key={paramName} className="flex flex-col gap-1">
                      <div className="flex items-center justify-between text-2xs">
                        <label className="font-semibold text-main font-mono">{paramName}</label>
                        <span className="text-dim">{paramProp.description || paramProp.type}</span>
                      </div>
                      <input
                        type="text"
                        value={paramInputs[paramName] || ''}
                        onChange={e => setParamInputs({ ...paramInputs, [paramName]: e.target.value })}
                        className="input-text text-xs font-mono"
                        placeholder={`Enter ${paramName}...`}
                      />
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-dim italic">This tool takes no parameters.</p>
              )}

              <button
                onClick={handleExecute}
                disabled={isExecuting}
                className="btn btn-primary self-start py-2 px-4 flex items-center gap-2 text-xs font-semibold"
              >
                <Play size={14} />
                <span>{isExecuting ? 'Executing...' : 'Run Tool'}</span>
              </button>
            </div>

            {/* Execution Result Box */}
            {executionResult && (
              <div className="card p-4 flex flex-col gap-2.5">
                <div className="flex items-center justify-between border-b border-subtle pb-2">
                  <span className="text-2xs font-bold font-mono uppercase tracking-wider text-muted">
                    Execution Output
                  </span>
                  <div className="flex items-center gap-2 text-2xs font-mono">
                    <span className={`badge ${executionResult.status === 'success' ? 'badge-success' : 'badge-danger'}`}>
                      {executionResult.status}
                    </span>
                    <span className="text-dim">{executionResult.execution_time_ms}ms</span>
                  </div>
                </div>

                {executionResult.error ? (
                  <div className="p-3 rounded-lg border border-red-900/50 bg-red-950/20 text-xs text-danger font-mono">
                    {executionResult.error}
                  </div>
                ) : (
                  <pre
                    className="p-3.5 rounded-lg border text-xs font-mono overflow-x-auto text-main select-text leading-relaxed"
                    style={{ backgroundColor: 'var(--bg-canvas)', borderColor: 'var(--border-subtle)' }}
                  >
                    {JSON.stringify(executionResult.result, null, 2)}
                  </pre>
                )}
              </div>
            )}

            {/* Audit History Card */}
            <div className="card p-4 flex flex-col gap-3">
              <h4 className="text-2xs font-bold font-mono uppercase tracking-wider text-muted">
                Recent Tool Audit Trail
              </h4>
              {history.length === 0 ? (
                <p className="text-xs text-dim italic">No recent tool logs recorded.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-2xs font-mono">
                    <thead className="border-b border-subtle text-dim">
                      <tr>
                        <th className="py-2">Time</th>
                        <th className="py-2">Tool</th>
                        <th className="py-2">Status</th>
                        <th className="py-2">Duration</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {history.slice(0, 6).map((h, i) => (
                        <tr key={i} className="hover:bg-card">
                          <td className="py-2 text-dim">{new Date(h.created_at).toLocaleTimeString()}</td>
                          <td className="py-2 font-semibold text-main">{h.tool_name}</td>
                          <td className="py-2">
                            <span className={h.status === 'success' ? 'text-emerald-400' : 'text-rose-400'}>
                              {h.status}
                            </span>
                          </td>
                          <td className="py-2 text-dim">{h.execution_time_ms}ms</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center text-xs text-dim">
            Select a tool on the left to inspect and test.
          </div>
        )}
      </div>
    </div>
  );
};
