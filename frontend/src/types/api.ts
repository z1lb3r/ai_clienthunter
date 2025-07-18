// frontend/src/types/api.ts
export interface ProductTemplate {
  id: number;
  user_id: number;
  name: string;
  keywords: string[];
  monitored_chats: string[];
  chat_ids: string[];
  check_interval_minutes: number;
  lookback_minutes: number;
  ai_prompt: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProductTemplateCreate {
  name: string;
  keywords: string[];
  monitored_chats?: string[];
  check_interval_minutes?: number;
  lookback_minutes?: number;
  ai_prompt: string;
}

export interface ProductTemplateUpdate {
  name?: string;
  keywords?: string[];
  monitored_chats?: string[];
  check_interval_minutes?: number;
  lookback_minutes?: number;
  ai_prompt?: string;
  is_active?: boolean;
}

// MonitoringSettings теперь только для глобальных настроек
export interface MonitoringSettings {
  id: number;
  user_id: number;
  notification_account: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_monitoring_check?: string;
}

export interface MonitoringSettingsUpdate {
  notification_account?: string[];
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
  totalChats: number;
  conversionRate: number;
}