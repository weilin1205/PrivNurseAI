// app/providers.tsx

import { ChakraProvider } from '@chakra-ui/react'
import { NavbarProvider } from '@/contexts/NavbarContext'
import { AuthProvider } from '@/contexts/AuthContext';
import { DemoModeProvider } from '@/contexts/DemoModeContext';

export function Providers({ children }: { children: React.ReactNode }) {
    return (
        <ChakraProvider>
            <NavbarProvider>
                <AuthProvider>
                    <DemoModeProvider>
                        {children} 
                    </DemoModeProvider>
                </AuthProvider>
            </NavbarProvider>
        </ChakraProvider>
    )
}