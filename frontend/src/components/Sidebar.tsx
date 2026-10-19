import React from 'react';
import {
  MessageSquare,
  Plus,
  Settings,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Trash2,
  ChevronRight,
} from 'lucide-react';
import { ChatSession } from '../types/chat';

interface SidebarProps {
  sessions: ChatSession[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
  onDeleteSession: (id: string, e: React.MouseEvent) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
}) => {
  const [isRecentOpen, setIsRecentOpen] = React.useState(true);

  return (
    <aside className="sidebar">
      {/* Brand Header */}
      <div className="sidebar-header">
        <div className="brand-logo-container">
          <div className="brand-logo">
            <Sparkles size={18} className="text-white" />
          </div>
          <div className="brand-text">
            <h2>Source Systems Chat</h2>
            <p>Ask • Search • Get Answers</p>
          </div>
        </div>
        <button className="icon-btn-ghost" title="Collapse sidebar">
          <ChevronRight size={16} />
        </button>
      </div>

      {/* New Chat Button */}
      <div className="sidebar-action">
        <button className="new-chat-btn" onClick={onNewChat}>
          <Plus size={18} />
          <span>New Chat</span>
        </button>
      </div>

      {/* Recent Chats Section */}
      <div className="recent-chats-container">
        <div
          className="section-header"
          onClick={() => setIsRecentOpen(!isRecentOpen)}
        >
          <div className="flex-center gap-8">
            <MessageSquare size={16} className="text-muted" />
            <span>Recent Chats</span>
          </div>
          {isRecentOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>

        {isRecentOpen && (
          <div className="session-list">
            {sessions.length === 0 ? (
              <div className="empty-sessions">No recent chats yet</div>
            ) : (
              sessions.map((session) => {
                const isActive = session.id === activeSessionId;
                return (
                  <div
                    key={session.id}
                    className={`session-item ${isActive ? 'active' : ''}`}
                    onClick={() => onSelectSession(session.id)}
                  >
                    <MessageSquare size={16} className="session-icon" />
                    <div className="session-meta">
                      <span className="session-title" title={session.title}>
                        {session.title}
                      </span>
                      <span className="session-time">
                        {new Date(session.updated_at).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </div>
                    <button
                      className="delete-session-btn"
                      title="Delete chat"
                      onClick={(e) => onDeleteSession(session.id, e)}
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>

      {/* Footer / User Profile */}
      <div className="sidebar-footer">
        <button className="footer-nav-item">
          <Settings size={18} />
          <span>Settings</span>
        </button>

        <div className="user-profile-pill">
          <div className="user-avatar-initials">SS</div>
          <div className="user-info">
            <span className="user-name">Shashvat Sharma</span>
          </div>
          <ChevronDown size={16} className="text-muted" />
        </div>
      </div>
    </aside>
  );
};
