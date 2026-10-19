import React from 'react';
import {
  Sparkles,
  User,
  CheckCheck,
  FileText,
  ExternalLink,
  Users,
  Link2,
  CheckCircle2,
  Mail,
  FolderGit2,
  Paperclip,
  Download,
} from 'lucide-react';
import { ChatMessage, RichCard, SourceAccessed } from '../types/chat';

interface MessageBubbleProps {
  message: ChatMessage;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="message-row user-row">
        <div className="user-message-bubble">
          <p className="message-text">{message.content}</p>
          <div className="message-meta-user">
            <span>{message.timestamp}</span>
            <CheckCheck size={14} className="checkmarks" />
          </div>
        </div>
        <div className="user-avatar-circle">
          <User size={16} className="text-white" />
        </div>
      </div>
    );
  }

  // Format assistant text with simple markdown formatting (bullet points, bold)
  const renderFormattedText = (text: string) => {
    const lines = text.split('\n');
    return lines.map((line, lIdx) => {
      // Check for bullet line
      const trimmed = line.trim();
      const isBullet = trimmed.startsWith('- ') || trimmed.startsWith('* ');
      const rawLine = isBullet ? trimmed.slice(2) : line;
      // Clean backslash escaped characters like \< and \>
      const cleanLine = rawLine.replace(/\\([<>])/g, '$1');

      // Simple bold replacement (**word**)
      const parts = cleanLine.split(/(\*\*[^*]+\*\*)/g);
      const renderedParts = parts.map((part, pIdx) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={pIdx} className="font-semibold text-white">{part.slice(2, -2)}</strong>;
        }
        return part;
      });

      if (isBullet) {
        return (
          <li key={lIdx} className="ml-4 list-disc my-1">
            {renderedParts}
          </li>
        );
      }

      if (trimmed === '---') {
        return <hr key={lIdx} className="my-3 border-gray-700/50" />;
      }

      return (
        <p key={lIdx} className="mb-2 min-h-[1.2rem]">
          {renderedParts}
        </p>
      );
    });
  };

  // Assistant Message
  return (
    <div className="message-row assistant-row">
      <div className="assistant-avatar-circle">
        <Sparkles size={18} className="sparkle-ai-icon" />
      </div>

      <div className="assistant-message-content">
        <div className="assistant-main-text">{renderFormattedText(message.content)}</div>

        {/* Rich Cards (Documents, Emails, Repos, Teams) */}
        {message.rich_cards && message.rich_cards.length > 0 && (
          <div className="rich-cards-container">
            {message.rich_cards.map((card, idx) => (
              <div key={idx} className="rich-card-wrapper">
                {/* 1. Document Card */}
                {card.type === 'document' && (
                  <div className="rich-card document-card">
                    <div className="card-header-label">
                      <FileText size={16} className="text-blue-accent" />
                      <span>{card.title || 'Document File'}</span>
                    </div>
                    <div className="card-inner-box">
                      <div className="card-file-type-icon doc-w-icon">W</div>
                      <div className="card-info">
                        <h4 className="card-item-title">
                          {card.snippet || card.title}
                        </h4>
                        <p className="card-item-sub">{card.metadata}</p>
                      </div>
                      {card.link && (
                        <button
                          className="card-action-btn"
                          onClick={() => window.open(card.link, '_blank')}
                        >
                          <span>{card.action_label || 'View File'}</span>
                          <ExternalLink size={14} />
                        </button>
                      )}
                    </div>
                  </div>
                )}

                {/* 2. Email Card */}
                {card.type === 'email' && (
                  <div className="rich-card email-card">
                    <div className="card-header-label">
                      <Mail size={16} className="text-red-400" />
                      <span>Gmail Message</span>
                    </div>
                    <div className="card-inner-box flex-col items-stretch gap-3">
                      <div className="flex items-center gap-3">
                        <div className="doc-w-icon !bg-red-600">M</div>
                        <div className="card-info">
                          <h4 className="card-item-title">{card.title}</h4>
                          <p className="card-item-sub">{card.metadata}</p>
                        </div>
                        {card.link && (
                          <button
                            className="card-action-btn !bg-red-500/10 !border-red-500/30 !text-red-400 hover:!bg-red-500/20"
                            onClick={() => window.open(card.link, '_blank')}
                          >
                            <span>{card.action_label || 'View Email'}</span>
                            <ExternalLink size={14} />
                          </button>
                        )}
                      </div>

                      {card.snippet && (
                        <div className="text-xs text-slate-300 italic bg-black/20 p-2.5 rounded border-l-2 border-red-500">
                          "{card.snippet}"
                        </div>
                      )}

                      {/* Attachments Section */}
                      {card.attachments && card.attachments.length > 0 && (
                        <div className="mt-2 pt-2 border-t border-white/5 flex flex-col gap-1.5">
                          <span className="text-[11px] font-semibold text-slate-400 flex items-center gap-1">
                            <Paperclip size={12} /> Attachments ({card.attachments.length})
                          </span>
                          <div className="flex flex-wrap gap-2">
                            {card.attachments.map((att, aIdx) => (
                              <button
                                key={aIdx}
                                className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs text-blue-400 border border-slate-700 transition"
                                onClick={() => window.open(att.download_url, '_blank')}
                                title="Download attachment"
                              >
                                <Download size={12} />
                                <span className="font-medium">{att.filename}</span>
                                <span className="text-[10px] text-slate-400">({att.size})</span>
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* 3. GitHub Repo Card */}
                {card.type === 'repo' && (
                  <div className="rich-card repo-card">
                    <div className="card-header-label">
                      <FolderGit2 size={16} className="text-emerald-400" />
                      <span>GitHub Repository</span>
                    </div>
                    <div className="card-inner-box">
                      <div className="doc-w-icon !bg-slate-800 !border !border-slate-700">G</div>
                      <div className="card-info">
                        <h4 className="card-item-title">{card.title}</h4>
                        <p className="card-item-sub">{card.metadata}</p>
                        {card.snippet && (
                          <p className="text-xs text-slate-400 mt-1 line-clamp-2">{card.snippet}</p>
                        )}
                      </div>
                      {card.link && (
                        <button
                          className="card-action-btn !bg-emerald-500/10 !border-emerald-500/30 !text-emerald-400 hover:!bg-emerald-500/20"
                          onClick={() => window.open(card.link, '_blank')}
                        >
                          <span>{card.action_label || 'View on GitHub'}</span>
                          <ExternalLink size={14} />
                        </button>
                      )}
                    </div>
                  </div>
                )}

                {/* 4. Teams Card */}
                {card.type === 'teams_message' && (
                  <div className="rich-card teams-card">
                    <div className="card-header-label">
                      <Users size={16} className="text-purple-accent" />
                      <span>{card.title || 'Related Teams Discussion'}</span>
                    </div>
                    <div className="card-inner-box">
                      <div className="teams-info-full">
                        <div className="teams-header-row">
                          <div>
                            <h4 className="card-item-title">
                              {card.source_name || 'Project Requirements - Discussion'}
                            </h4>
                            <p className="card-item-sub">
                              {card.metadata || 'Microsoft Teams • Apr 28, 2025, 2:34 PM'}
                            </p>
                          </div>
                          {card.link && (
                            <button
                              className="card-action-btn teams-btn"
                              onClick={() => window.open(card.link, '_blank')}
                            >
                              <Users size={14} />
                              <span>View in Teams</span>
                            </button>
                          )}
                        </div>
                        <p className="teams-quote-text">
                          {card.snippet ||
                            '"The updated requirements document has been shared. Please review and share your feedback by EOD tomorrow."'}
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Sources Accessed Section */}
        {message.sources_accessed && message.sources_accessed.length > 0 && (
          <div className="sources-accessed-container">
            <div className="sources-label">
              <Link2 size={15} className="text-muted" />
              <span>Sources Accessed</span>
            </div>
            <div className="sources-pills-grid">
              {message.sources_accessed.map((src, sIdx) => (
                <div key={sIdx} className="source-accessed-pill">
                  <div className="source-pill-icon">
                    {src.name === 'SharePoint' && <div className="mini-icon sp-mini">S</div>}
                    {src.name === 'Microsoft Teams' && <div className="mini-icon teams-mini">T</div>}
                    {src.name === 'Gmail' && <div className="mini-icon gmail-mini">M</div>}
                    {src.name === 'GitHub' && <div className="mini-icon gh-mini">G</div>}
                    {src.name === 'File Share' && <div className="mini-icon fs-mini">F</div>}
                    {src.name === 'LMS' && <div className="mini-icon lms-mini">L</div>}
                    {src.name === 'ServiceNow' && <div className="mini-icon sn-mini">N</div>}
                    {src.name === 'Salesforce' && <div className="mini-icon sf-mini">SF</div>}
                    {src.name === 'Google Drive' && <div className="mini-icon gdrive-mini">D</div>}
                    {src.name === 'Jira' && <div className="mini-icon jira-mini">J</div>}
                    {src.name === 'Azure DevOps' && <div className="mini-icon ado-mini">A</div>}
                    {!['SharePoint', 'Microsoft Teams', 'Gmail', 'GitHub', 'File Share', 'LMS', 'ServiceNow', 'Salesforce', 'Google Drive', 'Jira', 'Azure DevOps'].includes(src.name) && (
                      <div className="mini-icon bg-slate-700">{src.name.charAt(0)}</div>
                    )}
                  </div>
                  <div className="source-pill-text">
                    <span className="source-pill-name">{src.name}</span>
                    <span className="source-pill-sub">{src.status_text}</span>
                  </div>
                  <CheckCircle2 size={16} className={`source-pill-check ${src.verified ? 'text-emerald-400' : 'text-slate-500'}`} />
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="message-meta-assistant">
          <span>{message.timestamp}</span>
        </div>
      </div>
    </div>
  );
};

