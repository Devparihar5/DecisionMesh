import type { Page } from '../hooks/useNavigation';

export function AppNavigation({ current }: { current: Page }) {
  return <div className="navigation-wrap"><header className="app-navigation">
    <a className="brand" href="#/" aria-label="DecisionMesh workspace"><span className="brand-mark">✳</span>
      <span>DecisionMesh<span className="brand-period">.</span><small>DECISION INTELLIGENCE</small></span>
    </a>
    <nav aria-label="Main navigation">
      <a href="#/" aria-current={current === 'workspace' ? 'page' : undefined}><span aria-hidden="true">⌘</span>Workspace</a>
      <a href="#/history" aria-current={current === 'history' ? 'page' : undefined}><span aria-hidden="true">◷</span>Run history</a>
      <a href="#/analytics" aria-current={current === 'analytics' ? 'page' : undefined}><span aria-hidden="true">▥</span>Analytics</a>
    </nav>
    <span className="local-memory-label"><i />Local memory</span>
  </header></div>;
}
