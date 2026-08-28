import React from 'react';

export type BadgeVariant = 'default' | 'success' | 'danger' | 'warning' | 'info' | 'purple' | 'outline';

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  size?: 'sm' | 'md';
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  size = 'sm',
  className = '',
  ...props
}) => {
  const variantStyles: Record<BadgeVariant, string> = {
    default: 'bg-dark-hover text-dark-text border-dark-border',
    success: 'bg-netpulse-green/15 text-netpulse-green border-netpulse-green/30',
    danger: 'bg-netpulse-red/15 text-netpulse-red border-netpulse-red/30',
    warning: 'bg-netpulse-yellow/15 text-netpulse-yellow border-netpulse-yellow/30',
    info: 'bg-netpulse-blue/15 text-netpulse-blue border-netpulse-blue/30',
    purple: 'bg-netpulse-purple/15 text-netpulse-purple border-netpulse-purple/30',
    outline: 'bg-transparent text-dark-muted border-dark-border',
  };

  const sizeStyles = {
    sm: 'text-[11px] px-2 py-0.5',
    md: 'text-xs px-2.5 py-1',
  };

  return (
    <span
      className={`inline-flex items-center gap-1 font-mono font-medium rounded border ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
      {...props}
    >
      {children}
    </span>
  );
};
