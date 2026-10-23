import React, { useEffect, useRef, useState } from 'react';
import {
  Mail,
  ListChecks,
  Calendar,
  HardDrive,
  ArrowRight,
  ArrowUpRight,
  Paperclip,
  Mic,
  Send,
  Plus,
  ChevronDown,
  Database,
  GitBranch,
  Folder,
  GraduationCap,
  MessageSquare,
  FileText,
} from 'lucide-react';
import { ChatMessage, ConnectorSource } from '../types/chat';
import { MessageBubble } from './MessageBubble';
import { CerebroBrainLogo } from './CerebroBrainLogo';

interface ChatWindowProps {
  messages: ChatMessage[];
  sources?: ConnectorSource[];
  onSendMessage: (content: string) => void;
  onOpenAddSources?: () => void;
  isLoading?: boolean;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({
  messages,
  sources = [],
  onSendMessage,
  onOpenAddSources,
  isLoading = false,
}) => {
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isLoading) return;
    onSendMessage(inputText.trim());
    setInputText('');
  };

  // Quick Action Cards matching the reference image
  const quickActions = [
    {
      id: 'email-briefing',
      title: 'Latest Email Briefing',
      desc: 'Check your newest email and extract pending actions',
      prompt: 'What is in my last email?',
      icon: Mail,
      iconBg: 'rgba(239, 68, 68, 0.18)',
      iconColor: '#F87171',
    },
    {
      id: 'action-items',
      title: 'Action Items & Decisions',
      desc: 'Scan recent emails and discussions for approvals and deadlines',
      prompt: 'Summarize key updates and pending action items from my recent emails.',
      icon: ListChecks,
      iconBg: 'rgba(16, 185, 129, 0.18)',
      iconColor: '#34D399',
    },
    {
      id: 'catch-up',
      title: '3-Day Absence Catch-up',
      desc: 'Get prioritized delta updates from the last 3 days',
      prompt: 'I was away for 3 days. What happened while I was away?',
      icon: Calendar,
      iconBg: 'rgba(56, 189, 248, 0.18)',
      iconColor: '#38BDF8',
    },
    {
      id: 'drive-docs',
      title: 'Drive Documents',
      desc: 'Retrieve and inspect latest modified files in Google Drive',
      prompt: 'Search Google Drive for latest project files.',
      icon: FileText,
      iconBg: 'rgba(245, 158, 11, 0.18)',
      iconColor: '#FBBF24',
    },
  ];

  // Connected source chips for bottom of composer (Gmail, Google Chat, SQL Database, GitHub, File Share, LMS)
  const composerSourceChips = [
    { id: 'gmail', name: 'Gmail', icon: <Mail size={12} color="#EA4335" /> },
    { id: 'google_chat', name: 'Google Chat', icon: <MessageSquare size={12} color="#10B981" /> },
    { id: 'postgres', name: 'SQL Database', icon: <Database size={12} color="#38BDF8" /> },
    { id: 'github', name: 'GitHub', icon: <GitBranch size={12} color="#E2E8F0" /> },
    { id: 'file_share', name: 'File Share', icon: <Folder size={12} color="#06B6D4" /> },
    { id: 'lms', name: 'LMS', icon: <GraduationCap size={12} color="#F97316" /> },
  ];

  // Recent Activity items matching reference layout
  const recentActivities = [
    {
      id: 'act-1',
      title: 'Marketing Strategy v2',
      source: 'Google Drive',
      time: '2h ago',
      desc: 'You opened and analysed this document.',
      icon: HardDrive,
      iconColor: '#FBBF24',
      prompt: 'Summarize the Marketing Strategy v2 document in Google Drive.',
    },
    {
      id: 'act-2',
      title: 'Client Follow-up',
      source: 'Gmail',
      time: '4h ago',
      desc: '3 pending replies identified.',
      icon: Mail,
      iconColor: '#EA4335',
      prompt: 'Show details about client follow-up emails and pending replies.',
    },
    {
      id: 'act-3',
      title: 'Data Analysis Report',
      source: 'SQL Database',
      time: '1d ago',
      desc: 'Ran a query and generated insights.',
      icon: Database,
      iconColor: '#38BDF8',
      prompt: 'Show data analysis report from SQL Database.',
    },
    {
      id: 'act-4',
      title: 'Product Roadmap',
      source: 'Notion',
      time: '1d ago',
      desc: 'Reviewed and extracted action items.',
      icon: FileText,
      iconColor: '#E2E8F0',
      prompt: 'Search Notion for the Product Roadmap action items.',
    },
  ];

  return (
    <main className="cerebro-workspace-root">
      {/* Scrollable Container */}
      <div className="cerebro-workspace-scroll">
        <div className="cerebro-workspace-inner">
          {messages.length === 0 ? (
            /* ===================================================
               HERO & DASHBOARD (MATCHING TARGET REFERENCE SCREENSHOT)
               =================================================== */
            <div className="cerebro-hero-dashboard">
              {/* Central Glowing Brain & Greeting */}
              <div className="cerebro-hero-center">
                <CerebroBrainLogo size={76} showGlow={true} />
                <h1 className="hero-greeting">
                  Good day, <span className="greeting-emerald">Shashvat</span>
                </h1>
                <p className="hero-subtitle">
                  Your AI workspace connected across Gmail, Google Drive, Slack, SQL Database,
                  Notion, and GitHub.
                </p>
              </div>

              {/* Four Horizontal Action Cards */}
              <div className="hero-action-cards-grid">
                {quickActions.map((item) => {
                  const IconComponent = item.icon;
                  return (
                    <div
                      key={item.id}
                      className="hero-action-card"
                      onClick={() => onSendMessage(item.prompt)}
                    >
                      <div
                        className="action-card-icon-container"
                        style={{ background: item.iconBg, color: item.iconColor }}
                      >
                        <IconComponent size={18} />
                      </div>
                      <h3 className="action-card-title">{item.title}</h3>
                      <p className="action-card-desc">{item.desc}</p>
                      <div className="action-card-arrow-circle">
                        <ArrowRight size={13} />
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Wide Floating Chat Composer */}
              <div className="hero-composer-section">
                <form className="hero-composer-glass-bar" onSubmit={handleSubmit}>
                  <button
                    type="button"
                    className="composer-action-icon-btn"
                    title="Attach file"
                    aria-label="Attach file"
                  >
                    <Paperclip size={18} />
                  </button>

                  <input
                    type="text"
                    className="hero-composer-input"
                    placeholder='Ask anything... (e.g. "Find emails from marketing about Chyawanprash launch")'
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    disabled={isLoading}
                  />

                  <div className="composer-right-actions">
                    <button
                      type="button"
                      className="composer-action-icon-btn mic-btn"
                      title="Voice input"
                      aria-label="Voice input"
                    >
                      <Mic size={18} />
                    </button>

                    <button
                      type="submit"
                      className="composer-mint-send-btn"
                      disabled={!inputText.trim() || isLoading}
                      title="Send message"
                      aria-label="Send message"
                    >
                      <Send size={15} />
                    </button>
                  </div>
                </form>

                {/* Source Selection Chips Row */}
                <div className="composer-sources-row">
                  {composerSourceChips.map((chip) => (
                    <button
                      key={chip.id}
                      type="button"
                      className="composer-source-pill"
                      onClick={() => onSendMessage(`Search in ${chip.name}`)}
                    >
                      <span className="source-pill-icon">{chip.icon}</span>
                      <span className="source-pill-label">{chip.name}</span>
                      <ChevronDown size={12} className="source-pill-chevron" />
                    </button>
                  ))}

                  <button
                    type="button"
                    className="composer-connect-sources-btn"
                    onClick={onOpenAddSources}
                  >
                    <Plus size={13} />
                    <span>Connect sources</span>
                  </button>
                </div>
              </div>

              {/* Bottom Dashboard: Recent Activity & Upcoming Cards */}
              <div className="hero-bottom-dashboard-grid">
                {/* 1. Recent Activity Panel (Left, 4 cards) */}
                <div className="dashboard-glass-panel recent-activity-panel">
                  <div className="dashboard-panel-header">
                    <div className="panel-header-left">
                      <span className="live-status-dot-emerald" />
                      <h4 className="panel-title">Recent Activity</h4>
                    </div>
                    <button
                      type="button"
                      className="panel-view-all-btn"
                      onClick={() => onSendMessage('Show recent activity across connected sources.')}
                    >
                      <span>View all</span>
                      <ArrowRight size={13} />
                    </button>
                  </div>

                  <div className="activity-cards-row">
                    {recentActivities.map((act) => {
                      const ActIcon = act.icon;
                      return (
                        <div
                          key={act.id}
                          className="activity-sub-card"
                          onClick={() => onSendMessage(act.prompt)}
                          title={`Click to inspect ${act.title}`}
                        >
                          <div className="activity-card-top">
                            <div className="activity-icon-wrap">
                              <ActIcon size={14} color={act.iconColor} />
                            </div>
                            <div className="activity-meta-col">
                              <span className="activity-item-title">{act.title}</span>
                              <span className="activity-item-sub">
                                {act.source} • {act.time}
                              </span>
                            </div>
                          </div>
                          <p className="activity-item-desc">{act.desc}</p>
                          <div className="activity-corner-arrow">
                            <ArrowUpRight size={14} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* 2. Upcoming Panel (Right) */}
                <div className="dashboard-glass-panel upcoming-panel">
                  <div className="dashboard-panel-header">
                    <div className="panel-header-left">
                      <Calendar size={15} color="#38BDF8" />
                      <h4 className="panel-title">Upcoming</h4>
                    </div>
                    <button
                      type="button"
                      className="panel-view-all-btn"
                      onClick={() => onSendMessage('What upcoming deadlines and meetings do I have?')}
                    >
                      <span>View all</span>
                      <ArrowRight size={13} />
                    </button>
                  </div>

                  <div className="upcoming-events-list">
                    <div
                      className="upcoming-event-item"
                      onClick={() => onSendMessage('Show details about Project Review tomorrow')}
                    >
                      <span className="upcoming-dot dot-red" />
                      <div className="upcoming-info">
                        <span className="upcoming-title">Project Review</span>
                        <span className="upcoming-time">Tomorrow, 10:00 AM</span>
                      </div>
                    </div>

                    <div
                      className="upcoming-event-item"
                      onClick={() => onSendMessage('Show details about Client Submission this Friday')}
                    >
                      <span className="upcoming-dot dot-amber" />
                      <div className="upcoming-info">
                        <span className="upcoming-title">Client Submission</span>
                        <span className="upcoming-time">Fri, 4:00 PM</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            /* ===================================================
               IN-CHAT CONVERSATION STREAM
               =================================================== */
            <div className="cerebro-chat-stream">
              {messages.map((msg) => (
                <MessageBubble
                  key={msg.id}
                  message={msg}
                  onFollowupClick={(prompt) => onSendMessage(prompt)}
                />
              ))}

              {isLoading && (
                <div className="assistant-message-row">
                  <div className="assistant-avatar-badge">
                    <CerebroBrainLogo size={22} showGlow={true} />
                  </div>
                  <div className="assistant-content-wrapper">
                    <div className="assistant-bubble-card searching-indicator-card">
                      <div className="searching-pulse-row">
                        <span className="searching-spinner" />
                        <span className="searching-text">
                          Cerebro is scanning and synthesizing enterprise knowledge...
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Floating Composer when active in conversation */}
      {messages.length > 0 && (
        <div className="active-chat-composer-bar">
          <form className="hero-composer-glass-bar active-bar" onSubmit={handleSubmit}>
            <button
              type="button"
              className="composer-action-icon-btn"
              title="Attach file"
              aria-label="Attach file"
            >
              <Paperclip size={18} />
            </button>

            <input
              type="text"
              className="hero-composer-input"
              placeholder='Ask anything... (e.g. "Find emails from marketing about Chyawanprash launch")'
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              disabled={isLoading}
            />

            <div className="composer-right-actions">
              <button
                type="button"
                className="composer-action-icon-btn mic-btn"
                title="Voice input"
                aria-label="Voice input"
              >
                <Mic size={18} />
              </button>

              <button
                type="submit"
                className="composer-mint-send-btn"
                disabled={!inputText.trim() || isLoading}
                title="Send message"
                aria-label="Send message"
              >
                <Send size={15} />
              </button>
            </div>
          </form>
        </div>
      )}
    </main>
  );
};
