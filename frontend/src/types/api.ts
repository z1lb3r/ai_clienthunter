// frontend/src/types/api.ts
export interface ProductTemplate {
  id: number;
  user_id: number;
  name: string;
  keywords: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProductTemplateCreate {
  name: string;
  keywords: string[];
}

export interface ProductTemplateUpdate {
  name?: string;
  keywords?: string[];
  is_active?: boolean;
}

export interface MonitoringSettings {
  id: number;
  user_id: number;
  monitored_chats: string[];
  notification_account: string;
  check_interval_minutes: number;
  lookback_minutes: number;
  min_ai_confidence: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface MonitoringSettingsUpdate {
  monitored_chats?: string[];
  notification_account?: string;
  check_interval_minutes?: number;
  lookback_minutes?: number;
  min_ai_confidence?: number;
  is_active?: boolean;
}

export interface PotentialClient {
  id: number;
  user_id: number;
  telegram_user_id: string;
  username?: string;
  first_name?: string;
  last_name?: string;
  message_text: string;
  matched_template_id: number;
  matched_keywords: string[];
  ai_confidence: number;
  chat_id: string;
  message_id: number;
  client_status: 'new' | 'contacted' | 'ignored' | 'converted';
  created_at: string;
  updated_at: string;
}

export interface ClientStatusUpdate {
  status: 'new' | 'contacted' | 'ignored' | 'converted';
}

export interface ApiResponse<T> {
  status: 'success' | 'error';
  data?: T;
  message?: string;
}

export interface DashboardStats {
  clientsToday: number;
  clientsWeek: number;
  totalClients: number;
  conversionRate: number;
}