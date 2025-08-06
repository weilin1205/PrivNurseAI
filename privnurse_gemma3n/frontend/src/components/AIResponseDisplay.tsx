import React from 'react';
import { Box, Text, VStack, Divider, Badge } from '@chakra-ui/react';

interface AIResponseDisplayProps {
  response: string;
}

const AIResponseDisplay: React.FC<AIResponseDisplayProps> = ({ response }) => {
  // Check if response contains opening tags (for streaming support)
  const hasThinkingStart = response.includes('<thinking>');
  const hasAnswerStart = response.includes('<answer>');
  
  // Parse complete thinking and answer tags
  const thinkingMatch = response.match(/<thinking>([\s\S]*?)<\/thinking>/);
  const answerMatch = response.match(/<answer>([\s\S]*?)<\/answer>/);
  
  // Handle partial tags during streaming
  let thinking = '';
  let answer = '';
  let isThinkingPartial = false;
  let isAnswerPartial = false;
  
  if (thinkingMatch) {
    // Complete thinking tag found
    thinking = thinkingMatch[1].trim();
  } else if (hasThinkingStart) {
    // Partial thinking tag (still streaming)
    const thinkingStartIndex = response.indexOf('<thinking>') + '<thinking>'.length;
    const thinkingEndIndex = response.indexOf('</thinking>');
    
    if (thinkingEndIndex === -1) {
      // Tag not closed yet
      thinking = response.substring(thinkingStartIndex).trim();
      isThinkingPartial = true;
    }
  }
  
  if (answerMatch) {
    // Complete answer tag found
    answer = answerMatch[1].trim();
  } else if (hasAnswerStart) {
    // Partial answer tag (still streaming)
    const answerStartIndex = response.indexOf('<answer>') + '<answer>'.length;
    const answerEndIndex = response.indexOf('</answer>');
    
    if (answerEndIndex === -1) {
      // Tag not closed yet
      answer = response.substring(answerStartIndex).trim();
      isAnswerPartial = true;
    }
  }
  
  const hasStructuredFormat = hasThinkingStart || hasAnswerStart;
  
  if (!hasStructuredFormat) {
    // If no tags found, display as plain text
    return (
      <Box>
        <pre className="whitespace-pre-wrap" style={{ fontFamily: 'inherit', fontSize: 'inherit' }}>
          {response}
        </pre>
      </Box>
    );
  }
  
  return (
    <VStack spacing={4} align="stretch">
      {(thinking || isThinkingPartial) && (
        <Box>
          <Badge colorScheme="blue" mb={2}>
            Reasoning Process {isThinkingPartial && '(streaming...)'}
          </Badge>
          <Box
            p={3}
            borderRadius="md"
            backgroundColor="blue.50"
            borderLeft="4px solid"
            borderLeftColor="blue.400"
          >
            <Text fontSize="sm" color="gray.700" whiteSpace="pre-wrap">
              {thinking}
              {isThinkingPartial && (
                <Box as="span" display="inline-block" animation="pulse 1.5s infinite">
                  ▊
                </Box>
              )}
            </Text>
          </Box>
        </Box>
      )}
      
      {thinking && answer && <Divider />}
      
      {(answer || isAnswerPartial) && (
        <Box>
          <Badge colorScheme="green" mb={2}>
            Summary {isAnswerPartial && '(streaming...)'}
          </Badge>
          <Box
            p={3}
            borderRadius="md"
            backgroundColor="green.50"
            borderLeft="4px solid"
            borderLeftColor="green.400"
          >
            <Text fontSize="sm" color="gray.800" whiteSpace="pre-wrap" fontWeight="medium">
              {answer}
              {isAnswerPartial && (
                <Box as="span" display="inline-block" animation="pulse 1.5s infinite">
                  ▊
                </Box>
              )}
            </Text>
          </Box>
        </Box>
      )}
    </VStack>
  );
};

export default AIResponseDisplay;