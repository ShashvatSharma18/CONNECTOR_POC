import React, { useState } from 'react';
import {
  BookOpen,
  Search,
  CheckCircle2,
  ExternalLink,
  Settings2,
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
  ArrowRight,
  ShieldCheck,
  Check,
  Filter,
  MessageSquare,
} from 'lucide-react';
import { ConnectorSource } from '../types/chat';

interface KnowledgeHubProps {
  sources: ConnectorSource[];
  onRefreshConnectors: () => Promise<void>;
  onConnectClick: (source: ConnectorSource) => void;
  onDisconnectClick: (source: ConnectorSource) => Promise<void>;
  onSwitchToChat: () => void;
  isLoadingSourceId?: string | null;
}

export const KnowledgeHub: React.FC<KnowledgeHubProps> = ({
  sources,
  onRefreshConnectors,
  onConnectClick,
  onDisconnectClick,
  onSwitchToChat,
  isLoadingSourceId = null,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterTab, setFilterTab] = useState<'all' | 'connected' | 'available'>('all');

  // Filter out ServiceNow, Salesforce, and Jira as explicitly requested
  const excludedIds = ['servicenow', 'salesforce', 'jira'];
  const eligibleSources = sources.filter((s) => !excludedIds.includes(s.id.toLowerCase()));

  const connectedCount = eligibleSources.filter((s) => s.is_connected).length;
  const availableCount = eligibleSources.length - connectedCount;

  // Filtered by search and tab
  const filteredSources = eligibleSources.filter((src) => {
    const matchesSearch =
      src.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (src.description && src.description.toLowerCase().includes(searchQuery.toLowerCase())) ||
      src.type.toLowerCase().includes(searchQuery.toLowerCase());

    if (!matchesSearch) return false;
    if (filterTab === 'connected') return src.is_connected;
    if (filterTab === 'available') return !src.is_connected;
    return true;
  });

  const getSourceIcon = (id: string) => {
    switch (id) {
      case 'gmail':
        return (
          <div style={{ background: '#FEE2E2', color: '#DC2626' }} className="kh-icon-container">
            <Mail size={22} />
          </div>
        );
      case 'google_drive':
        return (
          <div style={{ background: '#FEF3C7', color: '#D97706' }} className="kh-icon-container">
            <HardDrive size={22} />
          </div>
        );
      case 'google_chat':
        return (
          <div style={{ background: '#DCFCE7', color: '#16A34A' }} className="kh-icon-container">
            <MessageSquare size={22} />
          </div>
        );
      case 'slack':
        return (
          <div style={{ background: '#F3E8FF', color: '#7E22CE' }} className="kh-icon-container">
            <Hash size={22} />
          </div>
        );
      case 'postgres':
      case 'database':
        return (
          <div style={{ background: '#E0F2FE', color: '#0284C7' }} className="kh-icon-container">
            <Database size={22} />
          </div>
        );
      case 'notion':
        return (
          <div style={{ background: '#F1F5F9', color: '#334155' }} className="kh-icon-container">
            <FileText size={22} />
          </div>
        );
      case 'github':
        return (
          <div style={{ background: '#EDE9FE', color: '#6D28D9' }} className="kh-icon-container">
            <GitBranch size={22} />
          </div>
        );
      case 'sharepoint':
        return (
          <div style={{ background: '#CCFBF1', color: '#0F766E' }} className="kh-icon-container">
            <Layers size={22} />
          </div>
        );
      case 'teams':
        return (
          <div style={{ background: '#E0E7FF', color: '#4338CA' }} className="kh-icon-container">
            <Users size={22} />
          </div>
        );
      case 'azure_devops':
        return (
          <div style={{ background: '#E0F2FE', color: '#0369A1' }} className="kh-icon-container">
            <Box size={22} />
          </div>
        );
      case 'file_share':
        return (
          <div style={{ background: '#E0F7FA', color: '#00838F' }} className="kh-icon-container">
            <Folder size={22} />
          </div>
        );
      case 'lms':
        return (
          <div style={{ background: '#FFEDD5', color: '#C2410C' }} className="kh-icon-container">
            <GraduationCap size={22} />
          </div>
        );
      default:
        return (
          <div style={{ background: '#F1F5F9', color: '#64748B' }} className="kh-icon-container">
            <Search size={22} />
          </div>
        );
    }
  };

  const getSourceCategory = (id: string, defType: string) => {
    switch (id) {
      case 'gmail':
      case 'google_drive':
        return 'Google Workspace';
      case 'google_chat':
        return 'Google Workspace Chat';
      case 'slack':
        return 'Team Communication';
      case 'postgres':
      case 'database':
        return 'Relational Database';
      case 'notion':
        return 'Knowledge Base & Wiki';
      case 'github':
        return 'Code Repository';
      case 'sharepoint':
        return 'Microsoft 365';
      case 'teams':
        return 'Microsoft Teams';
      case 'azure_devops':
        return 'Azure DevOps Repos';
      case 'file_share':
        return 'Network & Local Files';
      case 'lms':
        return 'Learning Portal';
      default:
        return defType;
    }
  };

  return (
    <main className="knowledge-hub-workspace">
      {/* Header Banner */}
      <header className="kh-top-header">
        <div className="kh-header-title-row">
          <div className="kh-title-left">
            <div className="kh-header-icon-badge">
              <BookOpen size={24} color="#164E33" />
            </div>
            <div>
              <h2>Knowledge Hub &amp; Enterprise Connectors</h2>
              <p>
                Connect your organization's tools to empower Cerebro RAG with accurate, verified evidence.
              </p>
            </div>
          </div>

          <button className="kh-start-chat-btn" onClick={onSwitchToChat}>
            <span>Go to AI Chat</span>
            <ArrowRight size={15} />
          </button>
        </div>

        {/* Stats Row */}
        <div className="kh-stats-grid">
          <div className="kh-stat-card">
            <span className="kh-stat-label">Connected Sources</span>
            <span className="kh-stat-value text-green">
              {connectedCount} <span className="kh-stat-sub">/ {eligibleSources.length}</span>
            </span>
          </div>

          <div className="kh-stat-card">
            <span className="kh-stat-label">RAG Retrieval Mode</span>
            <span className="kh-stat-value">Live Multi-Source</span>
          </div>

          <div className="kh-stat-card">
            <span className="kh-stat-label">Security &amp; Privacy</span>
            <span className="kh-stat-value" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <ShieldCheck size={16} color="#164E33" />
              <span>Enterprise Boundary</span>
            </span>
          </div>
        </div>
      </header>

      {/* Controls & Filter Toolbar */}
      <div className="kh-toolbar-row">
        <div className="kh-search-box">
          <Search size={16} color="#64748B" />
          <input
            type="text"
            placeholder="Search connectors by name, category, or keyword..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="kh-filter-tabs">
          <button
            className={`kh-tab-btn ${filterTab === 'all' ? 'active' : ''}`}
            onClick={() => setFilterTab('all')}
          >
            All ({eligibleSources.length})
          </button>
          <button
            className={`kh-tab-btn ${filterTab === 'connected' ? 'active' : ''}`}
            onClick={() => setFilterTab('connected')}
          >
            Connected ({connectedCount})
          </button>
          <button
            className={`kh-tab-btn ${filterTab === 'available' ? 'active' : ''}`}
            onClick={() => setFilterTab('available')}
          >
            Available ({availableCount})
          </button>
        </div>
      </div>

      {/* Connectors Grid */}
      <div className="kh-cards-grid">
        {filteredSources.map((source) => {
          const isLoading = isLoadingSourceId === source.id;

          return (
            <div
              key={source.id}
              className={`kh-connector-card ${source.is_connected ? 'kh-card-connected' : 'kh-card-disconnected'}`}
            >
              {/* Card Header */}
              <div className="kh-card-header">
                <div className="kh-card-header-left">
                  {getSourceIcon(source.id)}
                  <div>
                    <h3 className="kh-card-title">{source.name}</h3>
                    <span className="kh-category-tag">{getSourceCategory(source.id, source.type)}</span>
                  </div>
                </div>

                <span className={`kh-status-pill ${source.is_connected ? 'connected' : 'disconnected'}`}>
                  <span className={`kh-status-dot ${source.is_connected ? 'connected' : 'disconnected'}`}></span>
                  <span>{source.is_connected ? 'Connected' : 'Not Connected'}</span>
                </span>
              </div>

              {/* Description */}
              <p className="kh-card-desc">
                {source.description || `Search and retrieve data from ${source.name} within Dabur One RAG.`}
              </p>

              {/* Connected Account Info if applicable */}
              {source.is_connected && source.account && (
                <div className="kh-account-badge" title={source.account}>
                  <CheckCircle2 size={13} color="#164E33" />
                  <span>Account: {source.account}</span>
                </div>
              )}

              {/* Card Footer Actions */}
              <div className="kh-card-footer">
                {source.is_connected ? (
                  <div className="kh-actions-row">
                    {source.auth_type === 'credentials' && (
                      <button
                        type="button"
                        className="kh-btn-configure"
                        onClick={() => onConnectClick(source)}
                        title="Edit credentials"
                      >
                        <Settings2 size={13} />
                        <span>Configure</span>
                      </button>
                    )}

                    {source.auth_type !== 'info' && (
                      <button
                        type="button"
                        className="kh-btn-disconnect"
                        disabled={isLoading}
                        onClick={() => onDisconnectClick(source)}
                        title="Disconnect this service"
                      >
                        {isLoading ? 'Disconnecting...' : 'Disconnect'}
                      </button>
                    )}
                  </div>
                ) : (
                  <button
                    type="button"
                    className="kh-btn-connect"
                    onClick={() => onConnectClick(source)}
                    title="Connect this service"
                  >
                    <span>Connect {source.name}</span>
                    {source.auth_type === 'oauth' ? <ExternalLink size={13} /> : <ArrowRight size={13} />}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </main>
  );
};
