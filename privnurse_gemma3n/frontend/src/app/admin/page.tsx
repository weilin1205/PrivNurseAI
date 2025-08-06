'use client'

import React, { useState, useEffect } from 'react';
import { Box, VStack, Heading, Select, Button, useToast, Text, Link } from '@chakra-ui/react';
import OverlayComponent from "@/components/Overlay";
import { fetchWithAuth } from '@/utils/api';
import AuthGuard  from '@/components/AuthGuard';

export default function AdminPage() {
  return (
    <AuthGuard adminRequired>
      <AdminPageContent />
    </AuthGuard>
  );
}

function AdminPageContent() {
  const [selectedDischargeNoteSummaryModel, setSelectedDischargeNoteSummaryModel] = useState('');
  const [selectedDischargeNoteValidationModel, setSelectedDischargeNoteValidationModel] = useState('');
  const [selectedAudioTranscriptionModel, setSelectedAudioTranscriptionModel] = useState('google/gemma-3n-E4B-it');
  const [selectedConsultationSummaryModel, setSelectedConsultationSummaryModel] = useState('');
  const [selectedConsultationValidationModel, setSelectedConsultationValidationModel] = useState('');
  
  const [dischargeNoteSummaryModels, setDischargeNoteSummaryModels] = useState<string[]>([]);
  const [dischargeNoteValidationModels, setDischargeNoteValidationModels] = useState<string[]>([]);
  const [audioTranscriptionModels, setAudioTranscriptionModels] = useState<string[]>([]);
  const [consultationSummaryModels, setConsultationSummaryModels] = useState<string[]>([]);
  const [consultationValidationModels, setConsultationValidationModels] = useState<string[]>([]);
  
  const toast = useToast();

  useEffect(() => {
    const fetchAndFilterModels = async () => {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/tags`);
        if (!response.ok) {
          throw new Error('Cannot get model list');
        }
        const data = await response.json();
        const allModels = data.models.map((model: any) => model.name);
        
        setDischargeNoteSummaryModels(allModels.filter((model: string) => 
          model.toLowerCase().includes('note') && model.toLowerCase().includes('summary')
        ));
        setDischargeNoteValidationModels(allModels.filter((model: string) => 
          model.toLowerCase().includes('note') && model.toLowerCase().includes('validation')
        ));
        setAudioTranscriptionModels(allModels.filter((model: string) => 
          model.toLowerCase().includes('audio')
        ));
        setConsultationSummaryModels(allModels.filter((model: string) => 
          model.toLowerCase().includes('consult') && model.toLowerCase().includes('summary')
        ));
        setConsultationValidationModels(allModels.filter((model: string) => 
          model.toLowerCase().includes('consult') && model.toLowerCase().includes('validation')
        ));
      } catch (error) {
        console.error('Error fetching models:', error);
        toast({
          title: "Error",
          description: "Cannot get model list",
          status: "error",
          duration: 3000,
          isClosable: true,
        });
      }
    };

    fetchAndFilterModels();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const fetchActiveModels = async () => {
      try {
        const response = await fetchWithAuth('/api/active-models');
        if (!response.ok) {
          throw new Error('Cannot get current model settings');
        }
        const data = await response.json();
        
        // Map the new API response to model selections
        setSelectedConsultationSummaryModel(data.consultationSummaryModel || '');
        setSelectedConsultationValidationModel(data.consultationValidationModel || '');
        setSelectedDischargeNoteSummaryModel(data.dischargeNoteSummaryModel || '');
        setSelectedDischargeNoteValidationModel(data.dischargeNoteValidationModel || '');
        // Audio model is fixed, don't update it from the API
        // setSelectedAudioTranscriptionModel(data.audioModel || '');
      } catch (error) {
        console.error('Error fetching active models:', error);
        toast({
          title: "Warning",
          description: "Cannot get current model settings",
          status: "warning",
          duration: 3000,
          isClosable: true,
        });
      }
    };

    fetchActiveModels();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSubmit = async () => {
    try {
      const response = await fetchWithAuth('/api/active-models', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          consultation_summary_model: selectedConsultationSummaryModel,
          consultation_validation_model: selectedConsultationValidationModel,
          discharge_note_summary_model: selectedDischargeNoteSummaryModel,
          discharge_note_validation_model: selectedDischargeNoteValidationModel,
          audio_model: 'google/gemma-3n-E4B-it' // Always use the fixed model
        })
      });

      if (!response.ok) {
        throw new Error('Failed to update active models');
      }

      toast({
        title: "Success",
        description: "Model settings updated",
        status: "success",
        duration: 3000,
        isClosable: true,
      });
    } catch (error) {
      console.error('Error updating active models:', error);
      toast({
        title: "Error",
        description: "Failed to update model settings",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    }
  };

  return (
    <OverlayComponent>
      <Box 
        width="100%"
        maxWidth="900px" 
        backgroundColor="white" 
        borderRadius="lg" 
        boxShadow="lg"
        p={6}
        my={4}
      >
        <Heading as="h1" size="xl" mb={4}>AI Model Management</Heading>
        <Text mb={6} color="gray.600">
          Configure AI models for different types of medical documentation processing. Models are automatically filtered based on their names.
        </Text>
        
        <VStack spacing={6} align="stretch">
          {/* Discharge Note Models - Blue */}
          <Box 
            borderLeft="4px solid" 
            borderLeftColor="blue.500" 
            bg="blue.50" 
            p={4} 
            borderRadius="md"
          >
            <Heading as="h2" size="md" mb={4} color="blue.700">Discharge Note Models</Heading>
            
            <VStack spacing={4} align="stretch">
              <Box>
                <Heading as="h3" size="sm" mb={2}>Discharge Note Summary Model</Heading>
                <Text fontSize="sm" color="gray.600" mb={2}>Models containing keywords: &quot;note&quot;, &quot;summary&quot;</Text>
                <Select
                  value={selectedDischargeNoteSummaryModel}
                  onChange={(e) => setSelectedDischargeNoteSummaryModel(e.target.value)}
                  placeholder="Select discharge note summary model"
                  bg="white"
                >
                  {dischargeNoteSummaryModels.map((model) => (
                    <option key={model} value={model}>{model}</option>
                  ))}
                </Select>
                {dischargeNoteSummaryModels.length === 0 && (
                  <Text fontSize="sm" color="orange.500" mt={1}>
                    ⚠️ No models found with required keywords. Please ensure model names contain &quot;note&quot; and &quot;summary&quot;.
                  </Text>
                )}
              </Box>

              <Box>
                <Heading as="h3" size="sm" mb={2}>Discharge Note Validation Model</Heading>
                <Text fontSize="sm" color="gray.600" mb={2}>Models containing keywords: &quot;note&quot;, &quot;validation&quot;</Text>
                <Select
                  value={selectedDischargeNoteValidationModel}
                  onChange={(e) => setSelectedDischargeNoteValidationModel(e.target.value)}
                  placeholder="Select discharge note validation model"
                  bg="white"
                >
                  {dischargeNoteValidationModels.map((model) => (
                    <option key={model} value={model}>{model}</option>
                  ))}
                </Select>
                {dischargeNoteValidationModels.length === 0 && (
                  <Text fontSize="sm" color="orange.500" mt={1}>
                    ⚠️ No models found with required keywords. Please ensure model names contain &quot;note&quot; and &quot;validation&quot;.
                  </Text>
                )}
              </Box>
            </VStack>
          </Box>

          {/* Audio Transcription Models - Orange */}
          <Box 
            borderLeft="4px solid" 
            borderLeftColor="orange.500" 
            bg="orange.50" 
            p={4} 
            borderRadius="md"
          >
            <Heading as="h2" size="md" mb={4} color="orange.700">Audio Transcription Models</Heading>
            
            <Box>
              <Heading as="h3" size="sm" mb={2}>Audio Transcription Model</Heading>
              <Select
                value="google/gemma-3n-E4B-it"
                isDisabled={true}
                bg="gray.100"
                cursor="not-allowed"
              >
                <option value="google/gemma-3n-E4B-it">google/gemma-3n-E4B-it</option>
              </Select>
              <Text fontSize="sm" color="gray.500" mt={1}>
                This model is locked and cannot be changed.
              </Text>
            </Box>
          </Box>

          {/* Consultation Models - Green */}
          <Box 
            borderLeft="4px solid" 
            borderLeftColor="green.500" 
            bg="green.50" 
            p={4} 
            borderRadius="md"
          >
            <Heading as="h2" size="md" mb={4} color="green.700">Consultation Models</Heading>
            
            <VStack spacing={4} align="stretch">
              <Box>
                <Heading as="h3" size="sm" mb={2}>Consultation Summary Model</Heading>
                <Text fontSize="sm" color="gray.600" mb={2}>Models containing keywords: &quot;consult&quot;, &quot;summary&quot;</Text>
                <Select
                  value={selectedConsultationSummaryModel}
                  onChange={(e) => setSelectedConsultationSummaryModel(e.target.value)}
                  placeholder="Select consultation summary model"
                  bg="white"
                >
                  {consultationSummaryModels.map((model) => (
                    <option key={model} value={model}>{model}</option>
                  ))}
                </Select>
                {consultationSummaryModels.length === 0 && (
                  <Text fontSize="sm" color="orange.500" mt={1}>
                    ⚠️ No models found with required keywords. Please ensure model names contain &quot;consult&quot; and &quot;summary&quot;.
                  </Text>
                )}
              </Box>

              <Box>
                <Heading as="h3" size="sm" mb={2}>Consultation Validation Model</Heading>
                <Text fontSize="sm" color="gray.600" mb={2}>Models containing keywords: &quot;consult&quot;, &quot;validation&quot;</Text>
                <Select
                  value={selectedConsultationValidationModel}
                  onChange={(e) => setSelectedConsultationValidationModel(e.target.value)}
                  placeholder="Select consultation validation model"
                  bg="white"
                >
                  {consultationValidationModels.map((model) => (
                    <option key={model} value={model}>{model}</option>
                  ))}
                </Select>
                {consultationValidationModels.length === 0 && (
                  <Text fontSize="sm" color="orange.500" mt={1}>
                    ⚠️ No models found with required keywords. Please ensure model names contain &quot;consult&quot; and &quot;validation&quot;.
                  </Text>
                )}
              </Box>
            </VStack>
          </Box>

          {/* Submit Button */}
          <Button 
            colorScheme="blue" 
            size="lg"
            onClick={handleSubmit}
          >
            Update Model Configuration
          </Button>

          {/* Current Selection Status */}
          <Box bg="gray.50" p={4} borderRadius="md">
            <Heading as="h3" size="sm" mb={3}>Current Selection Status:</Heading>
            <VStack align="start" spacing={1}>
              <Text fontSize="sm">
                {selectedDischargeNoteSummaryModel ? '✅' : '❌'} 
                {' '}Discharge Note Summary: {selectedDischargeNoteSummaryModel || 'Not configured'}
              </Text>
              <Text fontSize="sm">
                {selectedDischargeNoteValidationModel ? '✅' : '❌'} 
                {' '}Discharge Note Validation: {selectedDischargeNoteValidationModel || 'Not configured'}
              </Text>
              <Text fontSize="sm">
                {selectedAudioTranscriptionModel ? '✅' : '❌'} 
                {' '}Audio Transcription: {selectedAudioTranscriptionModel || 'Not configured'}
              </Text>
              <Text fontSize="sm">
                {selectedConsultationSummaryModel ? '✅' : '❌'} 
                {' '}Consultation Summary: {selectedConsultationSummaryModel || 'Not configured'}
              </Text>
              <Text fontSize="sm">
                {selectedConsultationValidationModel ? '✅' : '❌'} 
                {' '}Consultation Validation: {selectedConsultationValidationModel || 'Not configured'}
              </Text>
            </VStack>
          </Box>
        </VStack>
      </Box>
    </OverlayComponent>
  );
}
