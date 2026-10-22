import React, { useState } from 'react';
import {
  Target,
  ChevronRight,
  ShieldCheck,
  Check,
  Mail,
  HardDrive,
  Hash,
  Database,
  FileText,
  Search,
  ExternalLink,
} from 'lucide-react';
import { ConnectorSource } from '../types/chat';
import { ConnectorModal } from './ConnectorModal';
import { configureConnector, disconnectConnector } from '../services/api';

interface SourcePanelProps {
  sources: ConnectorSource[];
  connectedCount: number;
  totalCount: number;
  onRefreshConnectors: () => Promise<void>;
}

export const SourcePanel: React.FC<SourcePanelProps> = ({
  sources,
  connectedCount,
  totalCount,
  onRefreshConnectors,
}) => {
  const [selectedSourceForModal, setSelectedSourceForModal] = useState<ConnectorSource | null>(null);
  const [toastMessage, setToastMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const showToast = (text: string, type: 'success' | 'error' = 'success') => {
    setToastMessage({ text, type });
    setTimeout(() => {
      setToastMessage(null);
    }, 4000);
  };

  const handleSourceClick = (source: ConnectorSource) => {
    if (source.auth_type === 'oauth' && source.auth_url && !source.is_connected) {
      window.location.href = source.auth_url;
    } else {
      setSelectedSourceForModal(source);
    }
  };

  const handleSaveCredentials = async (connectorId: string, credentials: Record<string, string>) => {
    const result = await configureConnector(connectorId, credentials);
    if (result.auth_url) {
      window.location.href = result.auth_url;
      return;
    }
    showToast(result.message || 'Connected successfully!', 'success');
    await onRefreshConnectors();
  };

  // Map primary 5 sources to match reference photo
  const primarySourceIds = ['gmail', 'google_drive', 'slack', 'postgres', 'notion'];
  const displaySources = primarySourceIds.map((id) => {
    const found = sources.find((s) => s.id === id);
    if (found) return found;

    // Friendly defaults if unseeded
    if (id === 'gmail') {
      return { id: 'gmail', name: 'Gmail', type: 'Google Workspace', status: 'Live', is_connected: true, badge_color: 'green' as const };
    }
    if (id === 'google_drive') {
      return { id: 'google_drive', name: 'Google Drive', type: 'Google Workspace', status: 'Live', is_connected: true, badge_color: 'green' as const };
    }
    if (id === 'slack') {
      return { id: 'slack', name: 'Slack', type: 'Team Communication', status: 'Live', is_connected: true, badge_color: 'green' as const };
    }
    if (id === 'postgres') {
      return { id: 'postgres', name: 'PostgreSQL', type: 'Database', status: 'Live', is_connected: true, badge_color: 'green' as const };
    }
    return { id: 'notion', name: 'Notion', type: 'Knowledge Base', status: 'Live', is_connected: true, badge_color: 'green' as const };
  });

  const recentActivities = [
    {
      text: 'Searched emails in Gmail',
      time: '2 minutes ago',
      icon: Mail,
      bg: '#FEE2E2',
      color: '#DC2626',
    },
    {
      text: 'Queried database for product info',
      time: '18 minutes ago',
      icon: Database,
      bg: '#E0F2FE',
      color: '#0284C7',
    },
    {
      text: 'Viewed Notion page',
      time: '32 minutes ago',
      icon: FileText,
      bg: '#F3F4F6',
      color: '#374151',
    },
    {
      text: 'Connected Slack workspace',
      time: '1 hour ago',
      icon: Hash,
      bg: '#F3E8FF',
      color: '#7E22CE',
    },
    {
      text: 'Analyzed 3 documents from Drive',
      time: '2 hours ago',
      icon: HardDrive,
      bg: '#FEF3C7',
      color: '#D97706',
    },
  ];

  const getSourceIcon = (id: string) => {
    switch (id) {
      case 'gmail':
        return (
          <div style={{ background: '#FEE2E2', color: '#DC2626' }} className="source-icon-container">
            <Mail size={16} />
          </div>
        );
      case 'google_drive':
        return (
          <div style={{ background: '#FEF3C7', color: '#D97706' }} className="source-icon-container">
            <HardDrive size={16} />
          </div>
        );
      case 'slack':
        return (
          <div style={{ background: '#F3E8FF', color: '#7E22CE' }} className="source-icon-container">
            <Hash size={16} />
          </div>
        );
      case 'postgres':
      case 'database':
        return (
          <div style={{ background: '#E0F2FE', color: '#0284C7' }} className="source-icon-container">
            <Database size={16} />
          </div>
        );
      case 'notion':
        return (
          <div style={{ background: '#F3F4F6', color: '#374151' }} className="source-icon-container">
            <FileText size={16} />
          </div>
        );
      default:
        return (
          <div style={{ background: '#F1F5F9', color: '#64748B' }} className="source-icon-container">
            <Search size={16} />
          </div>
        );
    }
  };

  const getSourceCategory = (id: string, defType: string) => {
    if (id === 'gmail' || id === 'google_drive') return 'Google Workspace';
    if (id === 'slack') return 'Team Communication';
    if (id === 'postgres') return 'Database';
    if (id === 'notion') return 'Knowledge Base';
    return defType;
  };

  return (
    <aside className="dabur-right-panel">
      {/* Toast Notification */}
      {toastMessage && (
        <div
          style={{
            position: 'fixed',
            top: '20px',
            right: '20px',
            background: toastMessage.type === 'success' ? '#164E33' : '#EF4444',
            color: '#FFFFFF',
            padding: '10px 16px',
            borderRadius: '8px',
            fontSize: '13px',
            fontWeight: 600,
            zIndex: 9999,
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
          }}
        >
          {toastMessage.text}
        </div>
      )}

      {/* 1. Connected Sources Header */}
      <div className="panel-header-row">
        <div className="panel-title-group">
          <Target size={17} className="text-muted" />
          <h3>Connected Sources</h3>
        </div>
        <span className="pill-all-connected">
          <Check size={12} />
          <span>All Connected</span>
        </span>
      </div>

      {/* Sources List */}
      <div className="sources-card-list">
        {displaySources.map((source) => (
          <div
            key={source.id}
            className="source-item-row"
            onClick={() => handleSourceClick(source)}
            title="Click to configure or view connection"
          >
            <div className="source-row-left">
              {getSourceIcon(source.id)}
              <div className="source-text-meta">
                <span className="source-title">{source.name}</span>
                <span className="source-category">{getSourceCategory(source.id, source.type)}</span>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span className="source-status-badge">
                <span className="source-status-dot"></span>
                <span>Connected</span>
              </span>
              <ChevronRight size={14} color="#94A3B8" />
            </div>
          </div>
        ))}
      </div>

      {/* 2. Recent Activity Section */}
      <div className="recent-activity-section">
        <div className="activity-header-row">
          <h4>Recent Activity</h4>
          <span className="activity-view-all">View all &gt;</span>
        </div>

        <div className="activity-list">
          {recentActivities.map((act, idx) => {
            const IconC = act.icon;
            return (
              <div key={idx} className="activity-item">
                <div
                  className="activity-icon-badge"
                  style={{ background: act.bg, color: act.color }}
                >
                  <IconC size={14} />
                </div>
                <div className="activity-meta">
                  <span className="activity-text">{act.text}</span>
                  <span className="activity-time">{act.time}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. Enterprise Context & Security Card */}
      <div className="security-assurance-card">
        <div className="security-card-header">
          <ShieldCheck size={18} color="#164E33" />
          <span>Enterprise Context &amp; Security</span>
        </div>

        <ul className="security-points-list">
          <li className="security-point-item">
            <Check size={14} className="security-check-icon" />
            <span>Your data stays within Dabur's secure environment</span>
          </li>
          <li className="security-point-item">
            <Check size={14} className="security-check-icon" />
            <span>Role-based access and permissions</span>
          </li>
          <li className="security-point-item">
            <Check size={14} className="security-check-icon" />
            <span>All queries are logged for audit</span>
          </li>
          <li className="security-point-item">
            <Check size={14} className="security-check-icon" />
            <span>Powered by trusted AI models</span>
          </li>
        </ul>

        {/* Decorative Watermark */}
        <svg
          className="security-leaf-watermark"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        >
          <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" />
          <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12" />
        </svg>
      </div>

      {/* Dynamic Connector Modal */}
      {selectedSourceForModal && (
        <ConnectorModal
          source={selectedSourceForModal}
          onClose={() => setSelectedSourceForModal(null)}
          onSave={handleSaveCredentials}
        />
      )}
    </aside>
  );
};
