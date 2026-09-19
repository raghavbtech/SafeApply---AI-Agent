import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './auth/AuthProvider';
import { ProtectedRoute } from './auth/ProtectedRoute';
import { AppShell } from './layouts/AppShell';

// Page Imports
import { Landing } from './pages/Landing';
import { Dashboard } from './pages/Dashboard';
import { Inbox } from './pages/Inbox';
import { ManualScan } from './pages/ManualScan';
import { Spam } from './pages/Spam';
import { Verification } from './pages/Verification';
import { JobAgent } from './pages/JobAgent';
import { Applications } from './pages/Applications';
import { Profile } from './pages/Profile';
import { Settings } from './pages/Settings';
import { Audit } from './pages/Audit';
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
            {/* Public Routes */}
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Landing />} />

            {/* Authenticated Application Shell */}
            <Route
              element={
                <ProtectedRoute>
                  <AppShell />
                </ProtectedRoute>
              }
            >
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/inbox" element={<Inbox />} />
              <Route path="/scan" element={<ManualScan />} />
              <Route path="/quarantine" element={<Spam />} />
              <Route path="/spam" element={<Spam />} />
              <Route path="/verification" element={<Verification />} />
              <Route path="/job-agent" element={<JobAgent />} />
              <Route path="/jobs" element={<JobAgent />} />
              <Route path="/applications" element={<Applications />} />
              <Route path="/profile" element={<Profile />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/audit" element={<Audit />} />
              <Route path="/analysis" element={<Analysis />} />
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
