import type { ReactNode } from 'react';

interface Props {
  index: string;
  title: string;
  children: ReactNode;
  action?: ReactNode;
  className?: string;
}

export function Panel({ index, title, children, action, className = '' }: Props) {
  return (
    <section className={`panel ${className}`} aria-label={title}>
      <div className="panel-head">
        <div><span className="section-index">{index}</span><h2>{title}</h2></div>
        {action}
      </div>
      {children}
    </section>
  );
}
