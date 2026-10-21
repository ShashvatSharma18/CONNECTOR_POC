import React, { useEffect, useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatWindow } from './components/ChatWindow';
import { SourcePanel } from './components/SourcePanel';
import {
  ChatMessage,
  ChatSession,
  ConnectorSource,
  RichCard,
  SourceAccessed,
} from './types/chat';
import {
  addMessage,
  createSession,
  deleteSession,
  fetchConnectorsStatus,
  fetchSessionDetails,
  fetchSessions,
  sendChatMessage,
} from './services/api';

export const App: React.FC = () => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sources, setSources] = useState<ConnectorSource[]>([]);
  const [connectedCount, setConnectedCount] = useState<number>(4);
  const [totalCount, setTotalCount] = useState<number>(11);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Load initial data from backend
  useEffect(() => {
    loadConnectors();
    loadSessions();

    const params = new URLSearchParams(window.location.search);
    if (params.get('connected')) {
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  const loadConnectors = async () => {
    try {
      const data = await fetchConnectorsStatus();
      setSources(data.sources);
      setConnectedCount(data.connected_count);
      setTotalCount(data.total_count);
    } catch (err) {
      console.error('Error fetching connector status:', err);
      // Fallback default sources matching reference photo
      setSources([
        { id: 'gmail', name: 'Gmail', type: 'email', status: 'Live', is_connected: true, badge_color: 'green' },
        { id: 'github', name: 'GitHub', type: 'code', status: 'Live', is_connected: true, badge_color: 'green' },
        { id: 'file_share', name: 'File Share', type: 'files', status: 'Local Test', is_connected: true, badge_color: 'blue' },
        { id: 'lms', name: 'LMS', type: 'learning', status: 'Mock', is_connected: true, badge_color: 'yellow' },
        { id: 'sharepoint', name: 'SharePoint', type: 'documents', status: 'Code Ready', is_connected: false, badge_color: 'purple' },
        { id: 'teams', name: 'Microsoft Teams', type: 'chat', status: 'Code Ready', is_connected: false, badge_color: 'purple' },
        { id: 'azure_devops', name: 'Azure DevOps Repos', type: 'code', status: 'Code Ready', is_connected: false, badge_color: 'purple' },
        { id: 'servicenow', name: 'ServiceNow', type: 'itsm', status: 'Code Ready', is_connected: false, badge_color: 'purple' },
        { id: 'salesforce', name: 'Salesforce', type: 'crm', status: 'Code Ready', is_connected: false, badge_color: 'purple' },
        { id: 'google_drive', name: 'Google Drive', type: 'documents', status: 'Code Ready', is_connected: false, badge_color: 'purple' },
        { id: 'jira', name: 'Jira', type: 'project_management', status: 'Code Ready', is_connected: false, badge_color: 'purple' },
      ]);
    }
  };

  const loadSessions = async (autoSelectFirst = true) => {
    try {
      const list = await fetchSessions();
      setSessions(list);
      if (autoSelectFirst) {
        if (list.length > 0) {
          selectSession(list[0].id);
        } else {
          handleNewChat();
        }
      }
    } catch (err) {
      console.error('Error loading chat sessions:', err);
      if (autoSelectFirst) handleNewChat();
    }
  };

  const selectSession = async (sessionId: string) => {
    setActiveSessionId(sessionId);
    try {
      const details = await fetchSessionDetails(sessionId);
      if (details.messages.length === 0) {
        // Populate initial demo conversation matching the reference photo
        await seedDemoConversation(sessionId);
      } else {
        setMessages(details.messages);
      }
    } catch (err) {
      console.error('Error fetching session details:', err);
    }
  };

  const seedDemoConversation = async (sessionId: string) => {
    const userMsg = await addMessage(
      sessionId,
      'user',
      'Find the latest project requirements file and show me related Teams discussion.'
    );

    const demoCards: RichCard[] = [
      {
        type: 'document',
        title: 'Project Requirements File',
        snippet: 'Project_Requirements_v2.1.docx',
        metadata: 'SharePoint • Updated on Apr 28, 2025 • 2.4 MB',
        link: 'http://localhost:8000/docs',
      },
      {
        type: 'teams_message',
        title: 'Related Teams Discussion',
        source_name: 'Project Requirements - Discussion',
        metadata: 'Microsoft Teams • Apr 28, 2025, 2:34 PM',
        snippet:
          '"The updated requirements document has been shared. Please review and share your feedback by EOD tomorrow."',
        link: 'http://localhost:8000/docs',
      },
    ];

    const demoSources: SourceAccessed[] = [
      {
        name: 'SharePoint',
        status_text: 'File accessed',
        icon: 'sharepoint',
        verified: true,
      },
      {
        name: 'Microsoft Teams',
        status_text: 'Message found',
        icon: 'teams',
        verified: true,
      },
    ];

    const assistantMsg = await addMessage(
      sessionId,
      'assistant',
      'I found the latest project requirements file and related Teams discussion. Here are the details:',
      demoCards,
      demoSources
    );

    setMessages([userMsg, assistantMsg]);
  };

  const handleNewChat = async () => {
    try {
      const newSession = await createSession('New Chat');
      setSessions((prev) => [newSession, ...prev]);
      setActiveSessionId(newSession.id);
      setMessages([]);
    } catch (err) {
      console.error('Error creating new chat:', err);
    }
  };

  const handleDeleteSession = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await deleteSession(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (activeSessionId === id) {
        const remaining = sessions.filter((s) => s.id !== id);
        if (remaining.length > 0) {
          selectSession(remaining[0].id);
        } else {
          handleNewChat();
        }
      }
    } catch (err) {
      console.error('Error deleting session:', err);
    }
  };

  const handleSendMessage = async (content: string) => {
    let currentSessionId = activeSessionId;
    if (!currentSessionId) {
      const newSession = await createSession(content.slice(0, 30) + '...');
      setSessions((prev) => [newSession, ...prev]);
      currentSessionId = newSession.id;
      setActiveSessionId(currentSessionId);
    }

    // Optimistically show user message immediately
    const tempUserMsg: ChatMessage = {
      id: 'temp-' + Date.now(),
      session_id: currentSessionId,
      role: 'user',
      content,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    setIsLoading(true);

    try {
      // Real backend AI chat orchestration call
      const response = await sendChatMessage(currentSessionId, content);
      setMessages((prev) => {
        const withoutTemp = prev.filter((m) => m.id !== tempUserMsg.id);
        return [...withoutTemp, response.user_message, response.assistant_message];
      });
      // Refresh session list without resetting the active selection
      loadSessions(false);
    } catch (err: any) {
      console.error('Error handling message send:', err);
      const errorMsg: ChatMessage = {
        id: 'err-' + Date.now(),
        session_id: currentSessionId,
        role: 'assistant',
        content: `Could not process your message: ${err?.message || 'Network or server error.'}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app-layout">
      {/* 1. Left Sidebar */}
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={selectSession}
        onNewChat={handleNewChat}
        onDeleteSession={handleDeleteSession}
      />

      {/* 2. Center Chat Panel */}
      <ChatWindow
        messages={messages}
        onSendMessage={handleSendMessage}
        isLoading={isLoading}
      />

      {/* 3. Right Sources Panel */}
      <SourcePanel
        sources={sources}
        connectedCount={connectedCount}
        totalCount={totalCount}
        onRefreshConnectors={loadConnectors}
      />
    </div>
  );
};

export default App;
