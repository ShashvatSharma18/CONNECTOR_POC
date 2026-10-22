import React from 'react';
import {
  User,
  CheckCheck,
  ExternalLink,
  Mail,
  FileText,
  Database,
  Hash,
  HardDrive,
} from 'lucide-react';
import { ChatMessage, RichCard } from '../types/chat';

interface MessageBubbleProps {
  message: ChatMessage;
  onFollowupClick?: (prompt: string) => void;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  onFollowupClick,
}) => {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="user-message-row">
        <div className="user-bubble">
          <p className="user-bubble-text">{message.content}</p>
          <div className="user-bubble-meta">
            <span>{message.timestamp}</span>
            <CheckCheck size={14} />
          </div>
        </div>
        <div className="user-avatar-icon">
          <User size={17} />
        </div>
      </div>
    );
  }

  // Assistant Message Avatar - Dabur Leaf
  const DaburLeafIcon = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
      <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" />
      <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12" />
    </svg>
  );

  // Email sender initials palette
  const getAvatarColor = (initials: string = 'AP') => {
    switch (initials) {
      case 'AP':
        return '#EF4444'; // Coral / Red
      case 'RK':
        return '#3B82F6'; // Blue
      case 'PS':
        return '#0D9488'; // Teal
      case 'VG':
        return '#F59E0B'; // Amber
      default:
        return '#164E33'; // Forest Green
    }
  };

  return (
    <div className="assistant-message-row">
      <div className="assistant-avatar-badge">
        <DaburLeafIcon />
      </div>

      <div className="assistant-content-wrapper">
        {/* Main lead text */}
        <p className="assistant-lead-text">{message.content}</p>

        {/* Source metadata pill */}
        {message.rich_cards && message.rich_cards.length > 0 && (
          <div className="assistant-source-header">
            <span className="source-tag-pill">
              <Mail size={13} color="#EA4335" />
              <span>Gmail</span>
            </span>
            <span>{message.rich_cards.length} relevant emails found • Latest first</span>
          </div>
        )}

        {/* Cards List */}
        {message.rich_cards && message.rich_cards.length > 0 && (
          <div className="cards-list">
            {message.rich_cards.map((card, idx) => {
              const initials = card.sender_initials || (card.title.slice(0, 2).toUpperCase());
              const avatarBg = card.badge_color || getAvatarColor(initials);
              const dept = card.department || 'General';

              return (
                <div key={idx} className="email-result-card">
                  <div className="card-left-group">
                    {/* Service Icon */}
                    <Mail size={16} color="#EA4335" className="card-service-icon" />

                    {/* Sender Initials Avatar */}
                    <div
                      className="sender-initials-badge"
                      style={{ background: avatarBg }}
                    >
                      {initials}
                    </div>

                    {/* Subject, sender, snippet */}
                    <div className="card-details-column">
                      <div className="card-title-row">
                        <span
                          className="card-subject"
                          onClick={() => card.link && window.open(card.link, '_blank')}
                        >
                          {card.title}
                        </span>
                      </div>

                      <div className="card-sender-meta">
                        <span>{card.sender_name || 'Marketing'}</span>
                        {card.date_str && <span> • {card.date_str}</span>}
                      </div>

                      {card.snippet && (
                        <p className="card-snippet-text">{card.snippet}</p>
                      )}
                    </div>
                  </div>

                  {/* Right Side: View email & department badge */}
                  <div className="card-right-group">
                    <button
                      className="btn-view-email"
                      onClick={() => card.link && window.open(card.link, '_blank')}
                    >
                      <span>{card.action_label || 'View email'}</span>
                      <ExternalLink size={12} />
                    </button>

                    <span className="department-badge">{dept}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Summary & Pending Actions Box */}
        {message.summary_block && (
          <div className="summary-actions-box">
            <div className="summary-header-row">
              <div className="summary-header-icon">
                <FileText size={16} />
              </div>
              <h3>Summary &amp; Pending Actions</h3>
            </div>

            <div className="summary-columns-grid">
              {/* Key Updates */}
              <div className="summary-col">
                <h4>Key Updates</h4>
                <ul className="summary-bullets-list">
                  {message.summary_block.key_updates.map((update, uIdx) => (
                    <li key={uIdx} className="summary-bullet-item">
                      {update}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Pending Actions */}
              <div className="summary-col">
                <h4>Pending Actions</h4>
                <ul className="pending-actions-list">
                  {message.summary_block.pending_actions.map((action, aIdx) => (
                    <li key={aIdx} className="pending-action-item">
                      <span className="action-num-badge">{aIdx + 1}</span>
                      <span>{action}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="summary-footer-meta">
              <span>{message.summary_block.source_summary || 'Source: 5 emails • Gmail'}</span>
            </div>
          </div>
        )}

        {/* Suggested Follow-Ups */}
        {message.suggested_followups && message.suggested_followups.length > 0 && (
          <div className="suggested-followups-container">
            <span className="followups-title">Suggested follow-ups</span>
            <div className="followups-pills-row">
              {message.suggested_followups.map((prompt, fIdx) => (
                <button
                  key={fIdx}
                  className="followup-pill-btn"
                  onClick={() => onFollowupClick && onFollowupClick(prompt)}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
