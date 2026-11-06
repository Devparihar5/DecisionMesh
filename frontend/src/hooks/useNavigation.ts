import { useEffect, useState } from 'react';

export type Page = 'workspace' | 'history' | 'analytics' | 'enterprise' | 'research';

function page(): Page {
  const hash = window.location.hash;
  if (hash.startsWith('#/history')) return 'history';
  if (hash.startsWith('#/analytics')) return 'analytics';
  if (hash.startsWith('#/enterprise')) return 'enterprise';
  if (hash.startsWith('#/research')) return 'research';
  return 'workspace';
}

/** Hash routes work identically with the local dev server and static preview. */
export function useNavigation() {
  const [current, setCurrent] = useState<Page>(page);
  useEffect(() => {
    const update = () => setCurrent(page());
    window.addEventListener('hashchange', update);
    return () => window.removeEventListener('hashchange', update);
  }, []);
  return current;
}
