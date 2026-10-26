import React, { useEffect, useRef, useState } from 'react';
import {
  ShieldCheck,
  Sparkles,
  Mail,
  Calendar,
  HardDrive,
  ArrowRight,
  Bot,
  FileSearch,
  FileSpreadsheet,
  X,
} from 'lucide-react';
import { ChatMessage, ConnectorSource, ActiveDocumentState } from '../types/chat';
import { MessageBubble } from './MessageBubble';
import { MessageComposer } from './MessageComposer';
import { DocumentPreviewModal } from './DocumentPreviewModal';

interface ChatWindowProps {
  messages: ChatMessage[];
  sources?: ConnectorSource[];
  activeDocument?: ActiveDocumentState | null;
  onAttachDocument?: (doc: ActiveDocumentState) => void;
  onClearActiveDocument?: () => void;
  onSendMessage: (content: string) => void;
  onOpenAddSources?: () => void;
  isLoading?: boolean;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({
  messages,
  sources = [],
  activeDocument,
  onAttachDocument,
  onClearActiveDocument,
  onSendMessage,
  onOpenAddSources,
  isLoading = false,
}) => {
  const [showActiveDocModal, setShowActiveDocModal] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const quickPrompts = [
    {
      icon: Mail,
      title: 'Latest Email Briefing',
      desc: 'Check your newest email and extract pending actions',
      prompt: 'What is in my last email?',
      color: '#EA4335',
    },
    {
      icon: Sparkles,
      title: 'Action Items & Decisions',
      desc: 'Scan recent emails and discussions for approvals and deadlines',
      prompt: 'Summarize key updates and pending action items from my recent emails.',
      color: '#164E33',
    },
    {
      icon: Calendar,
      title: '3-Day Absence Catch-up',
      desc: 'Get prioritized delta updates from the last 3 days',
      prompt: 'I was away for 3 days. What happened while I was away?',
      color: '#0284C7',
    },
    {
      icon: HardDrive,
      title: 'Drive Documents',
      desc: 'Retrieve and inspect latest modified files in Google Drive',
      prompt: 'Search Google Drive for latest project files.',
      color: '#D97706',
    },
    {
      icon: FileSearch,
      title: 'Universal Document Parser',
      desc: 'Multimodal ensemble: PDF, Word, Excel, OCR & Table Grounding',
      prompt: 'Tell me about the Universal Document Parser capabilities and how to use it.',
      color: '#059669',
    },
  ];

  return (
    <main className="chat-workspace">
      {/* Top Banner inside Chat */}
      <header className="chat-banner">
        <div className="banner-left">
          <div className="banner-leaf-badge">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
              <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" />
              <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12" />
            </svg>
          </div>
          <div className="banner-text">
            <h2>Cerebro</h2>
            <p>Enterprise AI Workplace Assistant • Verified RAG Multi-Source Search</p>
          </div>
        </div>

        <div className="enterprise-badge">
          <ShieldCheck size={14} />
          <span>Enterprise Secure</span>
        </div>
      </header>

      {/* Active Document Session Strip (Persistent Context) */}
      {activeDocument && (
        <div className="chat-active-document-strip">
          <div
            className="active-doc-left clickable"
            onClick={() => setShowActiveDocModal(true)}
            title="Click to view full extracted document text"
            style={{ cursor: 'pointer' }}
          >
            <div className="active-doc-icon-badge">
              <FileSpreadsheet size={15} />
            </div>
            <div className="active-doc-meta-text">
              <span className="active-doc-label">Active Document in Context:</span>
              <span className="active-doc-name">{activeDocument.filename}</span>
              <span className="active-doc-counts">
                ({activeDocument.elements_count || 0} elements
                {activeDocument.tables && activeDocument.tables.length > 0
                  ? `, ${activeDocument.tables.length} tables`
                  : ''}
                )
              </span>
            </div>
          </div>
          <button
            type="button"
            className="btn-detach-doc"
            onClick={onClearActiveDocument}
            title="Detach document from this chat session"
          >
            <X size={13} />
            <span>Detach</span>
          </button>
        </div>
      )}

      {/* Messages Scroll Area */}
      <div className="chat-messages-container">
        <div className="chat-content-container">
          {messages.length === 0 ? (
            <div className="chat-welcome-hero">
              <div className="welcome-leaf-circle">
                <svg width="34" height="34" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" />
                  <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12" />
                </svg>
              </div>

              <h1 className="welcome-title">Good day, Shashvat</h1>
              <p className="welcome-subtitle">
                Ask anything across your connected Gmail, Google Drive, Slack, SQL Database, Notion, and GitHub.
              </p>

              <div className="quick-prompts-grid">
                {quickPrompts.map((item, idx) => {
                  const IconC = item.icon;
                  return (
                    <div
                      key={idx}
                      className="quick-prompt-card"
                      onClick={() => onSendMessage(item.prompt)}
                    >
                      <div className="quick-prompt-top">
                        <div
                          className="prompt-icon-badge"
                          style={{ color: item.color, background: `${item.color}15` }}
                        >
                          <IconC size={18} />
                        </div>
                        <ArrowRight size={14} className="prompt-arrow-icon" />
                      </div>
                      <h4 className="prompt-card-title">{item.title}</h4>
                      <p className="prompt-card-desc">{item.desc}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="messages-stream">
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
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" />
                      <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12" />
                    </svg>
                  </div>
                  <div className="assistant-content-wrapper">
                    <div className="assistant-bubble-card searching-indicator-card">
                      <div className="searching-pulse-row">
                        <span className="searching-spinner"></span>
                        <span className="searching-text">
                          Retrieving and synthesizing enterprise knowledge...
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

      {/* Bottom Composer */}
      <div className="chat-composer-outer">
        <div className="chat-content-container">
          <MessageComposer
            sources={sources}
            activeDocument={activeDocument}
            onAttachDocument={onAttachDocument}
            onClearActiveDocument={onClearActiveDocument}
            onSendMessage={onSendMessage}
            onOpenAddSources={onOpenAddSources}
            disabled={isLoading}
          />
        </div>
      </div>

      {showActiveDocModal && activeDocument && (
        <DocumentPreviewModal
          document={{
            title: activeDocument.filename,
            filename: activeDocument.filename,
            text: activeDocument.text || '',
            elements_count: activeDocument.elements_count,
            tables: activeDocument.tables,
            duration_ms: activeDocument.duration_ms,
          }}
          onClose={() => setShowActiveDocModal(false)}
        />
      )}
    </main>
  );
};
