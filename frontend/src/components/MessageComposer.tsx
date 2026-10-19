import React, { useState } from 'react';
import {
  Paperclip,
  ArrowUp,
  Search,
  Folder,
  MessageSquare,
  GitBranch,
} from 'lucide-react';

interface MessageComposerProps {
  onSendMessage: (content: string) => void;
  disabled?: boolean;
}

export const MessageComposer: React.FC<MessageComposerProps> = ({
  onSendMessage,
  disabled = false,
}) => {
  const [input, setInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || disabled) return;
    onSendMessage(input.trim());
    setInput('');
  };

  const handleSuggestedPrompt = (prompt: string) => {
    if (disabled) return;
    onSendMessage(prompt);
  };

  return (
    <div className="composer-container">
      {/* Floating Input Pill */}
      <form className="composer-input-pill" onSubmit={handleSubmit}>
        <button
          type="button"
          className="composer-icon-btn"
          title="Attach file or context"
        >
          <Paperclip size={18} />
        </button>

        <input
          type="text"
          className="composer-text-input"
          placeholder="Ask a question about your connected sources..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={disabled}
        />

        <button
          type="submit"
          className={`composer-send-btn ${input.trim() ? 'active' : ''}`}
          disabled={!input.trim() || disabled}
          title="Send message"
        >
          <ArrowUp size={18} />
        </button>
      </form>

      {/* Suggested Prompts below input */}
      <div className="suggested-prompts-row">
        <button
          type="button"
          className="prompt-pill-btn"
          onClick={() =>
            handleSuggestedPrompt('Search across all sources for project status')
          }
        >
          <Search size={14} />
          <span>Search across all sources</span>
        </button>

        <button
          type="button"
          className="prompt-pill-btn"
          onClick={() => handleSuggestedPrompt('Find recent files in File Share and SharePoint')}
        >
          <Folder size={14} />
          <span>Find recent files</span>
        </button>

        <button
          type="button"
          className="prompt-pill-btn"
          onClick={() => handleSuggestedPrompt('Check Teams messages for announcements')}
        >
          <MessageSquare size={14} />
          <span>Check Teams messages</span>
        </button>

        <button
          type="button"
          className="prompt-pill-btn"
          onClick={() => handleSuggestedPrompt('Show GitHub repos and latest commits')}
        >
          <GitBranch size={14} />
          <span>Show GitHub repos</span>
        </button>
      </div>
    </div>
  );
};
