import React from 'react';
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
} from 'lucide-react';
import { ConnectorSource } from '../types/chat';

interface SourcePanelProps {
  sources: ConnectorSource[];
  connectedCount: number;
  totalCount: number;
}

export const SourcePanel: React.FC<SourcePanelProps> = ({
  sources,
  connectedCount,
  totalCount,
}) => {
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
        <span className="source-count-badge">{connectedCount ?? 7}</span>
      </div>

      {/* Sources List */}
      <div className="source-list">
        {sources.map((src) => (
          <div key={src.id} className="source-item-card">
            <div className="flex-center gap-12">
              {renderSourceIcon(src.id)}
              <div className="source-item-info">
                <span className="source-item-name">{src.name}</span>
                <span className={`source-status-badge ${getBadgeClass(src.status)}`}>
                  <span className="status-dot"></span>
                  {src.status}
                </span>
              </div>
            </div>
          </div>
        ))}
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
            <span>Ask for source references in answers</span>
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
    </aside>
  );
};
