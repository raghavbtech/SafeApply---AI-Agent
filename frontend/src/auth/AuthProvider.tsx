import React, { createContext, useContext, useState, useEffect } from 'react';
import { SessionStatusResponse, UserPrincipal } from '../api/contracts';
import { api } from '../api/client';

interface SessionContextType {
  session: SessionStatusResponse | null;
  user: UserPrincipal | null;
  loading: boolean;
  refreshSession: () => Promise<void>;
  purgeData: () => Promise<void>;
}

const SessionContext = createContext<SessionContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [session, setSession] = useState<SessionStatusResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const refreshSession = async () => {
    try {
      const sess = await api.getSession();
      setSession(sess);
    } catch {
      setSession(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshSession();
  }, []);

  const purgeData = async () => {
    setLoading(true);
    try {
      await api.purgeSessionData();
      // Immediately obtain a fresh session for the visitor
      await refreshSession();
    } finally {
      setLoading(false);
    }
  };

  const user: UserPrincipal | null = session
    ? {
        session_id: session.session_id,
        user_id: session.session_id,
        created_at: session.created_at,
        email: `${session.session_id}@anonymous.safeapply.local`,
        full_name: 'Candidate (Anonymous Session)',
        role: 'anonymous_candidate',
      }
    : null;

  return (
    <SessionContext.Provider value={{ session, user, loading, refreshSession, purgeData }}>
      {children}
    </SessionContext.Provider>
  );
};

export const SessionProvider = AuthProvider;

export const useSession = () => {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error('useSession must be used within SessionProvider');
  return ctx;
};

export const useAuth = useSession;
