'use client'

import { useDemoMode } from '@/contexts/DemoModeContext';
import { Box, Text } from '@chakra-ui/react';

export function DemoModeIndicator() {
  const { isDemoMode } = useDemoMode();

  if (!isDemoMode) {
    return null;
  }

  return (
    <Box
      position="fixed"
      top="0"
      left="50%"
      transform="translateX(-50%)"
      bg="orange.500"
      color="white"
      px={4}
      py={1}
      borderBottomRadius="md"
      boxShadow="md"
      zIndex={9999}
    >
      <Text fontSize="sm" fontWeight="bold">
        DEMO MODE - Read Only
      </Text>
    </Box>
  );
}