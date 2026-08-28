import React from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Input: React.FC<InputProps> = ({
  label,
  error,
  helperText,
  className = '',
  id,
  ...props
}) => {
  const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

  return (
    <div className="flex flex-col gap-1.5 w-full">
      {label && (
        <label htmlFor={inputId} className="text-xs font-semibold text-dark-muted uppercase tracking-wider">
          {label}
        </label>
      )}
      <input
        id={inputId}
        className={`bg-dark-bg border border-dark-border rounded px-3 py-1.5 text-sm text-dark-text placeholder-dark-muted/60 focus:outline-none focus:border-netpulse-blue transition-colors font-mono ${
          error ? 'border-netpulse-red focus:border-netpulse-red' : ''
        } ${className}`}
        {...props}
      />
      {error && <p className="text-xs text-netpulse-red">{error}</p>}
      {helperText && !error && <p className="text-xs text-dark-muted">{helperText}</p>}
    </div>
  );
};
