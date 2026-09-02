import React from 'react';
import phantomEmblem from '../../assets/branding/phantom-emblem.png';
import phantomWordmark from '../../assets/branding/phantom-wordmark.png';

interface LogoProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  showSubtitle?: boolean;
}

export const Logo: React.FC<LogoProps> = ({
  className = '',
  size = 'md',
}) => {
  const logoHeights = {
    sm: 30,
    md: 38,
    lg: 44,
  };

  const wordmarkHeights = {
    sm: 24,
    md: 30,
    lg: 36,
  };

  const currentLogoHeight = logoHeights[size];
  const currentWordmarkHeight = wordmarkHeights[size];

  return (
    <div
      className={`phantom-brand-logo ${className}`}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        userSelect: 'none',
        height: '100%',
      }}
    >
      {/* 1. 4K Clean Transparent PHANTOM Logo / Emblem (Left) */}
      <img
        src={phantomEmblem}
        alt="PHANTOM P-Camera Tactical Shield Emblem"
        style={{
          height: `${currentLogoHeight}px`,
          width: 'auto',
          aspectRatio: '1 / 1',
          objectFit: 'contain',
          display: 'block',
          flexShrink: 0,
          background: 'transparent',
          filter: 'drop-shadow(0 0 10px rgba(168, 85, 247, 0.45))',
        }}
      />

      {/* 2. 4K Clean Transparent PHANTOM Wordmark (Right) */}
      <img
        src={phantomWordmark}
        alt="PHANTOM 360° AI Surveillance"
        style={{
          height: `${currentWordmarkHeight}px`,
          width: 'auto',
          maxWidth: size === 'sm' ? '180px' : size === 'md' ? '280px' : '340px',
          objectFit: 'contain',
          display: 'block',
          flexShrink: 0,
          background: 'transparent',
          filter: 'drop-shadow(0 0 12px rgba(168, 85, 247, 0.35))',
        }}
      />
    </div>
  );
};
