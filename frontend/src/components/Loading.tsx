import React from 'react';

export const Loading: React.FC<{ label?: string; message?: string }> = ({ 
  label, 
  message = 'Loading SafeApply data...' 
}) => {
  const displayText = label || message;
  return (
    <div className="flex h-64 w-full flex-col items-center justify-center gap-4">
      <div className="relative flex h-12 w-12 items-center justify-center">
        <div className="absolute h-full w-full animate-spin rounded-full border-2 border-cyan-500/20 border-t-cyan-400" />
        <div className="h-6 w-6 rounded-full bg-cyan-500/10 shadow-neon-cyan" />
      </div>
      <p className="text-sm font-medium text-slate-400 animate-pulse">{displayText}</p>
    </div>
  );
};
export default Loading;
