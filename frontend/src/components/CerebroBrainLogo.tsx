import React from 'react';

interface CerebroBrainLogoProps {
  size?: number;
  className?: string;
  showGlow?: boolean;
}

export const CerebroBrainLogo: React.FC<CerebroBrainLogoProps> = ({
  size = 32,
  className = '',
  showGlow = true,
}) => {
  return (
    <div
      className={`cerebro-brain-logo-container ${className}`}
      style={{
        width: size,
        height: size,
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
        filter: showGlow
          ? 'drop-shadow(0 0 10px rgba(6, 182, 212, 0.45)) drop-shadow(0 0 16px rgba(192, 38, 211, 0.4))'
          : undefined,
        flexShrink: 0,
      }}
    >
      <img
        src="/cerebro_brain_logo.png"
        alt="Cerebro Neural Brain Logo"
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'contain',
          display: 'block',
          userSelect: 'none',
        }}
        draggable={false}
      />
    </div>
  );
};
