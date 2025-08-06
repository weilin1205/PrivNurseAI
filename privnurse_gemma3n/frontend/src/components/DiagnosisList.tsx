'use client'

import React from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Badge,
  Flex,
  Heading
} from '@chakra-ui/react';

export interface Diagnosis {
  category: string; // 'Primary', 'Secondary', 'Past', 'Current'
  diagnosis: string;
  code?: string; // ICD-10 or other medical codes
  date_diagnosed?: string;
}

interface DiagnosisListProps {
  diagnoses: Diagnosis[];
  onChange: (diagnoses: Diagnosis[]) => void;
  isReadOnly?: boolean;
}

export default function DiagnosisList({ diagnoses = [], onChange, isReadOnly = false }: DiagnosisListProps) {
  // Ensure diagnoses is always an array
  const normalizedDiagnoses = Array.isArray(diagnoses) ? diagnoses : [];

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'Primary': return 'red';
      case 'Secondary': return 'orange';
      case 'Past': return 'gray';
      case 'Current': return 'blue';
      default: return 'gray';
    }
  };

  const DiagnosisItem = ({ diagnosis, index }: { diagnosis: Diagnosis; index: number }) => {
    return (
      <Box p={4} borderWidth={1} borderRadius="md" bg="white" shadow="sm">
        <Flex align="start">
          <VStack align="start" spacing={2} flex={1}>
            <HStack spacing={3}>
              <Badge colorScheme={getCategoryColor(diagnosis.category)} size="md">
                {diagnosis.category}
              </Badge>
              {diagnosis.code && (
                <Text fontSize="sm" color="gray.600" fontFamily="mono">
                  {diagnosis.code}
                </Text>
              )}
              {diagnosis.date_diagnosed && (
                <Text fontSize="sm" color="gray.500">
                  {new Date(diagnosis.date_diagnosed).toLocaleDateString()}
                </Text>
              )}
            </HStack>
            <Text fontSize="md" fontWeight="medium">
              {diagnosis.diagnosis}
            </Text>
          </VStack>
          
        </Flex>
      </Box>
    );
  };

  return (
    <Box display="flex" flexDirection="column" height="100%">
      <HStack mb={4} justifyContent="space-between">
        <Heading as="h3" size="sm">
          Diagnoses ({normalizedDiagnoses.length})
        </Heading>
      </HStack>

      <Box 
        flex="1" 
        overflowY="auto" 
        maxHeight="300px"
        pr={2}
        css={{
          '&::-webkit-scrollbar': {
            width: '4px',
          },
          '&::-webkit-scrollbar-track': {
            width: '6px',
          },
          '&::-webkit-scrollbar-thumb': {
            background: '#CBD5E0',
            borderRadius: '24px',
          },
        }}
      >
        <VStack spacing={3} align="stretch">
          {/* Display existing diagnoses */}
          {normalizedDiagnoses.length > 0 ? (
            normalizedDiagnoses.map((diagnosis, index) => (
              <DiagnosisItem key={index} diagnosis={diagnosis} index={index} />
            ))
          ) : (
            <Box p={6} textAlign="center" bg="gray.50" borderRadius="md">
              <Text color="gray.500">
                No diagnoses recorded
              </Text>
            </Box>
          )}
        </VStack>
      </Box>
    </Box>
  );
}