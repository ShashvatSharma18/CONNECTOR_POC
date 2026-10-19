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
  type: 'document' | 'teams_message' | 'email' | 'repo';
  title: string;
  metadata?: string;
  snippet?: string;
  file_type?: string;
  file_size?: string;
  source_name?: string;
  link?: string;
  action_label?: string;
  attachments?: RichCardAttachment[];
}

export interface SourceAccessed {
  name: string;
  status_text: string;
  icon: string;
  verified: boolean;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  rich_cards?: RichCard[];
  sources_accessed?: SourceAccessed[];
}

export interface ConnectorSource {
  id: string;
  name: string;
  type: string;
  status: string;
  is_connected: boolean;
  badge_color: 'green' | 'blue' | 'yellow' | 'purple' | 'gray';
  account?: string;
}

export interface ConnectorsStatusResponse {
  connected_count: number;
  total_count: number;
  sources: ConnectorSource[];
}
