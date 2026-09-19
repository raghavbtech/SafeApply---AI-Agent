import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './auth/AuthProvider';
import { ProtectedRoute } from './auth/ProtectedRoute';
import { AppShell } from './layouts/AppShell';

// Primary 6 Destinations & Utilities
import { Landing } from './pages/Landing';
import { Dashboard } from './pages/Dashboard';
import { ManualScan } from './pages/ManualScan';
import { Inbox } from './pages/Inbox';
import { Applications } from './pages/Applications';
import { Profile } from './pages/Profile';
import { Settings } from './pages/Settings';
import { Analysis } from './pages/Analysis';
import { NotFound } from './pages/NotFound';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 1000 * 30, // 30 seconds
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            {/* Public Landing Page */}
            <Route path="/" element={<Landing />} />

            {/* Account-Free Candidate Portal App Shell */}
            <Route
              element={
                <ProtectedRoute>
                  <AppShell />
                </ProtectedRoute>
              }
            >
              {/* Primary 6 Destinations */}
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/scan" element={<ManualScan />} />
              <Route path="/inbox" element={<Inbox />} />
              <Route path="/applications" element={<Applications />} />
              <Route path="/profile" element={<Profile />} />
              <Route path="/settings" element={<Settings />} />

              {/* In-depth Analysis View */}
              <Route path="/analysis" element={<Analysis />} />

              {/* Backward Compatibility Redirects */}
              <Route path="/quarantine" element={<Navigate to="/inbox?tab=quarantine" replace />} />
              <Route path="/spam" element={<Navigate to="/inbox?tab=quarantine" replace />} />
              <Route path="/verification" element={<Navigate to="/inbox?tab=inbox" replace />} />
              <Route path="/job-agent" element={<Navigate to="/applications?tab=opportunities" replace />} />
              <Route path="/jobs" element={<Navigate to="/applications?tab=opportunities" replace />} />
              <Route path="/audit" element={<Navigate to="/dashboard" replace />} />
            </Route>

            {/* Catch-all 404 Route */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

export default App;
