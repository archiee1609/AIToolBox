import {
  ModelDetails,
  Conversation,
  Message,
  ToolDefinition,
  ToolExecutionResponse,
  WorkspaceTree,
  CodingTask,
  GitStatusResult,
  Workflow,
  WorkflowDryRunPreview,
  WorkflowRun,
  ComfyUIStatus,
  ImageHistoryItem,
  DiagnosticsReport,
  SystemSettings,
  BackupItem,
  MemoryItem,
  ProjectMemoryItem,
  ModelPullProgress,
  ReportGenerateRequest,
  ReportGenerateResponse
} from '../types';

const API_BASE = '/api';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}: ${res.statusText}`;
    try {
      const data = await res.json();
      if (data.detail) errorDetail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
      else if (data.error) errorDetail = data.error;
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }
  return res.json();
}

export const api = {
  // Health & Diagnostics
  getDiagnostics: () => fetch(`${API_BASE}/health`).then(r => handleResponse<DiagnosticsReport>(r)),

  // Ollama
  getOllamaHealth: () => fetch(`${API_BASE}/ollama/health`).then(r => handleResponse<any>(r)),
  listModels: () => fetch(`${API_BASE}/ollama/models`).then(r => handleResponse<ModelDetails[]>(r)),
  testModel: (model: string, prompt?: string) =>
    fetch(`${API_BASE}/ollama/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model, prompt })
    }).then(r => handleResponse<any>(r)),

  // Conversations & Chat
  listConversations: () => fetch(`${API_BASE}/chat/conversations`).then(r => handleResponse<Conversation[]>(r)),
  createConversation: (data: Partial<Conversation>) =>
    fetch(`${API_BASE}/chat/conversations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(r => handleResponse<Conversation>(r)),
  getConversation: (id: string) =>
    fetch(`${API_BASE}/chat/conversations/${id}`).then(r => handleResponse<{ conversation: Conversation; messages: Message[] }>(r)),
  updateConversation: (id: string, data: Partial<Conversation>) =>
    fetch(`${API_BASE}/chat/conversations/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(r => handleResponse<Conversation>(r)),
  deleteConversation: (id: string) =>
    fetch(`${API_BASE}/chat/conversations/${id}`, { method: 'DELETE' }).then(r => handleResponse<any>(r)),
  searchConversations: (q: string) =>
    fetch(`${API_BASE}/chat/conversations/search?q=${encodeURIComponent(q)}`).then(r => handleResponse<any[]>(r)),

  // Tools
  listTools: () => fetch(`${API_BASE}/tools`).then(r => handleResponse<ToolDefinition[]>(r)),
  executeTool: (name: string, args: Record<string, any>, approved: boolean = true) =>
    fetch(`${API_BASE}/tools/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tool_name: name, arguments: args, approved })
    }).then(r => handleResponse<ToolExecutionResponse>(r)),
  getToolHistory: () => fetch(`${API_BASE}/tools/history`).then(r => handleResponse<any[]>(r)),

  // Vision
  analyzeVision: (imageData: string, prompt: string, model?: string) =>
    fetch(`${API_BASE}/vision/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_data: imageData, prompt, model })
    }).then(r => handleResponse<{ model: string; response: string; capability_supported: boolean }>(r)),

  // Image Lab (ComfyUI)
  getComfyStatus: () => fetch(`${API_BASE}/image_lab/status`).then(r => handleResponse<ComfyUIStatus>(r)),
  startComfyService: () =>
    fetch(`${API_BASE}/image_lab/service/start`, { method: 'POST' }).then(r => handleResponse<any>(r)),
  stopComfyService: () =>
    fetch(`${API_BASE}/image_lab/service/stop`, { method: 'POST' }).then(r => handleResponse<any>(r)),
  getPopularComfyModels: () =>
    fetch(`${API_BASE}/image_lab/models/popular`).then(r => handleResponse<Record<string, any>>(r)),
  downloadComfyModel: (modelKey: string) =>
    fetch(`${API_BASE}/image_lab/models/download`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_key: modelKey })
    }).then(r => handleResponse<any>(r)),
  generateImage: (params: any) =>
    fetch(`${API_BASE}/image_lab/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    }).then(r => handleResponse<any>(r)),
  getImageHistory: () => fetch(`${API_BASE}/image_lab/history`).then(r => handleResponse<ImageHistoryItem[]>(r)),

  // Coding Agent
  getWorkspaceTree: (workspace?: string) =>
    fetch(`${API_BASE}/coding/workspace/tree${workspace ? `?workspace=${encodeURIComponent(workspace)}` : ''}`).then(r => handleResponse<WorkspaceTree>(r)),
  readWorkspaceFile: (path: string) =>
    fetch(`${API_BASE}/coding/workspace/read`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path })
    }).then(r => handleResponse<{ path: string; content: string; size_bytes: number; is_binary: boolean }>(r)),
  computeDiff: (path: string, newContent: string) =>
    fetch(`${API_BASE}/coding/diff`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path, new_content: newContent })
    }).then(r => handleResponse<any>(r)),
  createCodingTask: (taskDescription: string, workspacePath?: string) =>
    fetch(`${API_BASE}/coding/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_description: taskDescription, workspace_path: workspacePath })
    }).then(r => handleResponse<CodingTask>(r)),
  listCodingTasks: () => fetch(`${API_BASE}/coding/tasks`).then(r => handleResponse<CodingTask[]>(r)),
  applyCodingChanges: (taskId: string, fileChanges: Array<{ path: string; content: string }>, approved: boolean) =>
    fetch(`${API_BASE}/coding/tasks/${taskId}/apply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ approved, file_changes: fileChanges })
    }).then(r => handleResponse<any>(r)),
  runCodingTests: (taskId: string, command: string = 'pytest') =>
    fetch(`${API_BASE}/coding/tasks/${taskId}/run_tests`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command })
    }).then(r => handleResponse<any>(r)),
  getGitStatus: () => fetch(`${API_BASE}/coding/git/status`).then(r => handleResponse<GitStatusResult>(r)),

  // Workflows
  listWorkflows: () => fetch(`${API_BASE}/automation/workflows`).then(r => handleResponse<Workflow[]>(r)),
  createWorkflow: (data: Partial<Workflow>) =>
    fetch(`${API_BASE}/automation/workflows`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(r => handleResponse<Workflow>(r)),
  updateWorkflow: (id: string, data: Partial<Workflow>) =>
    fetch(`${API_BASE}/automation/workflows/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(r => handleResponse<Workflow>(r)),
  deleteWorkflow: (id: string) =>
    fetch(`${API_BASE}/automation/workflows/${id}`, { method: 'DELETE' }).then(r => handleResponse<any>(r)),
  previewWorkflow: (id: string) =>
    fetch(`${API_BASE}/automation/workflows/${id}/preview`, { method: 'POST' }).then(r => handleResponse<WorkflowDryRunPreview>(r)),
  runWorkflow: (id: string, confirmed: boolean = true) =>
    fetch(`${API_BASE}/automation/workflows/${id}/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirmed })
    }).then(r => handleResponse<WorkflowRun>(r)),
  listWorkflowRuns: (workflowId?: string) =>
    fetch(`${API_BASE}/automation/runs${workflowId ? `?workflow_id=${encodeURIComponent(workflowId)}` : ''}`).then(r => handleResponse<WorkflowRun[]>(r)),

  // Settings, Memory & Backups
  getSettings: () => fetch(`${API_BASE}/settings`).then(r => handleResponse<SystemSettings>(r)),
  updateSettings: (data: Partial<SystemSettings>) =>
    fetch(`${API_BASE}/settings`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(r => handleResponse<SystemSettings>(r)),
  listBackups: () => fetch(`${API_BASE}/settings/backups`).then(r => handleResponse<BackupItem[]>(r)),
  createBackup: () => fetch(`${API_BASE}/settings/backups`, { method: 'POST' }).then(r => handleResponse<BackupItem>(r)),
  restoreBackup: (backupFilename: string, confirm: boolean = true) =>
    fetch(`${API_BASE}/settings/restore`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ backup_filename: backupFilename, confirm })
    }).then(r => handleResponse<any>(r)),
  listMemories: () => fetch(`${API_BASE}/settings/memories`).then(r => handleResponse<MemoryItem[]>(r)),
  createMemory: (data: Partial<MemoryItem>) =>
    fetch(`${API_BASE}/settings/memories`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(r => handleResponse<MemoryItem>(r)),
  updateMemory: (id: string, data: Partial<MemoryItem>) =>
    fetch(`${API_BASE}/settings/memories/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(r => handleResponse<MemoryItem>(r)),
  toggleMemory: (id: string) =>
    fetch(`${API_BASE}/settings/memories/${id}/toggle`, { method: 'POST' }).then(r => handleResponse<any>(r)),
  importMemories: (items: Array<{ key: string; content: string; source_tool?: string; category?: string }>) =>
    fetch(`${API_BASE}/settings/memories/import`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items })
    }).then(r => handleResponse<{ imported: number }>(r)),
  deleteMemory: (id: string) =>
    fetch(`${API_BASE}/settings/memories/${id}`, { method: 'DELETE' }).then(r => handleResponse<any>(r)),
  getProjectContext: () => fetch(`${API_BASE}/settings/project_context`).then(r => handleResponse<ProjectMemoryItem>(r)),
  updateProjectContext: (instructions: string, contextSummary: string) =>
    fetch(`${API_BASE}/settings/project_context`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ instructions, context_summary: contextSummary })
    }).then(r => handleResponse<ProjectMemoryItem>(r)),

  // Ollama Model Installation & Management
  pullModel: async (
    name: string,
    onProgress: (p: ModelPullProgress) => void,
    signal?: AbortSignal
  ): Promise<void> => {
    const response = await fetch(`${API_BASE}/ollama/pull`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
      signal
    });

    if (!response.ok) {
      throw new Error(`Failed to pull model: ${response.statusText}`);
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    if (reader) {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              onProgress(data);
            } catch {
              // ignore
            }
          }
        }
      }
    }
  },

  deleteModel: (name: string) =>
    fetch(`${API_BASE}/ollama/models/${encodeURIComponent(name)}`, {
      method: 'DELETE'
    }).then(r => handleResponse<any>(r)),

  // Reports
  generateReport: (data: ReportGenerateRequest) =>
    fetch(`${API_BASE}/reports/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(r => handleResponse<ReportGenerateResponse>(r))
};
