import React from 'react';
import { useSession } from './AuthProvider';

export const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { loading } = useSession();

  if (loading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-dark-950">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-2 border-neon-cyan border-t-transparent shadow-neon-cyan" />
          <span className="text-sm font-medium text-slate-400">Initializing anonymous session...</span>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};
