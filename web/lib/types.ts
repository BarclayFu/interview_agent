export interface UsageByNode {
  node: string;
  model: string;
  calls: number;
  prompt_tokens: number;
  completion_tokens: number;
  cache_hit_tokens: number;
  cache_miss_tokens: number;
  cost_cny: number;
  latency_ms_avg: number;
}

export interface UsageTotals {
  calls: number;
  prompt_tokens: number;
  completion_tokens: number;
  cache_hit_tokens: number;
  cache_miss_tokens: number;
  cost_cny: number;
  cache_hit_rate: number;
}

export interface UsageResponse {
  totals: UsageTotals;
  by_node: UsageByNode[];
  calls: {
    id: number;
    node: string;
    model: string;
    prompt_tokens: number;
    completion_tokens: number;
    cache_hit_tokens: number;
    cost_cny: number;
    latency_ms: number;
    created_at: string;
  }[];
}

export interface DebugState {
  phase: string | null;
  question_count: number;
  max_questions: number | null;
  followup_depth: number;
  current_project_idx: number;
  project_count: number;
  project_names: string[];
  hint_count: number;
  next_action: string | null;
  pending_action: string | null;
  asked_count: number;
  current_question: string | null;
}

export interface DebugResponse {
  state: DebugState;
  next: string[];
  paused_tasks: string[];
}

export interface Decision {
  score: number;
  rationale: string;
  evidence: string;
  next_action: string;
  effective_action: string;
  guard: string | null;
  followup_depth: number;
}
