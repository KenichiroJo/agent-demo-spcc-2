import { PATHS } from '@/constants/path.ts';
import { lazy } from 'react';
import { Navigate } from 'react-router-dom';

const OAuthCallback = lazy(() => import('./pages/OAuthCallback'));
const SpccPage = lazy(() => import('./pages/SpccPage'));

// Existing chat / settings UI is intentionally disabled while this build is
// dedicated to the SPCC emotion karte app. The route definitions below are
// preserved in source as a reference and can be re-enabled in the future.
//
// import { SettingsLayout } from './pages/SettingsLayout';
// import { ChatPage } from './pages/ChatPage';
// import { EmptyStatePage } from './pages/EmptyState.tsx';
// import { MainLayout } from './pages/MainLayoutWithChatList';
//
// const legacyRoutes = {
//   element: <MainLayout />,
//   children: [
//     { path: PATHS.CHAT_EMPTY, element: <EmptyStatePage /> },
//     { path: PATHS.CHAT, element: <ChatPage /> },
//     { path: PATHS.SETTINGS.ROOT, element: <SettingsLayout /> },
//   ],
// };

export const appRoutes = [
  { path: PATHS.OAUTH_CB, element: <OAuthCallback /> },
  { path: '/', element: <Navigate to={PATHS.SPCC.ROOT} replace /> },
  { path: PATHS.SPCC.ROOT, element: <SpccPage /> },
  { path: '*', element: <Navigate to={PATHS.SPCC.ROOT} replace /> },
];
