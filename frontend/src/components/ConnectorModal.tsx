import React, { useState } from 'react';
import { X, Eye, EyeOff, ExternalLink, Loader2, AlertCircle, CheckCircle } from 'lucide-react';
import { ConnectorSource } from '../types/chat';

interface ConnectorModalProps {
  source: ConnectorSource;
  onClose: () => void;
  onSave: (connectorId: string, credentials: Record<string, string>) => Promise<void>;
}

export const ConnectorModal: React.FC<ConnectorModalProps> = ({
  source,
  onClose,
  onSave,
}) => {
  // Initialize form state with default_value if available
  const [formData, setFormData] = useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {};
    source.config_fields?.forEach((f) => {
      initial[f.key] = f.default_value || '';
    });
    return initial;
  });

  const [showPasswords, setShowPasswords] = useState<Record<string, boolean>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const togglePasswordVisibility = (key: string) => {
    setShowPasswords((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleChange = (key: string, value: string) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
    if (errorMessage) setErrorMessage(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);

    // Validate required fields
    for (const field of source.config_fields || []) {
      if (field.required && !formData[field.key]?.trim()) {
        setErrorMessage(`Please enter ${field.label}.`);
        return;
      }
    }

    setIsSubmitting(true);
    try {
      await onSave(source.id, formData);
      setSuccessMessage('Connected successfully!');
      setTimeout(() => {
        onClose();
      }, 1000);
    } catch (err: any) {
      setErrorMessage(err.message || 'Connection test failed. Please verify your credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="connector-modal-overlay" onClick={onClose}>
      <div
        className="connector-modal-container"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        {/* Modal Header */}
        <div className="connector-modal-header">
          <div className="modal-title-group">
            <h3>Configure {source.name}</h3>
            {source.description && (
              <p className="modal-subtitle">{source.description}</p>
            )}
          </div>
          <button
            type="button"
            className="modal-close-btn"
            onClick={onClose}
            aria-label="Close dialog"
          >
            <X size={18} />
          </button>
        </div>

        {/* Status Alerts */}
        {errorMessage && (
          <div className="modal-alert modal-alert-error">
            <AlertCircle size={16} className="alert-icon" />
            <span>{errorMessage}</span>
          </div>
        )}

        {successMessage && (
          <div className="modal-alert modal-alert-success">
            <CheckCircle size={16} className="alert-icon" />
            <span>{successMessage}</span>
          </div>
        )}

        {/* Configuration Form */}
        <form onSubmit={handleSubmit} className="connector-modal-form">
          <div className="modal-fields-list">
            {source.config_fields?.map((field) => {
              const isPassword = field.type === 'password';
              const isVisible = showPasswords[field.key];
              const inputType = isPassword ? (isVisible ? 'text' : 'password') : 'text';

              return (
                <div key={field.key} className="modal-field-group">
                  <div className="modal-field-label-row">
                    <label htmlFor={field.key} className="modal-field-label">
                      {field.label}
                      {field.required && <span className="text-danger">*</span>}
                    </label>
                    {field.help_url && (
                      <a
                        href={field.help_url}
                        target="_blank"
                        rel="noreferrer"
                        className="modal-field-help-link"
                      >
                        Get Token <ExternalLink size={12} />
                      </a>
                    )}
                  </div>

                  <div className="modal-input-wrapper">
                    <input
                      id={field.key}
                      type={inputType}
                      className="modal-text-input"
                      placeholder={field.placeholder}
                      value={formData[field.key] || ''}
                      onChange={(e) => handleChange(field.key, e.target.value)}
                      disabled={isSubmitting}
                      autoComplete="off"
                    />
                    {isPassword && (
                      <button
                        type="button"
                        className="password-toggle-btn"
                        onClick={() => togglePasswordVisibility(field.key)}
                        tabIndex={-1}
                        title={isVisible ? 'Hide value' : 'Show value'}
                      >
                        {isVisible ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    )}
                  </div>

                  {field.help_text && (
                    <span className="modal-field-help-text">{field.help_text}</span>
                  )}
                </div>
              );
            })}
          </div>

          {/* Modal Actions */}
          <div className="connector-modal-actions">
            <button
              type="button"
              className="modal-btn modal-btn-cancel"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="modal-btn modal-btn-submit"
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <Loader2 size={16} className="spinner" />
                  <span>Testing Connection...</span>
                </>
              ) : (
                <span>Save & Test Connection</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
