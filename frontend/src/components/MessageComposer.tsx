import React, { useState } from 'react';
import {
  Paperclip,
  Send,
  Check,
  Plus,
  Mail,
  HardDrive,
  Hash,
  Database,
  FileText,
} from 'lucide-react';

interface MessageComposerProps {
  onSendMessage: (content: string) => void;
  onOpenAddSources?: () => void;
  disabled?: boolean;
}

export const MessageComposer: React.FC<MessageComposerProps> = ({
  onSendMessage,
  onOpenAddSources,
  disabled = false,
}) => {
  const [input, setInput] = useState('');
  const [selectedSources, setSelectedSources] = useState<string[]>([
    'gmail',
    'drive',
    'slack',
    'database',
    'notion',
  ]);

  const toggleSource = (id: string) => {
    setSelectedSources((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || disabled) return;
    onSendMessage(input.trim());
    setInput('');
  };

  const sourcesList = [
    { id: 'gmail', label: 'Gmail', icon: Mail, color: '#EA4335' },
    { id: 'drive', label: 'Drive', icon: HardDrive, color: '#F59E0B' },
    { id: 'slack', label: 'Slack', icon: Hash, color: '#7E22CE' },
    { id: 'database', label: 'Database', icon: Database, color: '#0284C7' },
    { id: 'notion', label: 'Notion', icon: FileText, color: '#374151' },
  ];

  return (
    <div className="composer-wrapper">
      {/* Floating Main Input Card */}
      <form className="composer-card" onSubmit={handleSubmit}>
        <button
          type="button"
          className="composer-clip-btn"
          title="Attach file or context"
        >
          <Paperclip size={19} />
        </button>

        <input
          type="text"
          className="composer-input"
          placeholder='Ask anything... (e.g. "Find emails from marketing about Chyawanprash launch")'
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={disabled}
        />

        <button
          type="submit"
          className="composer-send-circle"
          disabled={!input.trim() || disabled}
          title="Send message"
        >
          <Send size={15} />
        </button>
      </form>

      {/* Bottom Connected Sources Quick-Filter Pills */}
      <div className="composer-sources-row">
        {sourcesList.map((src) => {
          const IconC = src.icon;
          const isActive = selectedSources.includes(src.id);
          return (
            <button
              key={src.id}
              type="button"
              className={`quick-source-chip ${isActive ? 'active' : ''}`}
              onClick={() => toggleSource(src.id)}
            >
              <IconC size={13} color={src.color} />
              <span>{src.label}</span>
              {isActive && <Check size={11} className="text-green-700" />}
            </button>
          );
        })}

        <button
          type="button"
          className="btn-add-sources-chip"
          onClick={onOpenAddSources}
        >
          <Plus size={12} style={{ display: 'inline', marginRight: '4px' }} />
          <span>Add sources</span>
        </button>
      </div>
    </div>
  );
};
