import type { ReactNode } from 'react';

type PageContainerProps = {
  children: ReactNode;
  className?: string;
};

export function PageContainer({ children, className = '' }: PageContainerProps) {
  return (
    <div className={`mx-auto w-full max-w-[1400px] px-6 py-8 lg:px-10 ${className}`}>
      {children}
    </div>
  );
}
