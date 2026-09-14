export interface UserPublic {
  id: string;
  username: string;
  display_name: string;
}

export interface Profile {
  child_name?: string | null;
  child_age?: number | null;
  home_area?: string | null;
  commute_method?: string | null;
  budget_max?: number | null;
  priorities: string[];
  desired_hours?: string | null;
  needs_bus?: boolean | null;
  siblings?: string | null;
  allergies?: string | null;
  notes?: string | null;
}

export interface Kindergarten {
  id: string;
  name: string;
  area: string;
  address_rough: string;
  nearest_station: string;
  min_age: number;
  max_age: number;
  standard_hours: string;
  extended_care: boolean;
  extended_hours: string;
  monthly_fee: number;
  features: string[];
  capacity: number;
  has_bus: boolean;
  lunch_type: string;
  education_style: string;
  philosophy: string;
  url?: string | null;
  // search 結果にのみ含まれる
  match_score?: number;
  match_reasons?: string[];
}

export interface VisitRequest {
  confirmation_id: string;
  kindergarten_id: string;
  kindergarten_name: string;
  preferred_dates: string[];
  applicant_note: string;
  status: string;
  created_at: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  updated_at: string;
  message_count: number;
}

export interface ConversationDetail {
  id: string;
  title: string;
  messages: unknown[]; // 保存された Msg[]（ChatPage で Msg[] にキャスト）
}

// /api/chat のストリーミングイベント
export type ChatEvent =
  | { type: "text"; text: string }
  | { type: "tool_use"; tool: string; label: string; agent?: string | null }
  | { type: "cards"; source: string; items: Kindergarten[] }
  | { type: "favorite"; action: "added" | "removed"; id: string; name: string }
  | {
      type: "visit";
      confirmation_id: string;
      id: string;
      name: string;
      preferred_dates: string[];
      applicant_note?: string;
    }
  | {
      type: "visit_cancel";
      confirmation_id: string;
      id: string;
      name: string;
      status: string;
    }
  | { type: "notice"; text: string }
  | { type: "done"; session_id: string; cost_usd?: number | null; subtype?: string }
  | { type: "error"; message: string; detail?: string };
