export type ExperimentMode = 'new' | 'old';
export type Direction = 'min' | 'max';
export type SamplingMethod = 'random' | 'lhs' | 'sobol';

export interface ContinuousFeatures {
  feature_names: string[];
  bounds: [number, number][];
  resolutions: number[];
}

export interface CategoricalFeatures {
  feature_names: string[];
  values: string[][];
}

export interface ExperimentConfig {
  continuous: ContinuousFeatures;
  categorical: CategoricalFeatures;
  objectives: string[];
  directions: Direction[];
  sampling: SamplingMethod;
  training_size: number;
  batch_size: number;
  file_name: string;
  regresor_model: string;
}

export interface Progress {
  reaction_scope: boolean;
  training_set: boolean;
  optimization: boolean;
}

export interface TrainingProgress {
  current_iteration: number;
  parameters: unknown[];
  objectives: unknown[];
}

export interface PredictionProgress {
  current_iteration: number;
  parameters: unknown[][];
  objectives: unknown[][];
}

export interface ExperimentState {
  id: string;
  mode: ExperimentMode;
  exp_dir: string;
  created_at: string;
  progress: Progress;
  config: ExperimentConfig | null;
  batch_size: number;
  training_progress: TrainingProgress;
  prediction_progress: PredictionProgress;
}

export interface ExperimentSummary {
  id: string;
  mode: ExperimentMode;
  exp_dir: string;
  created_at: string;
  updated_at: string;
  progress: Progress;
}

export interface ScanForExperimentsResult {
  added: ExperimentSummary[];
  skipped: { exp_dir: string; reason: string }[];
}

export interface DataUploadResult {
  columns: string[];
  row_count: number;
  preview: Record<string, unknown>[];
}

export interface TrainingRow {
  iteration: number;
  parameters: unknown[];
  objectives: unknown[] | null;
  status: 'pending' | 'completed';
}

export interface FullDataset {
  feature_names: string[];
  objective_names: string[];
  columns: string[];
  rows: (string | number)[][];
}

export interface TrainingTable {
  feature_names: string[];
  objective_names: string[];
  training_size: number;
  current_iteration: number;
  rows: TrainingRow[];
}

export interface TrainingNextResult {
  complete: boolean;
  parameters?: unknown[];
  current_iteration?: number;
  training_size?: number;
}

export interface PredictionNextResult {
  complete: boolean;
  parameters?: unknown[][];
  current_iteration?: number;
  batch_size?: number;
}

export interface CurrentBatchResult {
  parameters: unknown[][];
  current_iteration: number;
  batch_size: number;
}
