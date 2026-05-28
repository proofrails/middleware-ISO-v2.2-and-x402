import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from 'react';

type Toast = { id: number; message: string; variant: 'success' | 'info' };

type ToastContextValue = {
  showToast: (message: string, variant?: Toast['variant']) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

let toastId = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showToast = useCallback((message: string, variant: Toast['variant'] = 'success') => {
    const id = ++toastId;
    setToasts((t) => [...t, { id, message, variant }]);
    window.setTimeout(() => {
      setToasts((t) => t.filter((x) => x.id !== id));
    }, 3200);
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div
        className="pointer-events-none fixed bottom-6 right-6 z-[100] flex flex-col gap-2"
        aria-live="polite"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            className="pointer-events-auto rounded-lg border border-cyan-500/25 bg-slate-900/95 px-4 py-3 text-sm text-slate-100 shadow-[0_0_24px_rgba(34,211,238,0.12)] backdrop-blur-md transition-all duration-300"
          >
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}
