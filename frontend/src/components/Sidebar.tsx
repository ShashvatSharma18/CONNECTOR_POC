import React from 'react';
import {
  Plus,
  MessageSquare,
  BookOpen,
  Trash2,
  Mail,
  HardDrive,
  Hash,
  Database,
  FileText,
  GitBranch,
  Layers,
  Users,
  Box,
  Folder,
  GraduationCap,
  ChevronsLeft,
  Search,
} from 'lucide-react';
import { ChatSession, ConnectorSource } from '../types/chat';
import { CerebroBrainLogo } from './CerebroBrainLogo';

interface SidebarProps {
  activeTab?: string;
  onSelectTab?: (tab: string) => void;
  connectedCount?: number;
  totalCount?: number;
  sessions?: ChatSession[];
  activeSessionId?: string | null;
  onSelectSession?: (id: string) => void;
  onNewChat?: () => void;
  onDeleteSession?: (id: string) => void;
  sources?: ConnectorSource[];
  isOpen?: boolean;
  onToggle?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab = 'chat',
  onSelectTab,
  connectedCount = 6,
  totalCount = 12,
  sessions = [],
  activeSessionId = null,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  sources = [],
  isOpen = true,
  onToggle,
}) => {
  // 6 Connected sources matching the visual reference (Gmail, Google Chat, SQL Database, GitHub, File Share, LMS)
  const defaultSources: Array<{ id: string; name: string; is_connected: boolean }> = [
    { id: 'gmail', name: 'Gmail', is_connected: true },
    { id: 'google_chat', name: 'Google Chat', is_connected: true },
    { id: 'database', name: 'SQL Database', is_connected: true },
    { id: 'github', name: 'GitHub', is_connected: true },
    { id: 'file_share', name: 'File Share', is_connected: true },
    { id: 'lms', name: 'LMS', is_connected: true },
  ];

  const connectedSources = sources.filter(
    (s) => s.is_connected && !['servicenow', 'salesforce', 'jira'].includes(s.id.toLowerCase())
  );

  const displaySources = connectedSources.length >= 6 ? connectedSources : defaultSources;

  const getSourceIcon = (id: string) => {
    switch (id) {
      case 'gmail':
        return (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" fill="#EA4335" fillOpacity="0.2"/>
            <path d="M22 6l-10 7L2 6" stroke="#EA4335" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        );
      case 'google_chat':
        return <MessageSquare size={13} color="#10B981" />;
      case 'postgres':
      case 'database':
        return <Database size={13} color="#38BDF8" />;
      case 'github':
        return <GitBranch size={13} color="#E2E8F0" />;
      case 'file_share':
        return <Folder size={13} color="#06B6D4" />;
      case 'lms':
        return <GraduationCap size={13} color="#F97316" />;
      case 'google_drive':
        return <HardDrive size={13} color="#F59E0B" />;
      case 'slack':
        return <Hash size={13} color="#C084FC" />;
      case 'notion':
        return <FileText size={13} color="#94A3B8" />;
      case 'sharepoint':
        return <Layers size={13} color="#2DD4BF" />;
      case 'teams':
        return <Users size={13} color="#818CF8" />;
      default:
        return <Search size={13} color="#94A3B8" />;
    }
  };

  return (
    <aside className={`cerebro-sidebar ${isOpen ? 'expanded' : 'collapsed'}`}>
      {/* 1. Brand Header */}
      <div className="sidebar-brand-header">
        <div className="sidebar-brand-left" onClick={() => onNewChat && onNewChat()}>
          <CerebroBrainLogo size={36} showGlow={true} />
          <div className="sidebar-brand-text">
            <h1 className="sidebar-brand-title">Cerebro</h1>
            <p className="sidebar-brand-tagline">Smarter Search. Better Decisions.</p>
          </div>
        </div>
        {onToggle && (
          <button
            type="button"
            className="sidebar-toggle-btn"
            onClick={onToggle}
            title="Collapse sidebar"
            aria-label="Collapse sidebar"
          >
            <ChevronsLeft size={16} />
          </button>
        )}
      </div>

      {/* 2. New Chat Button with Shortcut */}
      <div className="sidebar-new-chat-wrapper">
        <button
          type="button"
          className="btn-sidebar-new-chat"
          onClick={() => {
            if (onSelectTab) onSelectTab('chat');
            if (onNewChat) onNewChat();
          }}
          title="Start a new chat (⌘ K)"
        >
          <div className="btn-new-chat-left">
            <Plus size={16} />
            <span>New Chat</span>
          </div>
          <span className="kbd-shortcut-pill">⌘ K</span>
        </button>
      </div>

      {/* 3. Primary Navigation (Chat & Knowledge Hub) */}
      <nav className="sidebar-nav-group">
        <button
          type="button"
          className={`sidebar-nav-pill ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => onSelectTab && onSelectTab('chat')}
          title="AI Chat Workspace"
        >
          <MessageSquare size={16} className="nav-pill-icon" />
          <span className="nav-pill-label">Chat</span>
        </button>

        <button
          type="button"
          className={`sidebar-nav-pill ${activeTab === 'knowledge' ? 'active' : ''}`}
          onClick={() => onSelectTab && onSelectTab('knowledge')}
          title="Enterprise Knowledge Hub"
        >
          <BookOpen size={16} className="nav-pill-icon" />
          <span className="nav-pill-label">Knowledge Hub</span>
          <span className="sidebar-ratio-pill">
            {connectedCount}/{totalCount}
          </span>
        </button>
      </nav>

      {/* 4. Recent Conversations Section */}
      <div className="sidebar-conversations-section">
        <div className="sidebar-section-title-row">
          <span className="sidebar-section-heading">RECENT CONVERSATIONS</span>
          <span className="sidebar-section-count-badge">{sessions.length}</span>
        </div>

        <div className="sidebar-conversations-list">
          {sessions.length === 0 ? (
            <div className="sidebar-empty-state">No recent conversations</div>
          ) : (
            sessions.map((sess) => {
              const isActive = sess.id === activeSessionId;
              return (
                <div
                  key={sess.id}
                  className={`sidebar-conversation-row ${isActive ? 'active' : ''}`}
                  onClick={() => {
                    if (onSelectTab) onSelectTab('chat');
                    if (onSelectSession) onSelectSession(sess.id);
                  }}
                  title={sess.title}
                >
                  <MessageSquare size={14} className="conversation-icon" />
                  <span className="conversation-title-text">{sess.title}</span>
                  {onDeleteSession && (
                    <button
                      type="button"
                      className="conversation-delete-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteSession(sess.id);
                      }}
                      title="Delete conversation"
                    >
                      <Trash2 size={13} />
                    </button>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* 5. Active Sources Section (6 Chips in 2 Columns) */}
      <div className="sidebar-sources-section">
        <div className="sidebar-section-title-row">
          <span className="sidebar-section-heading">
            ACTIVE SOURCES ({displaySources.length})
          </span>
          <button
            type="button"
            className="sidebar-manage-link"
            onClick={() => onSelectTab && onSelectTab('knowledge')}
          >
            MANAGE &gt;
          </button>
        </div>

        <div className="sidebar-sources-grid">
          {displaySources.slice(0, 6).map((src) => (
            <div
              key={src.id}
              className="sidebar-source-tile"
              onClick={() => onSelectTab && onSelectTab('knowledge')}
              title={`Connected: ${src.name}`}
            >
              <div className="source-tile-icon">{getSourceIcon(src.id)}</div>
              <span className="source-tile-name">{src.name}</span>
            </div>
          ))}
        </div>
      </div>

      {/* 6. Bottom Brand Card */}
      <div className="sidebar-bottom-brand-card">
        <CerebroBrainLogo size={42} showGlow={true} />
        <div className="bottom-brand-text">
          <h4 className="bottom-brand-title">Cerebro</h4>
          <p className="bottom-brand-motto">
            Search Beyond.<br />
            Think Ahead.
          </p>
        </div>
      </div>
    </aside>
  );
};
