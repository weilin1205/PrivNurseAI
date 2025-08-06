'use client'

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { Spinner, Center } from '@chakra-ui/react';

export default function AuthGuard({ children, adminRequired = false }: { 
  children: React.ReactNode;
  adminRequired?: boolean;
}) {
  const router = useRouter();
  const { user, isAdmin, isLoading } = useAuth();

  useEffect(() => {
    // Wait for auth context to finish loading
    if (isLoading) return;

    // If no user after loading completes, redirect to login
    if (!user) {
      router.replace('/login');
      return;
    }

    // If admin required but user is not admin
    if (adminRequired && !isAdmin()) {
      router.replace('/summary');
      return;
    }
  }, [router, adminRequired, isAdmin, user, isLoading]);

  // Show loading while auth context is initializing
  if (isLoading) {
    return (
      <Center h="100vh">
        <Spinner size="xl" />
      </Center>
    );
  }

  // If no user after loading, don't render children
  if (!user) {
    return (
      <Center h="100vh">
        <Spinner size="xl" />
      </Center>
    );
  }

  return <>{children}</>;
}
