export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface RichCardAttachment {
  filename: string;
  size: string;
  download_url: string;
}

export interface RichCard {
  type: 'document' | 'teams_message' | 'email' | 'repo' | 'slack' | 'database' | 'notion';
  title: string;
  metadata?: string;
  snippet?: string;
  file_type?: string;
  file_size?: string;
  source_name?: string;
  link?: string;
  action_label?: string;
  attachments?: RichCardAttachment[];
  sender_initials?: string;
  sender_name?: string;
  department?: string;
  date_str?: string;
  badge_color?: string;
}

export interface SourceAccessed {
  name: string;
  status_text: string;
  icon: string;
  verified: boolean;
}

export interface SummaryBlock {
  key_updates: string[];
  pending_actions: string[];
  source_summary?: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  rich_cards?: RichCard[];
  sources_accessed?: SourceAccessed[];
  summary_block?: SummaryBlock;
  suggested_followups?: string[];
}

export interface ConfigField {
  key: string;
  label: string;
  placeholder?: string;
  type?: 'text' | 'password';
  required?: boolean;
  help_text?: string;
  help_url?: string;
  default_value?: string;
}

export interface ConnectorSource {
  id: string;
  name: string;
  type: string;
  status: string;
  is_connected: boolean;
  badge_color: 'green' | 'blue' | 'yellow' | 'purple' | 'gray';
  account?: string | null;
  auth_type?: 'oauth' | 'credentials' | 'info';
  auth_url?: string;
  description?: string;
  config_fields?: ConfigField[];
  category?: string;
}

export interface ConnectorsStatusResponse {
  connected_count: number;
  total_count: number;
  sources: ConnectorSource[];
}

export interface ActivityItem {
  id: string;
  text: string;
  time_ago: string;
  icon_type: 'gmail' | 'database' | 'notion' | 'slack' | 'drive';
}
