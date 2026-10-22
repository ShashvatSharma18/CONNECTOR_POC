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
  GitBranch,
  Layers,
  Users,
  Box,
  Folder,
  GraduationCap,
  Search,
  MessageSquare,
} from 'lucide-react';
import { ConnectorSource } from '../types/chat';

interface MessageComposerProps {
  onSendMessage: (content: string) => void;
  onOpenAddSources?: () => void;
  sources?: ConnectorSource[];
  disabled?: boolean;
}

export const MessageComposer: React.FC<MessageComposerProps> = ({
  onSendMessage,
  onOpenAddSources,
  sources = [],
  disabled = false,
}) => {
  const [input, setInput] = useState('');

  // Filter ONLY sources that are actually connected and eligible
  const excludedIds = ['servicenow', 'salesforce', 'jira'];
  const connectedSources = sources.filter(
    (s) => s.is_connected && !excludedIds.includes(s.id.toLowerCase())
  );

  const [selectedSourceIds, setSelectedSourceIds] = useState<string[]>([]);

  // Toggle selection filter if user wants to target specific connected sources
  const toggleSource = (id: string) => {
    setSelectedSourceIds((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || disabled) return;
    onSendMessage(input.trim());
    setInput('');
  };

  const getSourceIcon = (id: string) => {
    switch (id) {
      case 'gmail':
        return <Mail size={13} color="#EA4335" />;
      case 'google_drive':
        return <HardDrive size={13} color="#D97706" />;
      case 'google_chat':
        return <MessageSquare size={13} color="#16A34A" />;
      case 'slack':
        return <Hash size={13} color="#7E22CE" />;
      case 'postgres':
      case 'database':
        return <Database size={13} color="#0284C7" />;
      case 'notion':
        return <FileText size={13} color="#374151" />;
      case 'github':
        return <GitBranch size={13} color="#6D28D9" />;
      case 'sharepoint':
        return <Layers size={13} color="#0F766E" />;
      case 'teams':
        return <Users size={13} color="#4338CA" />;
      case 'azure_devops':
        return <Box size={13} color="#0369A1" />;
      case 'file_share':
        return <Folder size={13} color="#00838F" />;
      case 'lms':
        return <GraduationCap size={13} color="#C2410C" />;
      default:
        return <Search size={13} color="#64748B" />;
    }
  };

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
        {connectedSources.length > 0 ? (
          connectedSources.map((src) => {
            const isTargeted =
              selectedSourceIds.length === 0 || selectedSourceIds.includes(src.id);

            return (
              <button
                key={src.id}
                type="button"
                className={`quick-source-chip ${isTargeted ? 'active' : ''}`}
                onClick={() => toggleSource(src.id)}
                title={`Connected: ${src.name}${src.account ? ` (${src.account})` : ''}`}
              >
                {getSourceIcon(src.id)}
                <span>{src.name}</span>
                <span className="chip-active-dot"></span>
                {isTargeted && <Check size={11} className="text-green-700" />}
              </button>
            );
          })
        ) : (
          <span className="composer-no-sources-hint">
            No sources connected yet.
          </span>
        )}

        <button
          type="button"
          className="btn-add-sources-chip"
          onClick={onOpenAddSources}
          title="Connect or configure enterprise knowledge sources"
        >
          <Plus size={12} style={{ display: 'inline', marginRight: '4px' }} />
          <span>Connect sources</span>
        </button>
      </div>
    </div>
  );
};
