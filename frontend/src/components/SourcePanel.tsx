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
  GitBranch,
  Layers,
  Users,
  Box,
  Folder,
  GraduationCap,
  Settings2,
  CheckCircle2,
  Unlink,
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
  const [loadingConnectorId, setLoadingConnectorId] = useState<string | null>(null);

  const showToast = (text: string, type: 'success' | 'error' = 'success') => {
    setToastMessage({ text, type });
    setTimeout(() => {
      setToastMessage(null);
    }, 4000);
  };

  const handleConnect = (source: ConnectorSource) => {
    if (source.auth_type === 'oauth' && source.auth_url) {
      window.location.href = source.auth_url;
    } else {
      setSelectedSourceForModal(source);
    }
  };

  const handleDisconnect = async (source: ConnectorSource) => {
    setLoadingConnectorId(source.id);
    try {
      const res = await disconnectConnector(source.id);
      showToast(res.message || `${source.name} disconnected.`, 'success');
      await onRefreshConnectors();
    } catch (err: any) {
      showToast(err.message || `Failed to disconnect ${source.name}`, 'error');
    } finally {
      setLoadingConnectorId(null);
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

  // Filter out ONLY ServiceNow, Salesforce, and Jira as explicitly instructed by user
  const excludedIds = ['servicenow', 'salesforce', 'jira'];
  const displaySources = sources.filter((s) => !excludedIds.includes(s.id.toLowerCase()));

  // Active connected count for the displayed sources
  const currentConnectedCount = displaySources.filter((s) => s.is_connected).length;
  const isAllConnected = currentConnectedCount > 0 && currentConnectedCount === displaySources.length;

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
      text: 'Viewed Notion knowledge page',
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
          <div style={{ background: '#F1F5F9', color: '#334155' }} className="source-icon-container">
            <FileText size={16} />
          </div>
        );
      case 'github':
        return (
          <div style={{ background: '#EDE9FE', color: '#6D28D9' }} className="source-icon-container">
            <GitBranch size={16} />
          </div>
        );
      case 'sharepoint':
        return (
          <div style={{ background: '#CCFBF1', color: '#0F766E' }} className="source-icon-container">
            <Layers size={16} />
          </div>
        );
      case 'teams':
        return (
          <div style={{ background: '#E0E7FF', color: '#4338CA' }} className="source-icon-container">
            <Users size={16} />
          </div>
        );
      case 'azure_devops':
        return (
          <div style={{ background: '#E0F2FE', color: '#0369A1' }} className="source-icon-container">
            <Box size={16} />
          </div>
        );
      case 'file_share':
        return (
          <div style={{ background: '#E0F7FA', color: '#00838F' }} className="source-icon-container">
            <Folder size={16} />
          </div>
        );
      case 'lms':
        return (
          <div style={{ background: '#FFEDD5', color: '#C2410C' }} className="source-icon-container">
            <GraduationCap size={16} />
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
    switch (id) {
      case 'gmail':
      case 'google_drive':
        return 'Google Workspace';
      case 'slack':
        return 'Team Communication';
      case 'postgres':
      case 'database':
        return 'Database';
      case 'notion':
        return 'Knowledge Base';
      case 'github':
        return 'Code Repository';
      case 'sharepoint':
        return 'Microsoft 365';
      case 'teams':
        return 'Microsoft Teams';
      case 'azure_devops':
        return 'Azure DevOps';
      case 'file_share':
        return 'File Storage';
      case 'lms':
        return 'Learning Portal';
      default:
        return defType;
    }
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
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          {toastMessage.type === 'success' ? <CheckCircle2 size={16} /> : <Unlink size={16} />}
          <span>{toastMessage.text}</span>
        </div>
      )}

      {/* 1. Connected Sources Header */}
      <div className="panel-header-row">
        <div className="panel-title-group">
          <Target size={17} className="text-muted" />
          <h3>Connected Sources</h3>
        </div>
        <span className={isAllConnected ? 'pill-all-connected' : 'pill-counter-connected'}>
          {isAllConnected ? (
            <>
              <Check size={12} />
              <span>All Connected</span>
            </>
          ) : (
            <span>{currentConnectedCount} / {displaySources.length} Connected</span>
          )}
        </span>
      </div>

      {/* Sources List */}
      <div className="sources-card-list">
        {displaySources.map((source) => {
          const isLoading = loadingConnectorId === source.id;

          return (
            <div
              key={source.id}
              className={`source-item-row ${source.is_connected ? 'source-row-connected' : 'source-row-disconnected'}`}
            >
              <div className="source-row-left">
                {getSourceIcon(source.id)}
                <div className="source-text-meta">
                  <span className="source-title">{source.name}</span>
                  <span className="source-category">{getSourceCategory(source.id, source.type)}</span>
                  {source.account && (
                    <span className="source-account-meta" title={source.account}>
                      {source.account}
                    </span>
                  )}
                </div>
              </div>

              {/* Status and Action Buttons */}
              <div className="source-row-right">
                <span className={`source-status-badge ${source.is_connected ? '' : 'disconnected'}`}>
                  <span className={`source-status-dot ${source.is_connected ? '' : 'disconnected'}`}></span>
                  <span>{source.is_connected ? 'Connected' : 'Not Connected'}</span>
                </span>

                <div className="source-action-group">
                  {source.is_connected ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                      {source.auth_type === 'credentials' && (
                        <button
                          type="button"
                          className="source-icon-action-btn"
                          title="Configure credentials"
                          onClick={() => setSelectedSourceForModal(source)}
                        >
                          <Settings2 size={13} />
                        </button>
                      )}
                      {source.auth_type !== 'info' && (
                        <button
                          type="button"
                          className="source-btn-disconnect"
                          disabled={isLoading}
                          onClick={() => handleDisconnect(source)}
                          title="Disconnect this service"
                        >
                          {isLoading ? '...' : 'Disconnect'}
                        </button>
                      )}
                    </div>
                  ) : (
                    <button
                      type="button"
                      className="source-btn-connect"
                      onClick={() => handleConnect(source)}
                      title="Connect this service"
                    >
                      <span>Connect</span>
                      {source.auth_type === 'oauth' && <ExternalLink size={11} />}
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
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
