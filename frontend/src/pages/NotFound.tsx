import React from 'react';
import { Link } from 'react-router-dom';
import { ShieldAlert, ArrowLeft } from 'lucide-react';

export const NotFound: React.FC = () => {
  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center text-center p-6 space-y-4">
      <div className="p-4 rounded-2xl bg-neon-coral/10 border border-neon-coral/30 text-neon-coral">
        <ShieldAlert className="w-12 h-12" />
      </div>
      <h1 className="text-3xl font-bold text-white tracking-tight">404 - Dossier Not Found</h1>
      <p className="text-slate-400 max-w-md text-sm">
        The requested endpoint or record does not exist in SafeApply's cryptographic routing index.
      </p>
      <Link
        to="/dashboard"
        className="mt-2 inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-neon-cyan hover:bg-neon-cyan/90 text-black font-semibold text-xs transition-all shadow-glow-cyan"
      >
        <ArrowLeft className="w-4 h-4" />
        Return to Safety Dashboard
      </Link>
    </div>
  );
};
export default NotFound;
