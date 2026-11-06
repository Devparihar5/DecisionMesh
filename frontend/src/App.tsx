import { WorkspacePage } from './pages/WorkspacePage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { HistoryPage } from './pages/HistoryPage';
import { AppNavigation } from './components/AppNavigation';
import { useNavigation } from './hooks/useNavigation';
import { EnterprisePage } from './pages/EnterprisePage';
import { ResearchPage } from './pages/ResearchPage';

export function App() {
  const page = useNavigation();
  return <>
    <AppNavigation current={page} />
    {/* Keep the live workspace mounted while browsing history or analytics. */}
    <div hidden={page !== 'workspace'}><WorkspacePage active={page === 'workspace'} /></div>
    {page === 'history' && <HistoryPage />}
    {page === 'analytics' && <AnalyticsPage />}
    {page === 'enterprise' && <EnterprisePage />}
    {page === 'research' && <ResearchPage />}
  </>;
}
