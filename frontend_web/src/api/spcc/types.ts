export type Section = '前半' | '中盤' | '後半';

export interface EmotionPoint {
  section: Section;
  positive: number;
  dissatisfied: number;
  anger: number;
  agent_score: number;
}

export interface PeakUtterance {
  timestamp: string | null;
  text: string;
  dissatisfied: number;
  anger: number;
}

export interface LLMScores {
  listening: number;
  problem_solving: number;
  clarity: number;
  manner: number;
  efficiency: number;
}

export interface LLMEvalResult {
  scores: LLMScores | null;
  total: number | null;
  grade: 'S' | 'A' | 'B' | 'C' | null;
  summary: string;
  highlights: string[];
  improvements: string[];
  coaching: string;
  peak_moment: string;
  resolution: string;
  error: string | null;
}

export interface CallSummary {
  call_id: string;
  operator: string;
  skill: string;
  duration_sec: number;
  direction: string;
  max_dissatisfied: number;
  avg_agent_score: number;
  flagged: boolean;
}

export interface CallDetail {
  call_id: string;
  operator: string;
  skill: string;
  duration_sec: number;
  direction: string;
  emotion_timeline: EmotionPoint[];
  transcript: string;
  peak_utterances: PeakUtterance[];
  llm_eval: LLMEvalResult | null;
}

export interface SkillCount {
  skill: string;
  count: number;
}

export interface ScoreBucket {
  range: string;
  count: number;
}

export interface DashboardStats {
  total_calls: number;
  avg_duration_sec: number;
  alert_calls: number;
  operator_count: number;
  skill_breakdown: SkillCount[];
  score_distribution: ScoreBucket[];
  match_rate: number;
}

export interface OperatorSummary {
  name: string;
  calls_count: number;
  avg_duration_sec: number;
  avg_agent_score: number;
  alert_rate: number;
}

export interface OperatorReport {
  operator: string;
  summary_stats: OperatorSummary;
  skill_breakdown: SkillCount[];
  recent_calls: CallSummary[];
  llm_eval_summary: LLMEvalResult | null;
  representative_call_id: string | null;
}

export interface UploadResponse {
  session_id: string;
  stats: DashboardStats;
}
