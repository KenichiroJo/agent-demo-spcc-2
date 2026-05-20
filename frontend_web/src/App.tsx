import Pages from '@/pages';

// SidebarProvider is intentionally removed for the SPCC build. The legacy
// chat / settings routes that depended on the sidebar context are disabled
// in routesConfig.tsx, so wrapping the tree in a flex container was causing
// the SPCC page to render at intrinsic width instead of filling the viewport.
export function App() {
  return <Pages />;
}
