import React from 'react';
import {
  Plus,
  MessageSquare,
  Sparkles,
  BookOpen,
  Trash2,
  CheckCircle2,
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
  PanelLeftClose,
  FileSearch,
} from 'lucide-react';
import { ChatSession, ConnectorSource } from '../types/chat';

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
  connectedCount = 0,
  totalCount = 0,
  sessions = [],
  activeSessionId = null,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  sources = [],
  isOpen = true,
  onToggle,
}) => {
  const connectedSources = sources.filter(
    (s) => s.is_connected && !['servicenow', 'salesforce', 'jira'].includes(s.id.toLowerCase())
  );

  const getSourceIcon = (id: string) => {
    switch (id) {
      case 'gmail':
        return <Mail size={12} color="#DC2626" />;
      case 'google_drive':
        return <HardDrive size={12} color="#D97706" />;
      case 'google_chat':
        return <MessageSquare size={12} color="#16A34A" />;
      case 'slack':
        return <Hash size={12} color="#7E22CE" />;
      case 'postgres':
      case 'database':
        return <Database size={12} color="#0284C7" />;
      case 'notion':
        return <FileText size={12} color="#334155" />;
      case 'github':
        return <GitBranch size={12} color="#6D28D9" />;
      case 'sharepoint':
        return <Layers size={12} color="#0F766E" />;
      case 'teams':
        return <Users size={12} color="#4338CA" />;
      case 'azure_devops':
        return <Box size={12} color="#0369A1" />;
      case 'file_share':
        return <Folder size={12} color="#00838F" />;
      case 'lms':
        return <GraduationCap size={12} color="#C2410C" />;
      case 'universal_parser':
      case 'document_parser':
        return <FileSearch size={12} color="#059669" />;
      default:
        return <CheckCircle2 size={12} color="#164E33" />;
    }
  };

  return (
    <aside className={`dabur-sidebar ${isOpen ? 'expanded' : 'collapsed'}`}>
      {/* 1. New Chat Action Button & Collapse Button */}
      <div className="sidebar-action-header">
        <button
          type="button"
          className="btn-new-chat-primary"
          onClick={() => {
            if (onSelectTab) onSelectTab('chat');
            if (onNewChat) onNewChat();
          }}
          title="Start a new conversation"
        >
          <Plus size={16} />
          <span>New Chat</span>
        </button>
        {onToggle && (
          <button
            type="button"
            className="btn-sidebar-collapse"
            onClick={onToggle}
            title="Collapse sidebar"
          >
            <PanelLeftClose size={17} />
          </button>
        )}
      </div>

      {/* 2. Primary Navigation */}
      <nav className="sidebar-nav-list">
        <button
          className={`sidebar-nav-item ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => onSelectTab && onSelectTab('chat')}
          title="Open AI Chat Assistant"
        >
          <MessageSquare size={16} className="nav-icon" />
          <span>Chat</span>
          <Sparkles size={13} className="nav-sparkle" />
        </button>

        <button
          className={`sidebar-nav-item ${activeTab === 'knowledge' ? 'active' : ''}`}
          onClick={() => onSelectTab && onSelectTab('knowledge')}
          title="Manage connected enterprise sources"
        >
          <BookOpen size={16} className="nav-icon" />
          <span>Knowledge Hub</span>
          {totalCount > 0 && (
            <span className="sidebar-count-badge">
              {connectedCount}/{totalCount}
            </span>
          )}
        </button>
      </nav>

      {/* 3. Recent Chats Section */}
      <div className="sidebar-recent-section">
        <div className="sidebar-section-header">
          <span>Recent Conversations</span>
          <span className="sidebar-session-count">{sessions.length}</span>
        </div>

        <div className="sidebar-sessions-list">
          {sessions.length > 0 ? (
            sessions.slice(0, 10).map((session) => {
              const isActive = session.id === activeSessionId && activeTab === 'chat';
              return (
                <div
                  key={session.id}
                  className={`sidebar-session-row ${isActive ? 'active' : ''}`}
                  onClick={() => {
                    if (onSelectTab) onSelectTab('chat');
                    if (onSelectSession) onSelectSession(session.id);
                  }}
                  title={session.title}
                >
                  <MessageSquare size={13} className="session-icon" />
                  <span className="session-title-text">{session.title}</span>
                  {onDeleteSession && (
                    <button
                      type="button"
                      className="session-delete-btn"
                      title="Delete chat"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteSession(session.id);
                      }}
                    >
                      <Trash2 size={12} />
                    </button>
                  )}
                </div>
              );
            })
          ) : (
            <span className="sidebar-empty-hint">No past conversations</span>
          )}
        </div>
      </div>

      {/* 4. Active Integrations Mini Widget */}
      <div className="sidebar-integrations-widget">
        <div
          className="sidebar-section-header clickable"
          onClick={() => onSelectTab && onSelectTab('knowledge')}
          title="Open Knowledge Hub"
        >
          <span>Active Sources ({connectedSources.length})</span>
          <span className="view-all-link">Manage &gt;</span>
        </div>

        <div className="sidebar-sources-chips">
          {connectedSources.map((s) => (
            <div
              key={s.id}
              className="sidebar-source-mini-chip"
              onClick={() => onSelectTab && onSelectTab('knowledge')}
              title={`Connected: ${s.name}`}
            >
              {getSourceIcon(s.id)}
              <span>{s.name}</span>
            </div>
          ))}
        </div>
      </div>

      {/* 5. Botanical Footer with Dabur Motto */}
      <div className="sidebar-botanical-footer">
        <svg
          className="quote-leaf-svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" />
          <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12" />
        </svg>
        <p className="botanical-quote-text">
          Goodness<br />
          of Nature.<br />
          Powered by<br />
          Technology.
        </p>
      </div>
    </aside>
  );
};
