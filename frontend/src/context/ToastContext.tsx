import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import Toast, { ToastOptions } from '../components/Toast';

interface ToastContextType {
  toast: (message: string, options?: ToastOptions) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

interface ToastProviderProps {
  children: ReactNode;
}

export function ToastProvider({ children }: ToastProviderProps) {
  const [toasts, setToasts] = useState<Array<{ id: number; message: string; options?: ToastOptions }>>([]);

  const toast = useCallback((message: string, options?: ToastOptions) => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, options }]);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 5000);
  }, []);

  const dismissToast = useCallback((id: number) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      {/* Render toasts */}
      {toasts.map(({ id, message, options }) => (
        <Toast
          key={id}
          message={message}
          options={options}
          onDismiss={() => dismissToast(id)}
        />
      ))}
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextType {
  const context = useContext(ToastContext);
  if (context === undefined) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}
