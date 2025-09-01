// frontend/src/components/Toast.tsx
import { useEffect, useState } from 'react';

export type ToastType = 'success' | 'error';

export interface ToastProps {
  type: ToastType;
  message: string;
  onClose: () => void;
  duration?: number;
}

export default function Toast({ type, message, onClose, duration = 5000 }: ToastProps) {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(false);
      setTimeout(onClose, 300); // Wait for fade out animation
    }, duration);

    return () => clearTimeout(timer);
  }, [duration, onClose]);

  const baseClasses = "fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg transition-opacity duration-300";
  const typeClasses = type === 'success' 
    ? "bg-green-50 text-green-800 border border-green-200" 
    : "bg-red-50 text-red-800 border border-red-200";

  return (
    <div className={`${baseClasses} ${typeClasses} ${isVisible ? 'opacity-100' : 'opacity-0'}`}>
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{message}</span>
        <button
          onClick={() => {
            setIsVisible(false);
            setTimeout(onClose, 300);
          }}
          className="ml-4 text-gray-400 hover:text-gray-600"
        >
          ×
        </button>
      </div>
    </div>
  );
}
