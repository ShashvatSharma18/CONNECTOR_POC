import { ChatMessage, ChatSession, ConnectorsStatusResponse } from '../types/chat';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export async function fetchConnectorsStatus(): Promise<ConnectorsStatusResponse> {
  const res = await fetch(`${API_BASE}/connectors/status`);
  if (!res.ok) throw new Error('Failed to fetch connector statuses');
  return res.json();
}

export async function fetchSessions(): Promise<ChatSession[]> {
  const res = await fetch(`${API_BASE}/chat/sessions`);
  if (!res.ok) throw new Error('Failed to fetch chat sessions');
  const data = await res.json();
  return data.sessions || [];
}

export async function createSession(title: string = 'New chat'): Promise<ChatSession> {
  const res = await fetch(`${API_BASE}/chat/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error('Failed to create session');
  return res.json();
}

export async function fetchSessionDetails(
  sessionId: string
): Promise<{ id: string; title: string; messages: ChatMessage[] }> {
  const res = await fetch(`${API_BASE}/chat/sessions/${sessionId}`);
  if (!res.ok) throw new Error('Failed to fetch session messages');
  return res.json();
}

export async function updateSessionTitle(sessionId: string, title: string): Promise<void> {
  const res = await fetch(`${API_BASE}/chat/sessions/${sessionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error('Failed to update title');
}

export async function deleteSession(sessionId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/chat/sessions/${sessionId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete session');
}

export async function addMessage(
  sessionId: string,
  role: 'user' | 'assistant',
  content: string,
  rich_cards?: any[],
  sources_accessed?: any[]
): Promise<ChatMessage> {
  const res = await fetch(`${API_BASE}/chat/sessions/${sessionId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      role,
      content,
      rich_cards,
      sources_accessed,
    }),
  });
  if (!res.ok) throw new Error('Failed to add message');
  return res.json();
}

export async function sendChatMessage(
  sessionId: string,
  message: string
): Promise<{ user_message: ChatMessage; assistant_message: ChatMessage }> {
  const res = await fetch(`${API_BASE}/chat/sessions/${sessionId}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || 'Failed to send chat message');
  }
  return res.json();
}

