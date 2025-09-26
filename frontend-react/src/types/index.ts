// API Response Types
export interface ChatResponse {
  answer: string;
  sources: Source[];
}

export interface Source {
  content: string;
  metadata: {
    source_type: string;
    source_id?: string;
    timestamp?: string;
    url?: string;
  };
}

export interface ClearConversationResponse {
  message: string;
}

export interface SystemStats {
  total_messages: number;
  total_sources: number;
  last_updated: string;
  health_status: 'healthy' | 'unhealthy';
}

// Chat Types
export interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  sources?: Source[];
  status?: 'sending' | 'sent' | 'error';
}

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
}

// UI State Types
export interface ChatState {
  messages: Message[];
  isLoading: boolean;
  currentQuestion: string;
  conversations: Conversation[];
  activeConversationId: string | null;
  error: string | null;
}

export interface AppState {
  theme: 'light' | 'dark';
  sidebarOpen: boolean;
  settings: UserSettings;
}

export interface UserSettings {
  autoSave: boolean;
  showSources: boolean;
  enableNotifications: boolean;
  language: 'zh-TW' | 'en';
}

// API Error Types
export interface ApiError {
  message: string;
  code?: string;
  details?: any;
}

// WebSocket Types
export interface WebSocketMessage {
  type: 'message' | 'typing' | 'error' | 'status';
  data: any;
}

export interface TypingIndicator {
  isTyping: boolean;
  userId?: string;
}
