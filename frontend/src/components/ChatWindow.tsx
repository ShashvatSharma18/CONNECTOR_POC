import React, { useEffect, useRef } from 'react';
import { ShieldCheck } from 'lucide-react';
import { ChatMessage } from '../types/chat';
import { MessageBubble } from './MessageBubble';
import { MessageComposer } from './MessageComposer';

interface ChatWindowProps {
  messages: ChatMessage[];
  onSendMessage: (content: string) => void;
  onOpenAddSources?: () => void;
  isLoading?: boolean;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({
  messages,
  onSendMessage,
  onOpenAddSources,
  isLoading = false,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

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
            <h2>Dabur One</h2>
            <p>Your AI workplace assistant for smarter, faster search across all your connected tools.</p>
          </div>
        </div>

        <div className="enterprise-badge">
          <ShieldCheck size={14} />
          <span>Enterprise</span>
        </div>
      </header>

      {/* Messages Scroll Area */}
      <div className="chat-messages-container">
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
              <div
                style={{
                  background: '#FFFFFF',
                  padding: '12px 18px',
                  borderRadius: '12px',
                  border: '1px solid #E2E8F0',
                  fontSize: '13px',
                  color: '#164E33',
                  fontWeight: 500,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  boxShadow: '0 2px 6px rgba(0,0,0,0.03)',
                }}
              >
                <span>Searching connected enterprise sources...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Bottom Composer */}
      <MessageComposer
        onSendMessage={onSendMessage}
        onOpenAddSources={onOpenAddSources}
        disabled={isLoading}
      />
    </main>
  );
};
