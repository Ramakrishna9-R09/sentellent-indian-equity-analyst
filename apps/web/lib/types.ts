export type User = {
  id: string;
  email: string;
  display_name?: string | null;
  picture_url?: string | null;
};

export type Stock = {
  id: string;
  symbol: string;
  exchange: string;
  company_name: string;
  sector?: string | null;
  yfinance_symbol?: string | null;
};

export type IngestionJob = {
  id: string;
  stock_id: string;
  status: "queued" | "running" | "succeeded" | "failed";
  trigger: string;
  attempt: number;
  correlation_id: string;
  created_at: string;
  completed_at?: string | null;
  last_error?: string | null;
};

export type Follow = {
  id: string;
  stock: Stock;
  latest_job?: IngestionJob | null;
};

export type Citation = {
  id: string;
  source_document_id: string;
  title: string;
  publisher: string;
  url: string;
  published_at?: string | null;
  excerpt: string;
};

export type Recommendation = {
  stock: Stock;
  score: number;
  reasons: string[];
  citation_ids: string[];
};

export type ChatReply = {
  request_id: string;
  answer_markdown: string;
  claims: { text: string; citation_ids: string[] }[];
  citations: Citation[];
  recommendations: Recommendation[];
  data_gaps: string[];
  profile_updates: { key: string; value: unknown }[];
  retrieved_at: string;
};

export type Profile = {
  profile: {
    risk_tolerance?: string | null;
    objectives?: string[];
    avoid_high_debt?: boolean;
    max_debt_to_equity?: number | null;
    horizon?: string | null;
    excluded_sectors?: string[];
  };
  version: number;
  facts: {
    id: string;
    key: string;
    value: { value: unknown; source?: string };
    state: string;
    source_message_id?: string | null;
    created_at: string;
  }[];
};

export type SourceDetail = {
  id: string;
  type: string;
  publisher: string;
  title: string;
  url: string;
  published_at?: string | null;
  retrieved_at?: string | null;
  excerpt?: string | null;
  content?: string | null;
};
