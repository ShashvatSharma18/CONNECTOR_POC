import React, { useEffect, useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatWindow } from './components/ChatWindow';
import { KnowledgeHub } from './components/KnowledgeHub';
import { ConnectorModal } from './components/ConnectorModal';
import {
  ChatMessage,
  ChatSession,
  ConnectorSource,
} from './types/chat';
import {
  createSession,
  deleteSession,
  fetchConnectorsStatus,
  fetchSessionDetails,
  fetchSessions,
  sendChatMessage,
  configureConnector,
  disconnectConnector,
} from './services/api';
import { Search, Bell, ChevronDown, ShieldCheck } from 'lucide-react';

export const App: React.FC = () => {
  const [activeNavTab, setActiveNavTab] = useState<'chat' | 'knowledge' | 'history' | 'settings'>('chat');
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(true);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sources, setSources] = useState<ConnectorSource[]>([]);
  const [connectedCount, setConnectedCount] = useState<number>(6);
  const [totalCount, setTotalCount] = useState<number>(12);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [topSearchQuery, setTopSearchQuery] = useState('');
  const [modalSource, setModalSource] = useState<ConnectorSource | null>(null);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);

  // Load initial data
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
      setMessages(details.messages || []);
    } catch (err) {
      console.error('Error fetching session details:', err);
    }
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

  const handleDeleteSession = async (sessionId: string) => {
    try {
      await deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (activeSessionId === sessionId) {
        const remaining = sessions.filter((s) => s.id !== sessionId);
        if (remaining.length > 0) {
          selectSession(remaining[0].id);
        } else {
          setActiveSessionId(null);
          setMessages([]);
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
      const result = await sendChatMessage(currentSessionId, content);
      setMessages((prev) => [
        ...prev.filter((m) => m.id !== tempUserMsg.id),
        result.user_message,
        result.assistant_message,
      ]);
    } catch (err: any) {
      console.error('Failed to send message:', err);
      const errMsg: ChatMessage = {
        id: 'err-' + Date.now(),
        session_id: currentSessionId,
        role: 'assistant',
        content: `Error: ${err.message || 'Unable to retrieve data from connected sources. Please check credentials.'}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTopSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (topSearchQuery.trim()) {
      handleSendMessage(topSearchQuery.trim());
      setTopSearchQuery('');
    }
  };

  return (
    <div className="cerebro-app-frame">
      {/* 1. Left Translucent Sidebar */}
      <Sidebar
        activeTab={activeNavTab}
        onSelectTab={(tab) => setActiveNavTab(tab as any)}
        connectedCount={connectedCount}
        totalCount={totalCount}
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={selectSession}
        onNewChat={handleNewChat}
        onDeleteSession={handleDeleteSession}
        sources={sources}
        isOpen={isSidebarOpen}
        onToggle={() => setIsSidebarOpen((prev) => !prev)}
      />

      {/* 2. Main Viewport (Top Header + Center Content) */}
      <div className="cerebro-main-viewport">
        {/* Top Floating Glass Navigation Bar */}
        <header className="cerebro-top-bar">
          {/* Center Search Input */}
          <form className="top-search-form" onSubmit={handleTopSearchSubmit}>
            <div className="top-search-bar-glass">
              <Search size={15} className="top-search-icon" />
              <input
                type="text"
                placeholder='Ask anything... (e.g. "Show me latest emails from the marketing team")'
                value={topSearchQuery}
                onChange={(e) => setTopSearchQuery(e.target.value)}
              />
              <span className="top-search-kbd">⌘ K</span>
            </div>
          </form>

          {/* Right Controls: Notification, Profile, Enterprise Secure */}
          <div className="top-bar-right-controls">
            <button type="button" className="top-bar-icon-btn" title="Notifications" aria-label="Notifications">
              <Bell size={17} />
              <span className="top-bell-badge" />
            </button>

            <div className="top-user-profile-pill">
              <div className="user-avatar-emerald">SS</div>
              <div className="user-profile-text">
                <span className="user-profile-name">Shashvat Sharma</span>
                <span className="user-profile-role">AI Assistant</span>
              </div>
              <ChevronDown size={13} className="user-chevron" />
            </div>

            <div className="enterprise-secure-badge-glass">
              <ShieldCheck size={14} />
              <span>Enterprise Secure</span>
            </div>
          </div>
        </header>

        {/* Center Main Workspace */}
        <div className="cerebro-viewport-content">
          {activeNavTab === 'knowledge' ? (
            <KnowledgeHub
              sources={sources}
              onRefreshConnectors={loadConnectors}
              onConnectClick={(source) => {
                if (source.auth_type === 'oauth' && source.auth_url) {
                  window.location.href = source.auth_url;
                } else {
                  setModalSource(source);
                }
              }}
              onDisconnectClick={async (source) => {
                setActionLoadingId(source.id);
                try {
                  await disconnectConnector(source.id);
                  await loadConnectors();
                } catch (err) {
                  console.error('Error disconnecting connector:', err);
                } finally {
                  setActionLoadingId(null);
                }
              }}
              onSwitchToChat={() => setActiveNavTab('chat')}
              isLoadingSourceId={actionLoadingId}
            />
          ) : (
            <ChatWindow
              messages={messages}
              sources={sources}
              onSendMessage={handleSendMessage}
              onOpenAddSources={() => setActiveNavTab('knowledge')}
              isLoading={isLoading}
            />
          )}
        </div>
      </div>

      {/* Modal Dialog */}
      {modalSource && (
        <ConnectorModal
          source={modalSource}
          onClose={() => setModalSource(null)}
          onSave={async (cid, creds) => {
            await configureConnector(cid, creds);
            await loadConnectors();
            setModalSource(null);
          }}
        />
      )}
    </div>
  );
};

export default App;
