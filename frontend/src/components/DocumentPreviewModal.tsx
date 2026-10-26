import React, { useState } from 'react';
import {
  X,
  Copy,
  Check,
  FileSpreadsheet,
  FileText,
  Table as TableIcon,
  Sparkles,
  Info,
  ShieldCheck,
} from 'lucide-react';

export interface DocumentPreviewData {
  title: string;
  filename: string;
  text: string;
  elements_count?: number;
  duration_ms?: number;
  tables?: Array<{ id: string; text: string; order: number } | any>;
  metadata?: string;
}

interface DocumentPreviewModalProps {
  document: DocumentPreviewData;
  onClose: () => void;
}

export const DocumentPreviewModal: React.FC<DocumentPreviewModalProps> = ({
  document,
  onClose,
}) => {
  const [activeTab, setActiveTab] = useState<'text' | 'tables' | 'stats'>('text');
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!document.text) return;
    navigator.clipboard.writeText(document.text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const tables = document.tables || [];

  return (
    <div className="doc-modal-overlay" onClick={onClose}>
      <div
        className="doc-modal-container"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        {/* Modal Header */}
        <header className="doc-modal-header">
          <div className="doc-modal-header-left">
            <div className="doc-modal-badge-icon">
              <FileSpreadsheet size={20} />
            </div>
            <div className="doc-modal-titles">
              <h2 className="doc-modal-title" title={document.filename || document.title}>
                {document.filename || document.title}
              </h2>
              <div className="doc-modal-submeta">
                <span className="doc-meta-pill green">Universal Parser Ensemble</span>
                {document.elements_count !== undefined && (
                  <span className="doc-meta-pill slate">
                    {document.elements_count} elements
                  </span>
                )}
                {tables.length > 0 && (
                  <span className="doc-meta-pill slate">{tables.length} tables</span>
                )}
                {document.duration_ms !== undefined && document.duration_ms > 0 && (
                  <span className="doc-meta-pill slate">
                    {document.duration_ms.toFixed(0)}ms
                  </span>
                )}
              </div>
            </div>
          </div>

          <button
            type="button"
            className="doc-modal-close-btn"
            onClick={onClose}
            title="Close preview"
          >
            <X size={18} />
          </button>
        </header>

        {/* Modal Toolbar / Tab Switcher */}
        <div className="doc-modal-toolbar">
          <div className="doc-modal-tabs">
            <button
              type="button"
              className={`doc-tab-btn ${activeTab === 'text' ? 'active' : ''}`}
              onClick={() => setActiveTab('text')}
            >
              <FileText size={14} />
              <span>Extracted Content</span>
            </button>

            {tables.length > 0 && (
              <button
                type="button"
                className={`doc-tab-btn ${activeTab === 'tables' ? 'active' : ''}`}
                onClick={() => setActiveTab('tables')}
              >
                <TableIcon size={14} />
                <span>Extracted Tables ({tables.length})</span>
              </button>
            )}

            <button
              type="button"
              className={`doc-tab-btn ${activeTab === 'stats' ? 'active' : ''}`}
              onClick={() => setActiveTab('stats')}
            >
              <Sparkles size={14} />
              <span>Inspection Details</span>
            </button>
          </div>

          <button
            type="button"
            className="doc-modal-copy-btn"
            onClick={handleCopy}
            disabled={!document.text}
            title="Copy extracted document text"
          >
            {copied ? (
              <>
                <Check size={14} color="#059669" />
                <span className="text-green-700">Copied!</span>
              </>
            ) : (
              <>
                <Copy size={14} />
                <span>Copy Text</span>
              </>
            )}
          </button>
        </div>

        {/* Modal Body */}
        <div className="doc-modal-body">
          {activeTab === 'text' && (
            <div className="doc-text-view-wrapper">
              {document.text ? (
                <pre className="doc-extracted-pre">{document.text}</pre>
              ) : (
                <div className="doc-empty-state">
                  <Info size={32} />
                  <p>No textual content could be extracted from this document.</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'tables' && (
            <div className="doc-tables-view-wrapper">
              {tables.length > 0 ? (
                tables.map((tbl: any, idx: number) => (
                  <div key={idx} className="doc-table-card">
                    <div className="doc-table-card-header">
                      <span className="table-badge">Table {idx + 1}</span>
                      {tbl.id && <span className="table-id-text">ID: {tbl.id}</span>}
                    </div>
                    <pre className="doc-table-pre">{tbl.text || JSON.stringify(tbl, null, 2)}</pre>
                  </div>
                ))
              ) : (
                <div className="doc-empty-state">
                  <TableIcon size={32} />
                  <p>No structured tables detected in this document.</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'stats' && (
            <div className="doc-stats-view-wrapper">
              <div className="doc-stats-grid">
                <div className="doc-stat-card">
                  <span className="stat-label">File Name</span>
                  <span className="stat-value">{document.filename || document.title}</span>
                </div>
                <div className="doc-stat-card">
                  <span className="stat-label">Total Elements</span>
                  <span className="stat-value">{document.elements_count ?? 'N/A'}</span>
                </div>
                <div className="doc-stat-card">
                  <span className="stat-label">Extracted Tables</span>
                  <span className="stat-value">{tables.length}</span>
                </div>
                <div className="doc-stat-card">
                  <span className="stat-label">Parsing Pipeline</span>
                  <span className="stat-value">Universal Parser Ensemble + pdfplumber OCR</span>
                </div>
                <div className="doc-stat-card">
                  <span className="stat-label">RAG Grounding Status</span>
                  <span className="stat-value highlight">Active in Current Chat Session</span>
                </div>
              </div>

              <div className="doc-grounding-notice">
                <ShieldCheck size={18} color="#059669" />
                <p>
                  This document's full extracted text and structured tables are grounded in your
                  conversation context. Cerebro references this content automatically whenever you
                  ask questions in this chat.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <footer className="doc-modal-footer">
          <div className="doc-footer-status">
            <span className="doc-status-indicator"></span>
            <span>Active in session context</span>
          </div>
          <button type="button" className="doc-modal-btn-primary" onClick={onClose}>
            Done
          </button>
        </footer>
      </div>
    </div>
  );
};
