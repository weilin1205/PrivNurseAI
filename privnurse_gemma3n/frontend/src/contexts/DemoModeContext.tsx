'use client'

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface DemoModeContextType {
  isDemoMode: boolean;
  setDemoMode: (value: boolean) => void;
}

const DemoModeContext = createContext<DemoModeContextType | undefined>(undefined);

export function DemoModeProvider({ children }: { children: ReactNode }) {
  const [isDemoMode, setIsDemoMode] = useState(false);

  useEffect(() => {
    // Check demo mode status from auth config
    const checkDemoMode = async () => {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth-config`);
        const config = await response.json();
        setIsDemoMode(config.demo_mode || false);
      } catch (error) {
        console.error('Failed to check demo mode:', error);
      }
    };

    checkDemoMode();
  }, []);

  return (
    <DemoModeContext.Provider value={{ isDemoMode, setDemoMode: setIsDemoMode }}>
      {children}
    </DemoModeContext.Provider>
  );
}

export function useDemoMode() {
  const context = useContext(DemoModeContext);
  if (context === undefined) {
    throw new Error('useDemoMode must be used within a DemoModeProvider');
  }
  return context;
}