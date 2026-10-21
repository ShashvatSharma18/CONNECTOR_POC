import React, { useState } from 'react';
import {
  Lightbulb,
  Check,
  Mail,
  GitBranch,
  Folder,
  GraduationCap,
  Layers,
  Users,
  Box,
  Sparkles,
  Cloud,
  HardDrive,
  CheckSquare,
  Settings2,
  Unlink,
  ExternalLink,
  CheckCircle2,
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
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const showToast = (text: string, type: 'success' | 'error' = 'success') => {
    setToastMessage({ text, type });
    setTimeout(() => {
      setToastMessage(null);
    }, 4000);
  };

  const handleConnect = (source: ConnectorSource) => {
    if (source.auth_type === 'oauth' && source.auth_url) {
      // Redirect to OAuth authorization endpoint
      window.location.href = source.auth_url;
    } else if (source.auth_type === 'credentials') {
      setSelectedSourceForModal(source);
    }
  };

  const handleDisconnect = async (source: ConnectorSource) => {
    const confirmed = window.confirm(`Are you sure you want to disconnect ${source.name}?`);
    if (!confirmed) return;

    setActionLoadingId(source.id);
    try {
      await disconnectConnector(source.id);
      showToast(`${source.name} disconnected successfully.`, 'success');
      await onRefreshConnectors();
    } catch (err: any) {
      showToast(err.message || `Failed to disconnect ${source.name}`, 'error');
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleSaveCredentials = async (connectorId: string, credentials: Record<string, string>) => {
    const result = await configureConnector(connectorId, credentials);
    if (result.auth_url) {
      // For Salesforce, after configuring client ID/secret, navigate to OAuth
      window.location.href = result.auth_url;
      return;
    }
    showToast(result.message || 'Connected successfully!', 'success');
    await onRefreshConnectors();
  };

  // Helper to render connector icon with proper branding color
  const renderSourceIcon = (id: string) => {
    switch (id) {
      case 'gmail':
        return (
          <div className="source-icon-box bg-red-gradient">
            <Mail size={16} className="text-white" />
          </div>
        );
      case 'github':
        return (
          <div className="source-icon-box bg-gray-gradient">
            <GitBranch size={16} className="text-white" />
          </div>
        );
      case 'file_share':
        return (
          <div className="source-icon-box bg-blue-gradient">
            <Folder size={16} className="text-white" />
          </div>
        );
      case 'lms':
        return (
          <div className="source-icon-box bg-orange-gradient">
            <GraduationCap size={16} className="text-white" />
          </div>
        );
      case 'sharepoint':
        return (
          <div className="source-icon-box bg-teal-gradient">
            <Layers size={16} className="text-white" />
          </div>
        );
      case 'teams':
        return (
          <div className="source-icon-box bg-purple-gradient">
            <Users size={16} className="text-white" />
          </div>
        );
      case 'azure_devops':
        return (
          <div className="source-icon-box bg-azure-gradient">
            <Box size={16} className="text-white" />
          </div>
        );
      case 'servicenow':
        return (
          <div className="source-icon-box bg-emerald-gradient">
            <Layers size={16} className="text-white" />
          </div>
        );
      case 'salesforce':
        return (
          <div className="source-icon-box bg-blue-gradient">
            <Cloud size={16} className="text-white" />
          </div>
        );
      case 'google_drive':
        return (
          <div className="source-icon-box bg-yellow-gradient">
            <HardDrive size={16} className="text-white" />
          </div>
        );
      case 'jira':
        return (
          <div className="source-icon-box bg-jira-gradient">
            <CheckSquare size={16} className="text-white" />
          </div>
        );
      default:
        return (
          <div className="source-icon-box bg-gray-gradient">
            <Box size={16} className="text-white" />
          </div>
        );
    }
  };

  const getBadgeClass = (status: string) => {
    if (status === 'Live') return 'status-live';
    if (status === 'Local Test') return 'status-local';
    if (status === 'Mock') return 'status-mock';
    return 'status-ready';
  };

  return (
    <aside className="source-panel">
      {/* Header */}
      <div className="source-header">
        <div className="flex-center gap-8">
          <h3>Connected Sources</h3>
        </div>
        <span className="source-count-badge">
          {connectedCount} / {totalCount}
        </span>
      </div>

      {/* Floating Toast Notification */}
      {toastMessage && (
        <div className={`source-toast source-toast-${toastMessage.type}`}>
          {toastMessage.type === 'success' ? (
            <CheckCircle2 size={15} />
          ) : (
            <Unlink size={15} />
          )}
          <span>{toastMessage.text}</span>
        </div>
      )}

      {/* Sources List */}
      <div className="source-list">
        {sources.map((src) => {
          const isLoading = actionLoadingId === src.id;

          return (
            <div key={src.id} className="source-item-card">
              <div className="source-card-main-row">
                <div className="flex-center gap-10 overflow-hidden">
                  {renderSourceIcon(src.id)}
                  <div className="source-item-info">
                    <span className="source-item-name">{src.name}</span>
                    <span className={`source-status-badge ${getBadgeClass(src.status)}`}>
                      <span className="status-dot"></span>
                      {src.status}
                    </span>
                  </div>
                </div>

                {/* Connect / Disconnect Action Button */}
                <div className="source-action-group">
                  {src.is_connected ? (
                    <div className="flex-center gap-4">
                      {src.auth_type === 'credentials' && (
                        <button
                          type="button"
                          className="source-icon-action-btn"
                          title="Configure credentials"
                          onClick={() => setSelectedSourceForModal(src)}
                        >
                          <Settings2 size={13} />
                        </button>
                      )}
                      {src.auth_type !== 'info' && (
                        <button
                          type="button"
                          className="source-btn-disconnect"
                          disabled={isLoading}
                          onClick={() => handleDisconnect(src)}
                          title="Disconnect service"
                        >
                          {isLoading ? '...' : 'Disconnect'}
                        </button>
                      )}
                    </div>
                  ) : (
                    <button
                      type="button"
                      className="source-btn-connect"
                      onClick={() => handleConnect(src)}
                    >
                      <span>Connect</span>
                      {src.auth_type === 'oauth' && <ExternalLink size={11} />}
                    </button>
                  )}
                </div>
              </div>

              {/* Show connected user account email or path */}
              {src.account && (
                <div className="source-account-meta" title={src.account}>
                  {src.account}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Quick Tips */}
      <div className="quick-tips-card">
        <div className="tips-title">
          <Lightbulb size={16} className="text-warning" />
          <span>Quick Tips</span>
        </div>
        <ul className="tips-list">
          <li>
            <Check size={14} className="tip-check" />
            <span>Search by file name, topic or person</span>
          </li>
          <li>
            <Check size={14} className="tip-check" />
            <span>You can ask for specific date ranges</span>
          </li>
          <li>
            <Check size={14} className="tip-check" />
            <span>Get results from multiple sources at once</span>
          </li>
          <li>
            <Check size={14} className="tip-check" />
            <span>Connect all your tools to cross-reference data</span>
          </li>
        </ul>
      </div>

      {/* Feature Promo Card */}
      <div className="promo-feature-card">
        <div className="promo-gradient-glow"></div>
        <div className="promo-content">
          <h4>Your data.<br />All in one place.</h4>
          <p>Connected. Searchable. Ready.</p>
          <div className="promo-stars">
            <Sparkles size={18} className="text-purple-accent" />
          </div>
        </div>
      </div>

      {/* Connector Credentials Modal */}
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
