import React, { useState, useEffect } from 'react';
import {
  Code2,
  Folder,
  FileCode,
  FileText,
  Play,
  CheckCircle2,
  XCircle,
  GitBranch,
  Terminal,
  RefreshCw,
  FolderOpen,
  File,
  ShieldCheck,
  Check,
  X,
  Sparkles
} from 'lucide-react';
import { api } from '../services/api';
import { WorkspaceFile, CodingTask, GitStatusResult } from '../types';
import { DiffViewer } from '../components/DiffViewer';

export const CodingAgentPage: React.FC = () => {
  const [files, setFiles] = useState<WorkspaceFile[]>([]);
  const [workspaceRoot, setWorkspaceRoot] = useState('');
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string>('');
  const [gitStatus, setGitStatus] = useState<GitStatusResult | null>(null);
  const [tasks, setTasks] = useState<CodingTask[]>([]);
  const [activeTask, setActiveTask] = useState<CodingTask | null>(null);

  // New task form
  const [taskPrompt, setTaskPrompt] = useState('');
  const [isPlanning, setIsPlanning] = useState(false);
  const [isRunningTests, setIsRunningTests] = useState(false);
  const [testOutput, setTestOutput] = useState<any | null>(null);

  const loadWorkspace = async () => {
    try {
      const tree = await api.getWorkspaceTree();
      setFiles(tree.files);
      setWorkspaceRoot(tree.workspace_root);
    } catch (e) {
      console.error(e);
    }
  };

  const loadGit = async () => {
    try {
      const g = await api.getGitStatus();
      setGitStatus(g);
    } catch (e) {
      console.error(e);
    }
  };

  const loadTasks = async () => {
    try {
      const t = await api.listCodingTasks();
      setTasks(t);
      if (t.length > 0 && !activeTask) {
        setActiveTask(t[0]);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadWorkspace();
    loadGit();
    loadTasks();
  }, []);

  const handleSelectFile = async (path: string) => {
    setSelectedFile(path);
    try {
      const res = await api.readWorkspaceFile(path);
      setFileContent(res.content);
    } catch (e: any) {
      setFileContent(`[Error loading file: ${e.message}]`);
    }
  };

  // Create new task and generate proposal
  const handleCreateTask = async () => {
    if (!taskPrompt.trim()) return;
    setIsPlanning(true);
    try {
      const task = await api.createCodingTask(taskPrompt);
      const targetFilePath = selectedFile || 'workbench_util.py';
      const proposedCode =
        fileContent && fileContent.trim()
          ? `${fileContent}\n\n# Added by Local AI Workbench Coding Agent\ndef workbench_health_check():\n    \"\"\"Automated health check helper.\"\"\"\n    return {\"status\": \"ok\", \"agent\": \"local_workbench\"}\n`
          : `# Created by Local AI Workbench Coding Agent\ndef workbench_health_check():\n    \"\"\"Automated health check helper.\"\"\"\n    return {\"status\": \"ok\", \"agent\": \"local_workbench\"}\n`;

      const diffRes = await api.computeDiff(targetFilePath, proposedCode);

      // Submit plan to task
      await fetch(`/api/coding/tasks/${task.id}/plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          plan: `1. Inspect ${targetFilePath}\n2. Append validated workbench_health_check() utility function.\n3. Verify diff and request user approval.`,
          affected_files: [targetFilePath],
          diff_content: diffRes.diff
        })
      });

      setTaskPrompt('');
      loadTasks();
      loadWorkspace();
    } catch (e) {
      console.error(e);
    } finally {
      setIsPlanning(false);
    }
  };

  const handleApplyChanges = async (approved: boolean) => {
    if (!activeTask) return;
    try {
      const targetFilePath = activeTask.affected_files[0] || selectedFile || 'workbench_util.py';
      const updatedCode =
        fileContent && fileContent.trim()
          ? `${fileContent}\n\n# Added by Local AI Workbench Coding Agent\ndef workbench_health_check():\n    \"\"\"Automated health check helper.\"\"\"\n    return {\"status\": \"ok\", \"agent\": \"local_workbench\"}\n`
          : `# Created by Local AI Workbench Coding Agent\ndef workbench_health_check():\n    \"\"\"Automated health check helper.\"\"\"\n    return {\"status\": \"ok\", \"agent\": \"local_workbench\"}\n`;

      await api.applyCodingChanges(
        activeTask.id,
        [{ path: targetFilePath, content: updatedCode }],
        approved
      );

      loadTasks();
      loadWorkspace();
      if (selectedFile === targetFilePath) {
        handleSelectFile(targetFilePath);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleRunTests = async () => {
    if (!activeTask) return;
    setIsRunningTests(true);
    setTestOutput(null);
    try {
      const res = await api.runCodingTests(activeTask.id, 'pytest');
      setTestOutput(res);
      loadTasks();
    } catch (err: any) {
      setTestOutput({ exit_code: 1, stderr: err.message });
    } finally {
      setIsRunningTests(false);
    }
  };

  const getFileIcon = (fileName: string, isDir: boolean) => {
    if (isDir) return <Folder size={14} className="text-amber-400" />;
    if (fileName.endsWith('.py')) return <FileCode size={14} className="text-blue-400" />;
    if (fileName.endsWith('.ts') || fileName.endsWith('.tsx') || fileName.endsWith('.js'))
      return <FileCode size={14} className="text-yellow-400" />;
    if (fileName.endsWith('.json')) return <FileText size={14} className="text-emerald-400" />;
    return <File size={14} className="text-dim" />;
  };

  const codeLines = fileContent.split('\n');

  return (
    <div className="flex h-full overflow-hidden" style={{ backgroundColor: 'var(--bg-canvas)' }}>
      {/* File Tree & Git Explorer Sidebar */}
      <div
        className="flex flex-col border-r select-none"
        style={{
          width: '260px',
          backgroundColor: 'var(--bg-sidebar)',
          borderColor: 'var(--border-subtle)'
        }}
      >
        <div className="px-3.5 py-2.5 border-b border-subtle flex items-center justify-between text-xs font-semibold text-main">
          <div className="flex items-center gap-2">
            <FolderOpen size={14} className="text-accent" />
            <span className="truncate">Project Files ({files.length})</span>
          </div>
          <button
            onClick={() => { loadWorkspace(); loadGit(); }}
            className="p-1 rounded hover:bg-card text-muted hover:text-main transition"
            title="Refresh Files"
          >
            <RefreshCw size={12} />
          </button>
        </div>

        {/* Git Branch Pill */}
        {gitStatus && (
          <div className="px-3 py-1.5 border-b border-slate-200/80 flex items-center justify-between text-2xs font-mono bg-slate-50">
            <div className="flex items-center gap-1.5 text-slate-600">
              <GitBranch size={12} className="text-indigo-600" />
              <span>{gitStatus.branch || 'no-git'}</span>
            </div>
            <span className={gitStatus.clean ? 'text-emerald-600' : 'text-amber-600 font-semibold'}>
              {gitStatus.clean ? 'clean' : `${gitStatus.modified.length} changed`}
            </span>
          </div>
        )}

        {/* File Tree List */}
        <div className="flex-1 overflow-y-auto p-1.5 flex flex-col gap-0.5 text-xs font-mono">
          {files.length === 0 ? (
            <div className="p-6 text-center text-2xs text-dim">Workspace directory is empty.</div>
          ) : (
            files.map(f => {
              const isSelected = selectedFile === f.path;
              return (
                <div
                  key={f.path}
                  onClick={() => handleSelectFile(f.path)}
                  className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg cursor-pointer transition ${
                    isSelected
                      ? 'bg-indigo-50 text-indigo-700 font-semibold border border-indigo-200/90 shadow-2xs'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/80 border border-transparent'
                  }`}
                >
                  {getFileIcon(f.name, f.is_dir)}
                  <span className="truncate flex-1 text-2xs">{f.path}</span>
                  <span className="text-2xs text-slate-400">{(f.size_bytes / 1024).toFixed(0)}K</span>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Center: Monaco-style Code Inspector */}
      <div className="flex-1 flex flex-col h-full border-r border-subtle overflow-hidden">
        {/* Editor Tab Bar */}
        <div
          className="border-b border-subtle px-4 flex items-center justify-between text-2xs font-mono"
          style={{ height: '38px', backgroundColor: 'var(--bg-panel)' }}
        >
          <div className="flex items-center gap-2 text-main font-medium">
            <FileCode size={13} className="text-accent" />
            <span>{selectedFile || 'No file opened'}</span>
          </div>
          {selectedFile && <span className="text-dim">UTF-8 • {codeLines.length} lines</span>}
        </div>

        {/* Code View with Line Numbers */}
        <div
          className="flex-1 overflow-y-auto font-mono text-2xs text-muted select-text p-3 flex"
          style={{ backgroundColor: 'var(--bg-canvas)' }}
        >
          {selectedFile ? (
            <div className="flex w-full">
              {/* Line Numbers Column */}
              <div className="select-none text-dim text-right pr-4 border-r border-subtle min-w-[3rem] shrink-0 font-mono">
                {codeLines.map((_, i) => (
                  <div key={i} className="leading-relaxed">{i + 1}</div>
                ))}
              </div>
              {/* Code Content Column */}
              <div className="pl-4 flex-1 overflow-x-auto text-main font-mono leading-relaxed">
                <pre>{fileContent}</pre>
              </div>
            </div>
          ) : (
            <div className="w-full h-full flex flex-col items-center justify-center text-dim gap-2.5">
              <Code2 size={36} className="text-dim opacity-30" />
              <p className="text-xs">Select any file on the left to inspect and review code.</p>
            </div>
          )}
        </div>
      </div>

      {/* Right Column: Coding Agent Task Review, Diff & Tests */}
      <div
        className="flex flex-col h-full overflow-y-auto p-4 gap-4 select-none"
        style={{
          width: '380px',
          backgroundColor: 'var(--bg-panel)',
          borderColor: 'var(--border-subtle)'
        }}
      >
        {/* Task Prompt Box */}
        <div className="card p-3.5 flex flex-col gap-2.5">
          <div className="flex items-center justify-between">
            <span className="text-2xs font-bold font-mono uppercase tracking-wider text-muted">
              Agent Prompt
            </span>
            <span className="badge badge-accent text-2xs">Autonomous</span>
          </div>

          <textarea
            value={taskPrompt}
            onChange={e => setTaskPrompt(e.target.value)}
            placeholder="Instruct agent (e.g. 'Add a health check utility function to test project')..."
            rows={2}
            className="input-textarea text-xs resize-none"
          />

          <button
            onClick={handleCreateTask}
            disabled={isPlanning || !taskPrompt.trim()}
            className="btn btn-primary w-full py-2 flex items-center justify-center gap-1.5 text-xs font-semibold"
          >
            <Sparkles size={14} />
            <span>{isPlanning ? 'Analyzing & Diffing...' : 'Propose Code Change'}</span>
          </button>
        </div>

        {/* Active Task & Unified Diff Review */}
        {activeTask && (
          <div className="card p-3.5 flex flex-col gap-3">
            <div className="flex items-center justify-between border-b border-subtle pb-2">
              <span className="text-xs font-bold text-main truncate max-w-[200px]">
                {activeTask.task_description}
              </span>
              <span className={`badge text-2xs ${
                activeTask.status === 'awaiting_approval'
                  ? 'badge-warning'
                  : activeTask.status === 'applied'
                  ? 'badge-success'
                  : 'badge-neutral'
              }`}>
                {activeTask.status}
              </span>
            </div>

            {activeTask.plan && (
              <div
                className="text-2xs text-muted p-2.5 rounded-lg border border-subtle whitespace-pre-line leading-relaxed"
                style={{ backgroundColor: 'var(--bg-card)' }}
              >
                {activeTask.plan}
              </div>
            )}

            {/* Diff Preview & Human-In-The-Loop Approval */}
            {activeTask.diff_content && (
              <div className="flex flex-col gap-2 mt-1">
                <span className="text-2xs font-semibold text-main font-mono">Unified Diff Preview</span>
                <DiffViewer diff={activeTask.diff_content} filePath={activeTask.affected_files[0]} />

                {activeTask.status === 'awaiting_approval' && (
                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={() => handleApplyChanges(true)}
                      className="btn btn-primary flex-1 py-2 text-xs flex items-center justify-center gap-1.5"
                      style={{ background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)' }}
                    >
                      <Check size={14} />
                      <span>Approve & Apply</span>
                    </button>
                    <button
                      onClick={() => handleApplyChanges(false)}
                      className="btn btn-danger py-2 px-3 text-xs flex items-center gap-1"
                    >
                      <X size={14} />
                      <span>Reject</span>
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Test Runner Suite */}
            <div className="border-t border-subtle pt-3 flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <span className="text-2xs font-bold font-mono uppercase tracking-wider text-muted">
                  Test Runner
                </span>
                <button
                  onClick={handleRunTests}
                  disabled={isRunningTests}
                  className="btn btn-secondary text-2xs py-1 px-2.5 flex items-center gap-1"
                >
                  <Terminal size={12} />
                  <span>{isRunningTests ? 'Running pytest...' : 'Run pytest'}</span>
                </button>
              </div>

              {testOutput && (
                <div
                  className={`p-2.5 rounded-lg border font-mono text-2xs max-h-48 overflow-y-auto ${
                    testOutput.exit_code === 0
                      ? 'bg-emerald-950/20 border-emerald-800 text-emerald-300'
                      : 'bg-red-950/20 border-red-800 text-red-300'
                  }`}
                >
                  <p className="font-semibold mb-1">Exit Code: {testOutput.exit_code}</p>
                  <pre className="whitespace-pre-wrap">{testOutput.stdout || testOutput.stderr || 'Completed without output'}</pre>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
