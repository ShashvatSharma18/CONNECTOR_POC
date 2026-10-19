import React, { useEffect, useRef } from 'react';
import { Sparkles, ChevronDown } from 'lucide-react';
import { ChatMessage } from '../types/chat';
import { MessageBubble } from './MessageBubble';
import { MessageComposer } from './MessageComposer';

interface ChatWindowProps {
  messages: ChatMessage[];
  onSendMessage: (content: string) => void;
  isLoading?: boolean;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({
  messages,
  onSendMessage,
  isLoading = false,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <main className="chat-window-container">
      {/* Top Header / Greeting Bar */}
      <header className="chat-top-header">
        <div className="flex-center gap-14">
          <div className="header-ai-badge">
            <Sparkles size={20} className="text-blue-accent" />
          </div>
          <div className="header-text-block">
            <h1>Good morning, Shashvat!</h1>
            <p>
              I'm your AI assistant. Ask me anything about your connected sources
              and I'll find the right information.
            </p>
          </div>
        </div>

        {/* Model Selector & Online Status */}
        <div className="header-status-group">
          <div className="model-selector-pill">
            <span className="model-name">GPT-OSS (Groq)</span>
            <ChevronDown size={14} className="text-muted" />
          </div>
          <div className="status-online-pill">
            <span className="online-dot"></span>
            <span>Online</span>
          </div>
        </div>
      </header>

      {/* Messages Scroll Area */}
      <div className="messages-scroll-area">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isLoading && (
          <div className="message-row assistant-row">
            <div className="assistant-avatar-circle">
              <Sparkles size={18} className="sparkle-ai-icon spin-subtle" />
            </div>
            <div className="assistant-message-content">
              <div className="thinking-bubble">
                <span className="thinking-dot"></span>
                <span className="thinking-dot"></span>
                <span className="thinking-dot"></span>
                <span className="thinking-text">Searching connected sources...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Bottom Composer */}
      <MessageComposer onSendMessage={onSendMessage} disabled={isLoading} />
    </main>
  );
};
