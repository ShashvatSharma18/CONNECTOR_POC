import React, { useState, useRef } from 'react';
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
  FileSearch,
  X,
  Loader2,
  FileSpreadsheet,
} from 'lucide-react';
import { ConnectorSource, ActiveDocumentState } from '../types/chat';
import { uploadAndParseDocument, ParsedDocumentResult } from '../services/api';

interface MessageComposerProps {
  onSendMessage: (content: string) => void;
  onOpenAddSources?: () => void;
  sources?: ConnectorSource[];
  activeDocument?: ActiveDocumentState | null;
  onAttachDocument?: (doc: ActiveDocumentState) => void;
  onClearActiveDocument?: () => void;
  disabled?: boolean;
}

export const MessageComposer: React.FC<MessageComposerProps> = ({
  onSendMessage,
  onOpenAddSources,
  sources = [],
  activeDocument,
  onAttachDocument,
  onClearActiveDocument,
  disabled = false,
}) => {
  const [input, setInput] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadError(null);
    try {
      const result = await uploadAndParseDocument(file, 'balanced', 'summary');
      if (result.success) {
        if (onAttachDocument) {
          onAttachDocument(result);
        }
      } else {
        setUploadError(result.error || 'Failed to parse document');
      }
    } catch (err: any) {
      setUploadError(err.message || 'Error uploading document');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if ((!input.trim() && !activeDocument) || disabled || isUploading) return;

    let finalPrompt = input.trim();
    if (activeDocument) {
      const docHeader = `[Attached Document: ${activeDocument.filename} (${activeDocument.elements_count || 0} elements, ${(activeDocument.tables || []).length} tables)]`;
      const docBody = activeDocument.text ? activeDocument.text.slice(0, 2500) : '';
      if (!finalPrompt) {
        finalPrompt = `Please analyze and summarize this attached document: ${activeDocument.filename}.\n\n${docHeader}\n${docBody}`;
      } else {
        finalPrompt = `${docHeader}\nContent Excerpt:\n${docBody}\n\nUser Question: ${finalPrompt}`;
      }
    }

    onSendMessage(finalPrompt);
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
      case 'universal_parser':
      case 'document_parser':
        return <FileSearch size={13} color="#059669" />;
      default:
        return <Search size={13} color="#64748B" />;
    }
  };

  return (
    <div className="composer-wrapper">
      {/* Hidden file input for attachment */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        style={{ display: 'none' }}
        accept=".pdf,.docx,.doc,.xlsx,.xls,.pptx,.ppt,.txt,.md,.csv,.json,.html,.png,.jpg,.jpeg"
      />

      {/* Upload Status / Attached Document Pill */}
      {(isUploading || activeDocument || uploadError) && (
        <div className="composer-attachment-bar">
          {isUploading && (
            <div className="attachment-chip uploading">
              <Loader2 size={13} className="spin-animation" />
              <span>Parsing document with Universal Parser ensemble...</span>
            </div>
          )}

          {activeDocument && !isUploading && (
            <div className="attachment-chip success">
              <FileSpreadsheet size={14} color="#059669" />
              <span className="attachment-filename">{activeDocument.filename}</span>
              <span className="attachment-meta">
                ({activeDocument.elements_count || 0} elements
                {activeDocument.tables && activeDocument.tables.length > 0
                  ? `, ${activeDocument.tables.length} tables`
                  : ''}
                {activeDocument.duration_ms ? ` • ${activeDocument.duration_ms.toFixed(0)}ms` : ''})
              </span>
              <button
                type="button"
                className="btn-remove-attachment"
                onClick={() => onClearActiveDocument?.()}
                title="Detach document from this chat"
              >
                <X size={12} />
              </button>
            </div>
          )}

          {uploadError && !isUploading && (
            <div className="attachment-chip error">
              <span>{uploadError}</span>
              <button
                type="button"
                className="btn-remove-attachment"
                onClick={() => setUploadError(null)}
              >
                <X size={12} />
              </button>
            </div>
          )}
        </div>
      )}

      {/* Floating Main Input Card */}
      <form className="composer-card" onSubmit={handleSubmit}>
        <button
          type="button"
          className={`composer-clip-btn ${activeDocument ? 'has-attachment' : ''}`}
          onClick={() => fileInputRef.current?.click()}
          title="Upload document to parse (PDF, Excel, Word, OCR, Images)"
          disabled={isUploading || disabled}
        >
          <Paperclip size={19} />
        </button>

        <input
          type="text"
          className="composer-input"
          placeholder={
            activeDocument
              ? `Ask anything about ${activeDocument.filename}... (stays active across this chat)`
              : 'Ask anything... (e.g. "Find emails from marketing" or attach a PDF/Excel file)'
          }
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={disabled || isUploading}
        />

        <button
          type="submit"
          className="composer-send-circle"
          disabled={(!input.trim() && !activeDocument) || disabled || isUploading}
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
