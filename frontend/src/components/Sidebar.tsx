import React from 'react';
import {
  MessageSquare,
  Sparkles,
  Layers,
  BookOpen,
  Clock,
  Settings,
  HeartPulse,
  Sparkle,
  Smile,
  Home,
  UtensilsCrossed,
} from 'lucide-react';

interface SidebarProps {
  activeTab?: string;
  onSelectTab?: (tab: string) => void;
  onOpenSourcesModal?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab = 'chat',
  onSelectTab,
  onOpenSourcesModal,
}) => {
  const businessUnits = [
    {
      name: 'Healthcare',
      subtitle: 'Ayurveda & Wellness',
      icon: HeartPulse,
    },
    {
      name: 'Personal Care',
      subtitle: 'Skin & Hair Care',
      icon: Sparkle,
    },
    {
      name: 'Oral Care',
      subtitle: 'Healthy Smiles',
      icon: Smile,
    },
    {
      name: 'Home Care',
      subtitle: 'Clean & Safe',
      icon: Home,
    },
    {
      name: 'Foods',
      subtitle: 'Nutrition & Taste',
      icon: UtensilsCrossed,
    },
  ];

  return (
    <aside className="dabur-sidebar">
      {/* Top Primary Navigation */}
      <nav className="sidebar-nav-list">
        <button
          className={`sidebar-nav-item ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => onSelectTab && onSelectTab('chat')}
        >
          <MessageSquare size={17} className="nav-icon" />
          <span>Chat</span>
          <Sparkles size={14} className="nav-sparkle" />
        </button>

        <button
          className={`sidebar-nav-item ${activeTab === 'sources' ? 'active' : ''}`}
          onClick={() => {
            if (onOpenSourcesModal) onOpenSourcesModal();
            else if (onSelectTab) onSelectTab('sources');
          }}
        >
          <Layers size={17} className="nav-icon" />
          <span>Sources</span>
        </button>

        <button
          className={`sidebar-nav-item ${activeTab === 'knowledge' ? 'active' : ''}`}
          onClick={() => onSelectTab && onSelectTab('knowledge')}
        >
          <BookOpen size={17} className="nav-icon" />
          <span>Knowledge Hub</span>
        </button>

        <button
          className={`sidebar-nav-item ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => onSelectTab && onSelectTab('history')}
        >
          <Clock size={17} className="nav-icon" />
          <span>History</span>
        </button>

        <button
          className={`sidebar-nav-item ${activeTab === 'settings' ? 'active' : ''}`}
          onClick={() => onSelectTab && onSelectTab('settings')}
        >
          <Settings size={17} className="nav-icon" />
          <span>Settings</span>
        </button>
      </nav>

      {/* Our Business Section */}
      <div className="business-units-section">
        <span className="business-section-title">Our Business</span>

        {businessUnits.map((bu, idx) => {
          const IconComp = bu.icon;
          return (
            <div key={idx} className="business-unit-item">
              <div className="bu-icon-badge">
                <IconComp size={15} />
              </div>
              <div className="bu-meta">
                <span className="bu-name">{bu.name}</span>
                <span className="bu-subtitle">{bu.subtitle}</span>
              </div>
            </div>
          );
        })}
      </div>

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
