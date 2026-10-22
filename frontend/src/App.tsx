import React, { useEffect, useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatWindow } from './components/ChatWindow';
import { SourcePanel } from './components/SourcePanel';
import { ConnectorModal } from './components/ConnectorModal';
import {
  ChatMessage,
  ChatSession,
  ConnectorSource,
  RichCard,
  SourceAccessed,
  SummaryBlock,
} from './types/chat';
import {
  addMessage,
  createSession,
  deleteSession,
  fetchConnectorsStatus,
  fetchSessionDetails,
  fetchSessions,
  sendChatMessage,
  configureConnector,
} from './services/api';
import { Search, Bell, ChevronDown } from 'lucide-react';

export const App: React.FC = () => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sources, setSources] = useState<ConnectorSource[]>([]);
  const [connectedCount, setConnectedCount] = useState<number>(5);
  const [totalCount, setTotalCount] = useState<number>(5);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [topSearchQuery, setTopSearchQuery] = useState('');
  const [modalSource, setModalSource] = useState<ConnectorSource | null>(null);

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
      if (details.messages.length === 0) {
        // Seed default Chyawanprash launch conversation matching the reference photo
        await seedDaburOneDemoConversation(sessionId);
      } else {
        setMessages(details.messages);
      }
    } catch (err) {
      console.error('Error fetching session details:', err);
    }
  };

  const seedDaburOneDemoConversation = async (sessionId: string) => {
    const userMsg = await addMessage(
      sessionId,
      'user',
      'Find the latest emails about the Chyawanprash launch and summarize pending actions.'
    );

    const demoCards: RichCard[] = [
      {
        type: 'email',
        title: 'Chyawanprash Launch – Final Creative Assets',
        sender_initials: 'AP',
        sender_name: 'Ananya Patel (Marketing)',
        date_str: 'Oct 18, 2026',
        department: 'Marketing',
        badge_color: '#EF4444',
        snippet: 'Hi team, Please find the final creative assets for the Chyawanprash launch campaign. The key visuals and packaging adaptions have been finalized.',
        link: 'http://localhost:8000/gmail/auth/login',
        action_label: 'View email',
      },
      {
        type: 'email',
        title: 'Chyawanprash Launch – Retailer Update',
        sender_initials: 'RK',
        sender_name: 'Rohit Kumar (Sales)',
        date_str: 'Oct 17, 2026',
        department: 'Sales',
        badge_color: '#3B82F6',
        snippet: 'Sharing the latest retailer list for the Chyawanprash launch. Please confirm the stock availability across tier-1 distributors by Friday.',
        link: 'http://localhost:8000/gmail/auth/login',
        action_label: 'View email',
      },
      {
        type: 'email',
        title: 'Product Launch – Packaging Review',
        sender_initials: 'PS',
        sender_name: 'Priya Singh (R&D)',
        date_str: 'Oct 16, 2026',
        department: 'R&D',
        badge_color: '#0D9488',
        snippet: 'The packaging design for the 500g and 1kg packs is approved. Production can start as per the revised batch manufacturing schedule.',
        link: 'http://localhost:8000/gmail/auth/login',
        action_label: 'View email',
      },
      {
        type: 'email',
        title: 'Chyawanprash Launch – Digital Campaign Plan',
        sender_initials: 'VG',
        sender_name: 'Vikram Gupta (Digital)',
        date_str: 'Oct 15, 2026',
        department: 'Digital',
        badge_color: '#F59E0B',
        snippet: 'Sharing the digital campaign plan with key channels, creatives and content calendar scheduled across YouTube and Meta ad networks.',
        link: 'http://localhost:8000/gmail/auth/login',
        action_label: 'View email',
      },
    ];

    const demoSources: SourceAccessed[] = [
      {
        name: 'Gmail',
        status_text: '5 relevant emails found',
        icon: 'gmail',
        verified: true,
      },
    ];

    const demoSummaryBlock: SummaryBlock = {
      key_updates: [
        'Final creative assets for the launch campaign are ready (Marketing).',
        'Retailer list shared and stock confirmation pending (Sales).',
        'Packaging design approved for 500g and 1kg packs (R&D).',
        'Digital campaign plan shared with channel-wise details (Digital).',
      ],
      pending_actions: [
        'Confirm stock availability with key retailers.',
        'Review and approve digital campaign creatives.',
        'Align with production team for packaging timelines.',
        'Finalize launch communication plan with regional heads.',
      ],
      source_summary: 'Source: 5 emails • Gmail',
    };

    const demoFollowups = [
      'Show emails from Sales team only',
      'Summarize the digital campaign plan',
      'Find attachments related to the launch',
      'Check updates from last 3 days',
    ];

    const assistantMsg = await addMessage(
      sessionId,
      'assistant',
      'Here are the latest emails related to the Chyawanprash launch from your Gmail inbox:',
      demoCards,
      demoSources,
      demoSummaryBlock,
      demoFollowups
    );

    setMessages([userMsg, assistantMsg]);
  };

  const handleNewChat = async () => {
    try {
      const newSession = await createSession('Chyawanprash Launch Search');
      setSessions((prev) => [newSession, ...prev]);
      setActiveSessionId(newSession.id);
      await seedDaburOneDemoConversation(newSession.id);
    } catch (err) {
      console.error('Error creating new chat:', err);
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
    <div className="app-layout">
      {/* Decorative Botanical Leaf Watermarks */}
      <div className="botanical-watermark-top" />
      <div className="botanical-watermark-bottom" />

      {/* Top Header Navigation Bar */}
      <header className="top-navbar">
        {/* Brand Logo & Subtitle */}
        <div className="navbar-brand" onClick={() => handleNewChat()}>
          <div className="dabur-logo-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor">
              <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" />
              <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12" />
            </svg>
          </div>
          <div className="dabur-brand-text">
            <h1>Dabur One</h1>
            <p>Smarter Search. Better Decisions.</p>
          </div>
        </div>

        {/* Center Search Bar */}
        <form className="navbar-search-wrapper" onSubmit={handleTopSearchSubmit}>
          <div className="navbar-search-bar">
            <Search size={16} color="#64748B" />
            <input
              type="text"
              placeholder='Ask anything... (e.g. "Show me latest emails from the marketing team")'
              value={topSearchQuery}
              onChange={(e) => setTopSearchQuery(e.target.value)}
            />
          </div>
        </form>

        {/* Right User & Notifications Group */}
        <div className="navbar-right-controls">
          <button className="navbar-bell-btn" title="Notifications">
            <Bell size={18} />
            <span className="bell-badge-dot" />
          </button>

          <div className="navbar-user-profile">
            <div className="user-avatar-green">SS</div>
            <div className="user-text-info">
              <span className="user-display-name">Shashvat Sharma</span>
              <span className="user-role-label">AI Assistant</span>
            </div>
            <ChevronDown size={14} color="#64748B" />
          </div>
        </div>
      </header>

      {/* Main Body: Left Sidebar + Center Chat + Right Source Panel */}
      <div className="main-body-content">
        <Sidebar
          activeTab="chat"
          onOpenSourcesModal={() => {
            if (sources.length > 0) setModalSource(sources[0]);
          }}
        />

        <ChatWindow
          messages={messages}
          onSendMessage={handleSendMessage}
          onOpenAddSources={() => {
            if (sources.length > 0) setModalSource(sources[0]);
          }}
          isLoading={isLoading}
        />

        <SourcePanel
          sources={sources}
          connectedCount={connectedCount}
          totalCount={totalCount}
          onRefreshConnectors={loadConnectors}
        />
      </div>

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

