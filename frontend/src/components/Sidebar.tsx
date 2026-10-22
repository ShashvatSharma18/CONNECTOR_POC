import React from 'react';
import {
  MessageSquare,
  Sparkles,
  BookOpen,
  Clock,
  Settings,
} from 'lucide-react';

interface SidebarProps {
  activeTab?: string;
  onSelectTab?: (tab: string) => void;
  connectedCount?: number;
  totalCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab = 'chat',
  onSelectTab,
  connectedCount = 0,
  totalCount = 0,
}) => {
  return (
    <aside className="dabur-sidebar">
      {/* Top Primary Navigation */}
      <nav className="sidebar-nav-list">
        <button
          className={`sidebar-nav-item ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => onSelectTab && onSelectTab('chat')}
          title="Open AI Chat Assistant"
        >
          <MessageSquare size={17} className="nav-icon" />
          <span>Chat</span>
          <Sparkles size={14} className="nav-sparkle" />
        </button>

        <button
          className={`sidebar-nav-item ${activeTab === 'knowledge' ? 'active' : ''}`}
          onClick={() => onSelectTab && onSelectTab('knowledge')}
          title="Manage connected enterprise sources"
        >
          <BookOpen size={17} className="nav-icon" />
          <span>Knowledge Hub</span>
          {totalCount > 0 && (
            <span
              style={{
                marginLeft: 'auto',
                background: connectedCount > 0 ? '#E8F5E9' : '#F1F5F9',
                color: connectedCount > 0 ? '#164E33' : '#64748B',
                fontSize: '10.5px',
                fontWeight: 700,
                padding: '2px 7px',
                borderRadius: '9999px',
                border: '1px solid',
                borderColor: connectedCount > 0 ? '#C8E6C9' : '#E2E8F0',
              }}
            >
              {connectedCount}/{totalCount}
            </span>
          )}
        </button>

        <button
          className={`sidebar-nav-item ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => onSelectTab && onSelectTab('history')}
          title="View conversation history"
        >
          <Clock size={17} className="nav-icon" />
          <span>History</span>
        </button>

        <button
          className={`sidebar-nav-item ${activeTab === 'settings' ? 'active' : ''}`}
          onClick={() => onSelectTab && onSelectTab('settings')}
          title="Application settings"
        >
          <Settings size={17} className="nav-icon" />
          <span>Settings</span>
        </button>
      </nav>

      {/* Botanical Footer with Dabur Motto */}
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
