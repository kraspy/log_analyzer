/**
 * Root application component with routing, theme and query providers.
 * @module App
 */
import { BrowserRouter, Routes, Route, Navigate } from 'react-router';
import { ConfigProvider, App as AntApp, theme } from 'antd';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { lazy, Suspense } from 'react';
import { Spin } from 'antd';

import { ThemeProvider, useTheme } from './contexts/ThemeContext';
import { AppLayout } from './components/Layout/AppLayout';

// Lazy-loaded pages — each becomes a separate chunk
// Only loaded when the user navigates to the route
const DashboardPage = lazy(() =>
  import('./pages/DashboardPage').then((m) => ({ default: m.DashboardPage }))
);
const UploadPage = lazy(() =>
  import('./pages/UploadPage').then((m) => ({ default: m.UploadPage }))
);
const ReportPage = lazy(() =>
  import('./pages/ReportPage').then((m) => ({ default: m.ReportPage }))
);

// TanStack Query client — caches server data, handles refetching
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes before data is considered stale
      retry: 1,
    },
  },
});

/**
 * Inner app — reads theme context and applies Ant Design algorithm.
 *
 * Separated from App() because useTheme() needs to be called
 * inside the ThemeProvider tree.
 */
function ThemedApp() {
  const { isDark } = useTheme();

  const PageLoader = <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;

  return (
    <ConfigProvider
      theme={{
        algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
        token: {
          colorPrimary: '#1677ff',
          borderRadius: 8,
        },
      }}
    >
      <AntApp>
        <BrowserRouter>
          <Routes>
            <Route element={<AppLayout />}>
              <Route
                path="/"
                element={
                  <Suspense fallback={PageLoader}>
                    <DashboardPage />
                  </Suspense>
                }
              />
              <Route
                path="/upload"
                element={
                  <Suspense fallback={PageLoader}>
                    <UploadPage />
                  </Suspense>
                }
              />
              <Route
                path="/report/:id"
                element={
                  <Suspense fallback={PageLoader}>
                    <ReportPage />
                  </Suspense>
                }
              />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AntApp>
    </ConfigProvider>
  );
}

/**
 * Root component: ThemeProvider wraps everything so useTheme() is available.
 */
function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <ThemedApp />
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
