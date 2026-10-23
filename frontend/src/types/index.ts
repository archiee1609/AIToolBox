export interface ModelCapabilities {
  text_generation: boolean;
  streaming: boolean;
  tool_calling: boolean;
  image_understanding: boolean;
  structured_output: boolean;
  reasoning_controls: boolean;
}

export interface ModelDetails {
  name: string;
  model: string;
  parameter_size?: string;
  quantization_level?: string;
  format?: string;
  family?: string;
  context_length?: number;
  capabilities: ModelCapabilities;
  is_preferred: boolean;
  modified_at?: string;
  size_bytes?: number;
}

export interface Conversation {
  id: string;
  title: string;
  model: string;
  system_prompt: string;
  temperature: number;
  context_length: number;
  created_at: string;
  updated_at: string;
  message_count?: number;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  images: string[];
  tool_calls?: any[];
  tool_call_id?: string;
  token_count?: number;
  created_at: string;
}

export interface ToolDefinition {
  name: string;
  description: string;
  parameters: {
    type: string;
    properties: Record<string, any>;
    required?: string[];
  };
  requires_approval: boolean;
  category: string;
  is_external: boolean;
}

export interface ToolExecutionResponse {
  tool_name: string;
  status: 'success' | 'error' | 'blocked' | 'requires_approval';
  result?: any;
  error?: string;
  execution_time_ms: number;
  requires_approval?: boolean;
  confirmation_message?: string;
}

export interface WorkspaceFile {
  name: string;
  path: string;
  is_dir: boolean;
  size_bytes: number;
  modified_at: string;
}

export interface WorkspaceTree {
  workspace_root: string;
  files: WorkspaceFile[];
}

export interface CodingTask {
  id: string;
  workspace_path: string;
  task_description: string;
  status: 'planning' | 'awaiting_approval' | 'applied' | 'rejected' | 'testing' | 'completed' | 'failed';
  plan?: string;
  affected_files: string[];
  diff_content?: string;
  command_logs: any[];
  created_at: string;
  completed_at?: string;
}

export interface GitStatusResult {
  is_git_repo: boolean;
  branch?: string;
  clean: boolean;
  modified: string[];
  untracked: string[];
  diff?: string;
}

export interface WorkflowStep {
  id: string;
  action_type: 'read_files' | 'extract_info' | 'llm_transform' | 'write_file' | 'run_test';
  parameters: Record<string, any>;
  require_confirmation: boolean;
}

export interface Workflow {
  id: string;
  name: string;
  description: string;
  steps: WorkflowStep[];
  enabled: boolean;
  timeout_seconds: number;
  max_iterations: number;
  created_at: string;
  updated_at: string;
}

export interface WorkflowDryRunPreview {
  workflow_id?: string;
  workflow_name: string;
  valid: boolean;
  validation_errors: string[];
  action_previews: Array<{
    step_index: number;
    action_type: string;
    summary: string;
    requires_confirmation: boolean;
  }>;
  sensitive_steps_requiring_approval: string[];
}

export interface WorkflowRun {
  id: string;
  workflow_id: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  triggered_by: string;
  logs: Array<{
    timestamp: string;
    step: string;
    message: string;
    detail?: any;
  }>;
  result: Record<string, any>;
  error?: string;
  duration_ms: number;
  created_at: string;
}

export interface ComfyUIStatus {
  is_reachable: boolean;
  is_installed?: boolean;
  service_url: string;
  version?: string;
  queue_remaining: number;
  available_checkpoints: string[];
  actionable_instructions?: string;
  download_progress?: {
    status: 'idle' | 'downloading' | 'completed' | 'failed';
    model_key?: string;
    filename?: string;
    percent?: number;
    downloaded_bytes?: number;
    total_bytes?: number;
    message?: string;
  };
}

export interface ImageHistoryItem {
  id: string;
  prompt: string;
  negative_prompt?: string;
  model_checkpoint?: string;
  seed?: number;
  width: number;
  height: number;
  image_filename: string;
  image_url?: string;
  status: string;
  error?: string;
  created_at: string;
}

export interface ServiceHealth {
  name: string;
  status: 'healthy' | 'unavailable' | 'degraded';
  endpoint: string;
  details: Record<string, any>;
}

export interface DiagnosticsReport {
  app_name: string;
  app_version: string;
  backend_status: string;
  ollama: ServiceHealth;
  comfyui: ServiceHealth;
  database: ServiceHealth;
  workspace: ServiceHealth;
  installed_models: string[];
  selected_model?: string;
  recent_errors: string[];
}

export interface SystemSettings {
  ollama_base_url: string;
  comfyui_base_url: string;
  workspace_root: string;
  default_model: string;
  default_temperature: number;
  default_context_length: number;
  enable_web_search: boolean;
  theme: string;
}

export interface BackupItem {
  filename: string;
  backup_path: string;
  size_bytes: number;
  created_at: string;
}

export interface MemoryItem {
  id: string;
  key: string;
  content: string;
  source_tool?: 'chatgpt' | 'claude' | 'cursor' | 'copilot' | 'gemini' | 'custom' | string;
  category?: 'rules' | 'persona' | 'instructions' | 'tech_stack' | 'general' | string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProjectMemoryItem {
  workspace_path: string;
  instructions: string;
  context_summary: string;
  updated_at: string;
}

export interface ModelPullProgress {
  status: string;
  digest?: string;
  total?: number;
  completed?: number;
  percent?: number;
  error?: string;
  done?: boolean;
}

export interface ReportGenerateRequest {
  title: string;
  report_type: 'executive_summary' | 'codebase_audit' | 'test_audit' | 'technical_research' | 'custom';
  topic_description?: string;
  model?: string;
  save_to_workspace?: boolean;
  output_filename?: string;
}

export interface ReportGenerateResponse {
  title: string;
  report_type: string;
  model: string;
  content: string;
  word_count: number;
  saved_path?: string;
  created_at: string;
}


export interface SystemHardwareSpec {
  os_name: string;
  cpu_name: string;
  cpu_cores: number;
  ram_total_gb: number;
  ram_available_gb: number;
  gpu_vendor: string;
  gpu_name: string;
  vram_gb: number;
  is_unified_memory: boolean;
  tier: string;
  tier_badge: string;
  tier_description: string;
}

export interface ModelRecommendation {
  tag: string;
  name: string;
  category: string;
  category_label: string;
  parameter_size: string;
  download_size: string;
  min_ram_gb: number;
  recommended_ram_gb: number;
  fit_score: string;
  fit_badge: string;
  execution_mode: string;
  description: string;
  reason: string;
  is_installed: boolean;
  is_primary: boolean;
}

export interface ModelRecommendationsResponse {
  system_spec: SystemHardwareSpec;
  primary_recommendation?: ModelRecommendation;
  recommendations: ModelRecommendation[];
  installed_tags: string[];
}
