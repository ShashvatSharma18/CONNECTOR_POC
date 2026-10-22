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

  // Comprehensive Markdown, Table, and List parser for assistant responses
  const parseInlineMarkdown = (text: string): React.ReactNode[] => {
    const parts: React.ReactNode[] = [];
    const regex = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;
    let lastIdx = 0;
    let match: RegExpExecArray | null;

    while ((match = regex.exec(text)) !== null) {
      if (match.index > lastIdx) {
        parts.push(text.substring(lastIdx, match.index));
      }
      const token = match[0];
      if (token.startsWith('**') && token.endsWith('**')) {
        parts.push(<strong key={match.index}>{token.slice(2, -2)}</strong>);
      } else if (token.startsWith('*') && token.endsWith('*')) {
        parts.push(<em key={match.index}>{token.slice(1, -1)}</em>);
      } else if (token.startsWith('`') && token.endsWith('`')) {
        parts.push(<code key={match.index} className="inline-code">{token.slice(1, -1)}</code>);
      } else if (token.startsWith('[') && token.includes('](')) {
        const linkMatch = token.match(/\[([^\]]+)\]\(([^)]+)\)/);
        if (linkMatch) {
          parts.push(
            <a key={match.index} href={linkMatch[2]} target="_blank" rel="noreferrer" className="content-link">
              {linkMatch[1]}
            </a>
          );
        } else {
          parts.push(token);
        }
      } else {
        parts.push(token);
      }
      lastIdx = regex.lastIndex;
    }
    if (lastIdx < text.length) {
      parts.push(text.substring(lastIdx));
    }
    return parts;
  };

  const renderFormattedContent = (content: string) => {
    if (!content) return null;

    // 1. Normalize linebreaks and row separators like "||" into newlines
    const normalized = content.replace(/\|\|+/g, '\n|');
    const rawLines = normalized.split('\n');

    const elements: React.ReactNode[] = [];
    let currentTableRows: string[][] = [];
    let currentListItems: string[] = [];
    let isNumberedList = false;

    const flushTable = (keyPrefix: string) => {
      if (currentTableRows.length === 0) return;
      const headerRow = currentTableRows[0];
      const bodyRows = currentTableRows.slice(1);

      elements.push(
        <div key={`table-${keyPrefix}`} className="table-responsive-wrapper">
          <table className="markdown-table">
            <thead>
              <tr>
                {headerRow.map((cell, cIdx) => (
                  <th key={cIdx}>{parseInlineMarkdown(cell)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {bodyRows.map((row, rIdx) => (
                <tr key={rIdx}>
                  {row.map((cell, cIdx) => (
                    <td key={cIdx}>{parseInlineMarkdown(cell)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      currentTableRows = [];
    };

    const flushList = (keyPrefix: string) => {
      if (currentListItems.length === 0) return;
      if (isNumberedList) {
        elements.push(
          <ol key={`ol-${keyPrefix}`} className="content-ol">
            {currentListItems.map((item, idx) => (
              <li key={idx} className="content-li">
                {parseInlineMarkdown(item)}
              </li>
            ))}
          </ol>
        );
      } else {
        elements.push(
          <ul key={`ul-${keyPrefix}`} className="content-ul">
            {currentListItems.map((item, idx) => (
              <li key={idx} className="content-li">
                {parseInlineMarkdown(item)}
              </li>
            ))}
          </ul>
        );
      }
      currentListItems = [];
      isNumberedList = false;
    };

    for (let i = 0; i < rawLines.length; i++) {
      const line = rawLines[i].trim();

      if (!line) {
        flushTable(`line-${i}`);
        flushList(`line-${i}`);
        continue;
      }

      // Check if line contains a markdown table row (has pipe)
      if (line.includes('|')) {
        flushList(`line-${i}`);

        // Check if there is lead text before the table on the same line
        const pipeIndex = line.indexOf('|');
        const leadText = line.substring(0, pipeIndex).trim();
        const tablePart = line.substring(pipeIndex);

        if (leadText) {
          flushTable(`pre-lead-${i}`);
          elements.push(
            <p key={`lead-${i}`} className="assistant-lead-text">
              {parseInlineMarkdown(leadText)}
            </p>
          );
        }

        // Check if it's a separator line (e.g. | ------------- | ----------- |)
        const isSeparator = /^\|?[\s\-:]+(\|[\s\-:]+)+\|?$/.test(tablePart.trim());
        if (isSeparator) {
          continue;
        }

        // Split row into cells
        const cells = tablePart
          .split('|')
          .map((c) => c.trim())
          .filter((c, idx, arr) => {
            if (idx === 0 && c === '') return false;
            if (idx === arr.length - 1 && c === '') return false;
            return true;
          });

        if (cells.length > 0) {
          currentTableRows.push(cells);
        }
        continue;
      }

      // Not a table line, flush pending table
      flushTable(`line-${i}`);

      // Horizontal dividers (---, ___, ***)
      if (/^[-*_]{3,}$/.test(line)) {
        flushList(`hr-${i}`);
        elements.push(<div key={`hr-${i}`} className="content-divider" />);
        continue;
      }

      // Headers (# to ######)
      if (/^#{1,6}\s+/.test(line)) {
        flushList(`line-${i}`);
        const headerMatch = line.match(/^(#{1,6})\s+(.*)$/);
        if (headerMatch) {
          const level = headerMatch[1].length;
          const text = headerMatch[2];
          if (level === 1) {
            elements.push(
              <h2 key={`h1-${i}`} className="content-h1">
                {parseInlineMarkdown(text)}
              </h2>
            );
          } else if (level === 2) {
            elements.push(
              <h3 key={`h2-${i}`} className="content-h2">
                {parseInlineMarkdown(text)}
              </h3>
            );
          } else if (level === 3) {
            elements.push(
              <h4 key={`h3-${i}`} className="content-h3">
                {parseInlineMarkdown(text)}
              </h4>
            );
          } else if (level === 4) {
            elements.push(
              <h5 key={`h4-${i}`} className="content-h4">
                {parseInlineMarkdown(text)}
              </h5>
            );
          } else {
            elements.push(
              <h6 key={`h5-${i}`} className="content-h5">
                {parseInlineMarkdown(text)}
              </h6>
            );
          }
          continue;
        }
      }

      if (/^[-*•]\s+/.test(line)) {
        // Bullet list item
        if (isNumberedList) flushList(`num-to-bullet-${i}`);
        currentListItems.push(line.replace(/^[-*•]\s+/, ''));
      } else if (/^\d+[\.)]\s+/.test(line)) {
        // Numbered list item
        if (!isNumberedList) flushList(`bullet-to-num-${i}`);
        isNumberedList = true;
        currentListItems.push(line.replace(/^\d+[\.)]\s+/, ''));
      } else {
        // Regular paragraph text
        flushList(`para-${i}`);
        elements.push(
          <p key={`p-${i}`} className="assistant-lead-text">
            {parseInlineMarkdown(line)}
          </p>
        );
      }
    }

    flushTable('final');
    flushList('final');

    return elements;
  };

  return (
    <div className="assistant-message-row">
      <div className="assistant-avatar-badge">
        <DaburLeafIcon />
      </div>

      <div className="assistant-content-wrapper">
        <div className="assistant-bubble-card">
          <div className="assistant-card-header">
            <div className="assistant-card-identity">
              <span className="assistant-card-name">Dabur One</span>
              <span className="assistant-card-badge">Enterprise RAG</span>
            </div>
            {message.timestamp && (
              <span className="assistant-card-time">{message.timestamp}</span>
            )}
          </div>

          {/* Main lead text / structured markdown */}
          <div className="assistant-lead-block">
            {renderFormattedContent(message.content)}
          </div>

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
                          onClick={() => {
                            const rawLink = card.link || '';
                            const target = rawLink.includes('mail.google.com')
                              ? rawLink
                              : (rawLink.match(/\/gmail\/messages\/([a-zA-Z0-9]+)/)
                                  ? `https://mail.google.com/mail/#all/${rawLink.match(/\/gmail\/messages\/([a-zA-Z0-9]+)/)![1]}`
                                  : rawLink || 'https://mail.google.com');
                            window.open(target, '_blank', 'noopener,noreferrer');
                          }}
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
                      onClick={() => {
                        const rawLink = card.link || '';
                        const target = rawLink.includes('mail.google.com')
                          ? rawLink
                          : (rawLink.match(/\/gmail\/messages\/([a-zA-Z0-9]+)/)
                              ? `https://mail.google.com/mail/#all/${rawLink.match(/\/gmail\/messages\/([a-zA-Z0-9]+)/)![1]}`
                              : rawLink || 'https://mail.google.com');
                        window.open(target, '_blank', 'noopener,noreferrer');
                      }}
                      title="Open this email in Gmail"
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
    </div>
  );
};
