'use client'

/** @jsxImportSource react */
import React, { useState, useEffect, useRef } from 'react';
import { Box, Text, Textarea, Button, VStack, HStack, Heading, useToast, Select, Accordion, AccordionItem, AccordionButton, AccordionPanel, AccordionIcon, Tabs, TabList, TabPanels, Tab, TabPanel, Badge, Divider, Flex } from '@chakra-ui/react';
import { useRouter } from 'next/navigation';
import OverlayComponent from "@/components/Overlay";
import DiagnosisList, { Diagnosis } from '@/components/DiagnosisList';
import Head from 'next/head';
import { fetchWithAuth } from '@/utils/api';
import { convertWebMToWAV, getBestSupportedFormat } from '@/utils/audioConverter';
import AuthGuard  from '@/components/AuthGuard';
import AIResponseDisplay from '@/components/AIResponseDisplay';
import { normalizePatientCategory } from '@/utils/patientCategoryMapper';

// Helper function to convert diagnosis data to array format
const normalizeDiagnosis = (diagnosis: any): Diagnosis[] => {
  if (Array.isArray(diagnosis)) {
    return diagnosis;
  }
  if (typeof diagnosis === 'string' && diagnosis.trim()) {
    // Try to parse as JSON first
    try {
      const parsed = JSON.parse(diagnosis);
      if (Array.isArray(parsed)) {
        return parsed;
      }
    } catch (e) {
      // Not JSON, treat as string
    }
    // Convert old string format to array format
    return [{ category: 'Primary', diagnosis: diagnosis.trim() }];
  }
  return [];
};

// Helper function to parse AI response with thinking and answer tags
const parseAIResponse = (response: string): { thinking: string; answer: string; full: string } => {
  const thinkingMatch = response.match(/<thinking>([\s\S]*?)<\/thinking>/);
  const answerMatch = response.match(/<answer>([\s\S]*?)<\/answer>/);
  
  return {
    thinking: thinkingMatch ? thinkingMatch[1].trim() : '',
    answer: answerMatch ? answerMatch[1].trim() : response.trim(),
    full: response
  };
};

interface ResponseData {
  model: string;
  created_at: string;
  response: string;
  done: boolean;
}

const HighlightedText: React.FC<{ 
  text: string; 
  highlights: string[]; 
  fontSize?: string;
  fontWeight?: string;
  color?: string;
  fontFamily?: string;
}> = ({ text, highlights, fontSize, fontWeight, color, fontFamily }) => {
  console.log("Highlights:", highlights); // Debug information

  const escapeRegExp = (string: string) => {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  };

  const highlightText = () => {
    if (highlights.length === 0) return text;

    // Check if any highlight contains the current text as a substring
    let shouldHighlight = false;
    for (const highlight of highlights) {
      if (highlight.toLowerCase().includes(text.toLowerCase())) {
        shouldHighlight = true;
        break;
      }
    }

    if (shouldHighlight) {
      return `<mark style="background-color: yellow;">${text}</mark>`;
    }

    // Original regex matching
    const regex = new RegExp(`(${highlights.map(escapeRegExp).join('|')})`, 'gi');
    return text.replace(regex, '<mark style="background-color: yellow;">$1</mark>');
  };

  const style = {
    fontSize: fontSize || 'inherit',
    fontWeight: fontWeight || 'inherit',
    color: color || 'inherit',
    fontFamily: fontFamily || 'inherit',
    display: 'inline'
  };

  return (
    <span style={style} dangerouslySetInnerHTML={{ __html: highlightText().replace(/\n/g, '<br>') }} />
  );
};

export default function SummaryPage() {
  return (
    <AuthGuard>
      <SummaryPageContent />
    </AuthGuard>
  );
}

interface PatientInfo {
  id?: number;
  medical_record_no?: string;
  medicalRecordNo?: string;  // Keep for backward compatibility
  patient_category?: 'NHI General' | 'NHI Injury' | 'Self-Pay';
  patientCategory?: 'NHI General' | 'NHI Injury' | 'Self-Pay';  // Keep for backward compatibility
  name: string;
  gender: 'M' | 'F';
  weight: number;
  department: string;
  birthday: string;
  admission_time?: string;
  admissionTime?: string;  // Keep for backward compatibility
  bed_number?: string;
  bedNumber?: string;  // Keep for backward compatibility
  status: 'HOSPITALIZED' | 'DISCHARGED' | 'TRANSFERRED';
}

interface ConsultationRecord {
  id: number;
  patient_id?: number;
  doctor_name?: string;
  consultation_date?: string;  // from consultation_records table
  created_at?: string;  // from ai_inferences table
  department?: string;
  consultation_type?: string;
  original_content: string;
  ai_summary?: string;  // from consultation_records table
  ai_generated_result?: string;  // from ai_inferences table
  nurse_confirmation?: string;
  relevant_highlights?: any;  // from consultation_records table
  relevant_text?: any;  // from ai_inferences table
  status: string;
  created_by?: number;
  confirmed_by?: number;
  confirmed_at?: string;
}

function SummaryPageContent() {
  const [activeTab, setActiveTab] = useState(0); // Default to Discharge Note tab (index 0)
  const [originalContent, setOriginalContent] = useState("" as string);
  const [llamaResult, setLLamaResult] = useState("" as string);
  const aiSummaryBoxRef = useRef<HTMLDivElement>(null);
  const [nurseConfirmation, setNurseConfirmation] = useState("" as string);
  const [isLoading, setIsLoading] = useState(false as boolean);
  const [relevantText, setRelevantText] = useState<string[]>([]);
  const [isOriginalContentStatic, setIsOriginalContentStatic] = useState(false);
  const [consultationRecords, setConsultationRecords] = useState<ConsultationRecord[]>([]);
  const [isLoadingRecords, setIsLoadingRecords] = useState(false);
  const toast = useToast();
  const router = useRouter();
  const [activeModels, setActiveModels] = useState({
    consultationSummaryModel: '',
    consultationValidationModel: '',
    dischargeNoteSummaryModel: '',
    dischargeNoteValidationModel: '',
    audioModel: ''
  });

  // Patient data - will be loaded from localStorage or redirect to patient selection
  const [patientInfo, setPatientInfo] = useState<PatientInfo | null>(null);
  const [hasLoadedPatient, setHasLoadedPatient] = useState(false);
  
  // Nursing Note tab state
  const [recordTime, setRecordTime] = useState(new Date().toLocaleString());
  const [recordType, setRecordType] = useState('');
  const [speechToTextContent, setSpeechToTextContent] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [nursingNoteHistory, setNursingNoteHistory] = useState<any[]>([]);
  const [isSubmittingNote, setIsSubmittingNote] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const [audioChunks, setAudioChunks] = useState<Blob[]>([]);
  
  // Discharge Note tab state
  const [treatmentCourse, setTreatmentCourse] = useState('');
  const [isGeneratingTreatmentCourse, setIsGeneratingTreatmentCourse] = useState(false);
  const [dischargeNoteRelevantText, setDischargeNoteRelevantText] = useState<string[]>([]);
  const [isSubmittingDischargeNote, setIsSubmittingDischargeNote] = useState(false);
  const [isDischargeNoteLocked, setIsDischargeNoteLocked] = useState(false);
  
  // Discharge note data collection
  const [dischargeNoteData, setDischargeNoteData] = useState({
    chiefComplaint: '',
    diagnosis: [] as Diagnosis[],
    specialistConsultation: '',
    nursingNote: '',
    labReport: [] as any[],
    treatmentCourse: '',
    // Additional fields that might be needed
    dischargeInstructions: '',
    followUpPlan: '',
    medications: '',
    restrictions: ''
  });

  useEffect(() => {
    console.log("Relevant Text:", relevantText); // Debug info
  }, [relevantText]);

  // Load patient data from localStorage if available, otherwise redirect to patient selection
  useEffect(() => {
    if (hasLoadedPatient) return; // Prevent re-running if already loaded
    
    const savedPatient = localStorage.getItem('selectedPatient');
    if (savedPatient) {
      try {
        const patientData = JSON.parse(savedPatient);
        console.log('Loaded patient from localStorage:', patientData);
        
        // Normalize field names and validate data
        const sanitizedPatientData = {
          ...patientData,
          // Use either format for medical record number
          medicalRecordNo: patientData.medicalRecordNo || patientData.medical_record_no,
          medical_record_no: patientData.medical_record_no || patientData.medicalRecordNo,
          // Use either format for patient category and normalize
          patientCategory: normalizePatientCategory(patientData.patientCategory || patientData.patient_category),
          patient_category: normalizePatientCategory(patientData.patient_category || patientData.patientCategory),
          // Use either format for admission time
          admissionTime: patientData.admissionTime || patientData.admission_time,
          admission_time: patientData.admission_time || patientData.admissionTime,
          // Use either format for bed number
          bedNumber: patientData.bedNumber || patientData.bed_number,
          bed_number: patientData.bed_number || patientData.bedNumber,
          // Validate date fields
          birthday: patientData.birthday
        };
        
        console.log('Sanitized patient data:', sanitizedPatientData);
        console.log('Patient ID:', sanitizedPatientData.id);
        
        setPatientInfo(sanitizedPatientData);
        setHasLoadedPatient(true);
        // Keep patient data in localStorage for persistence across page refreshes
        
      } catch (error) {
        console.error('Error parsing patient data from localStorage:', error);
        // Redirect to patient selection if data is corrupted
        toast({
          title: "Error",
          description: "Failed to load patient data",
          status: "error",
          duration: 3000,
          isClosable: true,
        });
        router.push('/patients');
      }
    } else if (!hasLoadedPatient) {
      // No patient selected and we haven't loaded one yet, redirect to patient selection
      toast({
        title: "No Patient Selected",
        description: "Please select a patient first",
        status: "warning",
        duration: 3000,
        isClosable: true,
      });
      router.push('/patients');
    }
  }, [router, toast, hasLoadedPatient]);

  // Helper function to calculate age
  const calculateAge = (birthDate: string) => {
    if (!birthDate) {
      return 'Unknown age';
    }
    
    const birth = new Date(birthDate);
    
    // Check if the birth date is valid
    if (isNaN(birth.getTime())) {
      return 'Invalid birth date';
    }
    
    const today = new Date();
    
    let years = today.getFullYear() - birth.getFullYear();
    let months = today.getMonth() - birth.getMonth();
    let days = today.getDate() - birth.getDate();

    if (days < 0) {
      months--;
      const lastDayOfPrevMonth = new Date(today.getFullYear(), today.getMonth(), 0).getDate();
      days += lastDayOfPrevMonth;
    }

    if (months < 0) {
      years--;
      months += 12;
    }

    return `${years}y ${months}m ${days}d`;
  };

  // Helper function to format admission time
  const formatAdmissionTime = (dateTimeStr: string) => {
    if (!dateTimeStr) {
      return 'Not specified';
    }
    
    const date = new Date(dateTimeStr);
    
    // Check if the date is valid
    if (isNaN(date.getTime())) {
      return 'Invalid date';
    }
    
    try {
      const dateOnly = date.toISOString().split('T')[0];
      const timeOnly = date.toTimeString().split(' ')[0];
      return `${dateOnly} (${timeOnly})`;
    } catch (error) {
      console.error('Error formatting date:', error);
      return 'Date formatting error';
    }
  };

  // Helper function to get patient category color
  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'NHI General': return 'blue';
      case 'NHI Injury': return 'orange';
      case 'Self-Pay': return 'purple';
      default: return 'gray';
    }
  };

  // Helper function to get status color
  const getStatusColor = (status: string) => {
    return status === 'HOSPITALIZED' ? 'red' : 'green';
  };

  // Function to fetch consultation records from AI inference history for current patient
  const fetchConsultationRecords = async () => {
    // Don't fetch if no patient is selected
    if (!patientInfo?.id) {
      console.log('No patient selected - skipping consultation records fetch');
      setConsultationRecords([]);
      return;
    }
    
    setIsLoadingRecords(true);
    try {
      console.log('Fetching consultation records for patient:', patientInfo.id);
      
      const apiUrl = `/api/patients/${patientInfo.id}/consultations?limit=20`;
      console.log('Fetching consultation records from:', apiUrl);
      
      const response = await fetchWithAuth(apiUrl);
      if (!response.ok) {
        throw new Error('Failed to fetch consultation records');
      }
      const data = await response.json();
      console.log('Received consultation records:', data);
      setConsultationRecords(data.items || []);
    } catch (error) {
      console.error('Error fetching consultation records:', error);
      toast({
        title: "Warning",
        description: "Could not load consultation records",
        status: "warning",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setIsLoadingRecords(false);
    }
  };

  // Fetch nursing notes for the current patient
  const fetchNursingNotes = async () => {
    if (!patientInfo?.id) return;
    
    try {
      const response = await fetchWithAuth(`/api/patients/${patientInfo.id}/nursing-notes?limit=10`);
      if (response.ok) {
        const data = await response.json();
        const formattedNotes = data.items.map((note: any) => ({
          id: note.id,
          timestamp: note.record_time,
          type: note.record_type,
          content: note.content,
          nurse: `User ID: ${note.created_by}` // Could be enhanced with user name lookup
        }));
        setNursingNoteHistory(formattedNotes);
      }
    } catch (error) {
      console.error('Failed to fetch nursing notes:', error);
    }
  };

  // Fetch lab reports for the current patient
  const fetchLabReports = async () => {
    if (!patientInfo?.id) return;
    
    try {
      const response = await fetchWithAuth(`/api/patients/${patientInfo.id}/lab-reports?limit=20`);
      if (response.ok) {
        const data = await response.json();
        const formattedLabReports = data.items.map((report: any) => ({
          id: report.id,
          testName: report.test_name,
          testDate: report.test_date,
          resultValue: report.result_value,
          resultUnit: report.result_unit,
          normalRange: report.normal_range,
          flag: report.flag || 'NORMAL',
          labTechnician: report.lab_technician
        }));
        
        // Sort lab reports by date (latest first) and update discharge note data
        const sortedLabReports = formattedLabReports.sort((a: any, b: any) => {
          const dateA = new Date(a.testDate);
          const dateB = new Date(b.testDate);
          return dateB.getTime() - dateA.getTime(); // Latest first
        });
        
        setDischargeNoteData(prev => ({
          ...prev,
          labReport: sortedLabReports
        }));
        
        console.log('Fetched lab reports:', formattedLabReports);
      }
    } catch (error) {
      console.error('Failed to fetch lab reports:', error);
      toast({
        title: "Warning",
        description: "Could not load lab reports",
        status: "warning",
        duration: 3000,
        isClosable: true,
      });
    }
  };

  // Handle nursing note submission
  const handleSubmitNursingNote = async () => {
    if (!speechToTextContent.trim() || !recordType || !patientInfo?.id) {
      toast({
        title: "Error",
        description: "Please fill in all required fields and ensure a patient is selected",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    setIsSubmittingNote(true);
    try {
      const noteData = {
        patient_id: patientInfo.id,
        record_type: recordType,
        content: speechToTextContent,
        transcription_text: speechToTextContent, // Since this is speech-to-text content
        priority: 'medium' // Default priority
      };

      const response = await fetchWithAuth('/api/nursing-notes', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(noteData)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to submit nursing note');
      }

      const savedNote = await response.json();
      
      // Reset form
      setSpeechToTextContent('');
      setRecordType('');
      setRecordTime(new Date().toLocaleString());
      
      // Refresh nursing notes list
      fetchNursingNotes();
      
      // Also refresh discharge note nursing data
      fetchNursingNotesForDischarge();
      
      toast({
        title: "Success",
        description: "Nursing note submitted successfully",
        status: "success",
        duration: 3000,
        isClosable: true,
      });

    } catch (error) {
      console.error('Error submitting nursing note:', error);
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to submit nursing note",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setIsSubmittingNote(false);
    }
  };

  const handleStartRecording = async () => {
    try {
      // Request microphone permission
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      // Get the best supported format
      const bestFormat = getBestSupportedFormat();
      let mimeType = bestFormat.mimeType;
      let fileExtension = bestFormat.extension;
      
      console.log('Browser Audio Support Check:');
      console.log('  Best format:', mimeType);
      console.log('  Extension:', fileExtension);
      console.log('  Needs conversion:', fileExtension === 'webm' ? 'Yes (to WAV)' : 'No');
      
      // Create MediaRecorder with the best format
      const recorder = new MediaRecorder(stream, { mimeType });
      
      console.log('Audio Recording Format:');
      console.log('  MIME Type:', mimeType || 'default');
      console.log('  File Extension:', fileExtension);
      console.log('  Supported by Gemma API:', fileExtension === 'ogg' ? '✅ Yes' : '⚠️ Will be converted');
      
      // Store chunks in a local array to avoid closure issues
      const chunks: Blob[] = [];
      
      // Collect audio chunks
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunks.push(event.data);
        }
      };
      
      // Store file extension in closure
      const recordedFileExtension = fileExtension;
      
      // Handle recording stop
      recorder.onstop = async () => {
        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());
        
        // Create blob from chunks
        let audioBlob = new Blob(chunks, { type: mimeType || 'audio/webm' });
        let finalExtension = recordedFileExtension;
        
        console.log('Recording Complete:');
        console.log('  Original Size:', audioBlob.size, 'bytes');
        console.log('  Original Type:', audioBlob.type);
        console.log('  Original Extension:', recordedFileExtension);
        
        // Convert to WAV if needed (WebM not supported by Gemma)
        if (recordedFileExtension === 'webm') {
          try {
            console.log('Converting WebM to WAV in browser...');
            audioBlob = await convertWebMToWAV(audioBlob);
            finalExtension = 'wav';
            console.log('  Converted Size:', audioBlob.size, 'bytes');
            console.log('  Converted Type:', audioBlob.type);
          } catch (error) {
            console.error('WAV conversion failed:', error);
            console.log('Sending original WebM (backend will convert)');
          }
        }
        
        // Send to backend for transcription
        await sendAudioToBackend(audioBlob, finalExtension);
      };
      
      // Start recording
      recorder.start();
      setMediaRecorder(recorder);
      setIsRecording(true);
      
      toast({
        title: "Recording Started",
        description: "Speak clearly into your microphone",
        status: "info",
        duration: 2000,
        isClosable: true,
      });
      
    } catch (error) {
      console.error('Error starting recording:', error);
      toast({
        title: "Recording Error",
        description: "Failed to access microphone. Please check permissions.",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    }
  };

  const handleStopRecording = () => {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
      setIsRecording(false);
      
      toast({
        title: "Processing Audio",
        description: "Sending audio for transcription...",
        status: "info",
        duration: 2000,
        isClosable: true,
      });
    }
  };

  const sendAudioToBackend = async (audioBlob: Blob, fileExtension: string = 'webm') => {
    if (!patientInfo?.id) {
      toast({
        title: "Error",
        description: "Please select a patient first",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    try {
      console.log('Audio blob details:', {
        size: audioBlob.size,
        type: audioBlob.type,
        extension: fileExtension
      });
      
      // Create FormData for file upload
      const formData = new FormData();
      formData.append('audio_file', audioBlob, `recording.${fileExtension}`);
      formData.append('patient_id', patientInfo.id.toString());
      formData.append('record_type', recordType || 'NarrativeNote'); // Default to NarrativeNote if not selected
      formData.append('context', `Nursing note audio for patient ${patientInfo.name}, recorded at ${recordTime}`);

      // Send to backend
      const response = await fetchWithAuth('/api/audio/transcribe', {
        method: 'POST',
        headers: {
          // Remove Content-Type header to let browser set it with boundary
        },
        body: formData
      });

      if (!response.ok) {
        throw new Error('Failed to transcribe audio');
      }

      const result = await response.json();
      
      // Update the text content with transcription
      setSpeechToTextContent(result.transcription);
      
      toast({
        title: "Transcription Complete",
        description: "Audio has been transcribed successfully. You can now edit and submit.",
        status: "success",
        duration: 3000,
        isClosable: true,
      });
      
    } catch (error) {
      console.error('Error sending audio to backend:', error);
      toast({
        title: "Transcription Error",
        description: "Failed to transcribe audio. Please try again.",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    }
  };


  // Collect discharge note data from patient info and form fields
  const collectDischargeNoteData = () => {
    const collectedData = {
      // Patient information
      patientId: patientInfo?.id || null,
      patientName: patientInfo?.name || '',
      medicalRecordNo: patientInfo?.medicalRecordNo || patientInfo?.medical_record_no || '',
      
      // Core discharge note components
      chiefComplaint: dischargeNoteData.chiefComplaint || '',
      diagnosis: normalizeDiagnosis(dischargeNoteData.diagnosis) || [],
      specialistConsultation: dischargeNoteData.specialistConsultation || '',
      nursingNote: dischargeNoteData.nursingNote || '',
      labReport: dischargeNoteData.labReport || [],
      treatmentCourse: treatmentCourse || '',
      
      // Additional discharge information
      dischargeInstructions: dischargeNoteData.dischargeInstructions || '',
      followUpPlan: dischargeNoteData.followUpPlan || '',
      medications: dischargeNoteData.medications || '',
      restrictions: dischargeNoteData.restrictions || ''
    };

    console.log('Collected discharge note data:', collectedData);
    return collectedData;
  };

  // Handle treatment course generation using AI - Simplified approach
  const handleGenerateTreatmentCourse = async () => {
    if (!patientInfo?.id) {
      toast({
        title: "Error",
        description: "Please select a patient first",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    setIsGeneratingTreatmentCourse(true);
    setTreatmentCourse('');
    let accumulatedResult = "";
    let accumulatedJson = "";

    try {
      console.log('Generating discharge summary for patient:', patientInfo.id);

      // Simplified API call - just send patient_id, backend handles data stitching
      const response = await fetchWithAuth('/gen-discharge-summary', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          patient_id: patientInfo.id
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API request failed: ${response.status} ${response.statusText}. Error details: ${errorText}`);
      }
      
      const reader = response.body?.getReader();
      if (!reader) throw new Error('Failed to get reader from response');

      // Handle streaming response (same as consultation)
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = new TextDecoder().decode(value);
        console.log(chunk);
        accumulatedJson += chunk;

        try {
          const lastNewlineIndex = accumulatedJson.lastIndexOf('\n');
          if (lastNewlineIndex !== -1) {
            const completeJson = accumulatedJson.substring(0, lastNewlineIndex);
            const lines = completeJson.split('\n').filter(line => line.trim() !== '');

            for (const line of lines) {
              const data = JSON.parse(line);
              accumulatedResult += data.response;
              setTreatmentCourse(accumulatedResult.replace(/\\n/g, '\n'));
              if (data.done) break;
            }

            accumulatedJson = accumulatedJson.substring(lastNewlineIndex + 1);
          }
        } catch (jsonError) {
          // JSON incomplete, continue accumulating
        }
      }

      if (accumulatedJson.trim() !== '') {
        try {
          const data = JSON.parse(accumulatedJson);
          accumulatedResult += data.response;
          setTreatmentCourse(accumulatedResult.replace(/\\n/g, '\n'));
        } catch (jsonError) {
          console.error('Final JSON parse error:', jsonError);
        }
      }

      const finalResult = accumulatedResult.replace(/\\n/g, '\n');
      setTreatmentCourse(finalResult);

      toast({
        title: "Treatment Course Generated",
        description: "AI-generated treatment course is ready for review",
        status: "success",
        duration: 3000,
        isClosable: true,
      });

      // Automatically validate after generation
      if (activeModels.dischargeNoteValidationModel && finalResult.trim()) {
        try {
          console.log('Auto-validating discharge note for patient:', patientInfo.id);

          const validationResponse = await fetchWithAuth('/gen-discharge-validation', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              patient_id: patientInfo.id,
              treatment_course: finalResult
            })
          });

          if (validationResponse.ok) {
            const validationData = await validationResponse.json();
            setDischargeNoteRelevantText(validationData.relevant_text || []);
            console.log('Auto-validation completed successfully');
          }
        } catch (validationError) {
          console.error('Auto-validation failed:', validationError);
          // Don't show error toast for auto-validation failure
        }
      }

    } catch (error) {
      console.error('Error generating treatment course:', error);
      setTreatmentCourse('Error generating treatment course. Please try again.');
      
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to generate treatment course",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setIsGeneratingTreatmentCourse(false);
    }
  };

  // Handle discharge note validation (similar to consultation validation)
  const handleValidateDischargeNote = async () => {
    if (!treatmentCourse.trim()) {
      toast({
        title: "Error",
        description: "Please generate treatment course first",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    if (!patientInfo?.id) {
      toast({
        title: "Error",
        description: "Please select a patient first",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    try {
      console.log('Validating discharge note for patient:', patientInfo.id);

      // Simplified API call - just send patient_id and treatment_course
      const response = await fetchWithAuth('/gen-discharge-validation', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          patient_id: patientInfo.id,
          treatment_course: treatmentCourse
        })
      });

      if (!response.ok) {
        throw new Error('Failed to validate discharge note');
      }

      const validationData = await response.json();
      setDischargeNoteRelevantText(validationData.relevant_text || []);

      toast({
        title: "Validation Complete",
        description: "Discharge note validated and highlighting applied",
        status: "success",
        duration: 3000,
        isClosable: true,
      });

    } catch (error) {
      console.error('Error validating discharge note:', error);
      toast({
        title: "Error",
        description: "Failed to validate discharge note",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    }
  };

  // Handle final discharge note submission
  const handleSubmitDischargeNote = async () => {
    if (!treatmentCourse.trim() || !patientInfo?.id) {
      toast({
        title: "Error",
        description: "Please generate treatment course and ensure a patient is selected",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    setIsSubmittingDischargeNote(true);
    
    try {
      // Collect discharge note data
      const collectedData = collectDischargeNoteData();
      
      // Prepare submission data for discharge notes table
      const submissionData = {
        chiefComplaint: collectedData.chiefComplaint,
        diagnosis: collectedData.diagnosis,
        treatmentCourse: treatmentCourse,
        dischargeInstructions: collectedData.dischargeInstructions,
        followUpPlan: collectedData.followUpPlan,
        medications: collectedData.medications,
        restrictions: collectedData.restrictions
      };

      console.log('Submitting discharge note:', submissionData);

      const response = await fetchWithAuth(`/api/discharge-notes/${patientInfo.id}/submit-final`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(submissionData)
      });

      if (!response.ok) {
        // Don't try to read body again, it might have been consumed by fetchWithAuth
        throw new Error('Failed to submit discharge note');
      }

      toast({
        title: "Success",
        description: "Discharge note finalized and locked. Data has been saved to the database.",
        status: "success",
        duration: 5000,
        isClosable: true,
      });

      // Lock the discharge note interface
      setIsDischargeNoteLocked(true);
      
      // Note: We don't reset the form after submission since the data is now locked in place
      // The discharge note remains visible but in read-only state

    } catch (error) {
      console.error('Error submitting discharge note:', error);
      // Don't show another toast if it's a demo mode error (already shown by fetchWithAuth)
      if (!(error instanceof Error && error.message === 'Demo mode restriction')) {
        toast({
          title: "Error",
          description: error instanceof Error ? error.message : "Failed to submit discharge note",
          status: "error",
          duration: 3000,
          isClosable: true,
        });
      }
    } finally {
      setIsSubmittingDischargeNote(false);
    }
  };

  useEffect(() => {
    const fetchActiveModels = async () => {
      try {
        const response = await fetchWithAuth('/api/active-models');
        if (!response.ok) {
          throw new Error('Cannot get current model settings');
        }
        const data = await response.json();
        setActiveModels(data);
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
    
    // Don't fetch consultation records on mount - wait for patient to be loaded
    // fetchConsultationRecords();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-scroll AI Summary box when content updates
  useEffect(() => {
    if (!aiSummaryBoxRef.current) return;
    
    const scrollToBottom = () => {
      if (aiSummaryBoxRef.current) {
        aiSummaryBoxRef.current.scrollTop = aiSummaryBoxRef.current.scrollHeight;
      }
    };
    
    // Scroll when content changes
    scrollToBottom();
    
    // Also observe DOM mutations for more reliable scrolling
    const observer = new MutationObserver(() => {
      scrollToBottom();
    });
    
    observer.observe(aiSummaryBoxRef.current, {
      childList: true,
      subtree: true,
      characterData: true
    });
    
    return () => {
      observer.disconnect();
    };
  }, [llamaResult]);

  // Fetch nursing notes and lab reports when component mounts or patient changes
  useEffect(() => {
    fetchNursingNotes();
    fetchLabReports();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patientInfo?.id]);


  // Fetch and populate consultation records for discharge note
  const fetchConsultationRecordsForDischarge = async () => {
    if (!patientInfo?.id) return;
    
    try {
      const response = await fetchWithAuth(`/api/patients/${patientInfo.id}/consultations?limit=5`);
      if (response.ok) {
        const data = await response.json();
        const consultationSummary = data.items.map((consultation: any) => 
          `[${consultation.consultation_date}]\n${consultation.nurse_confirmation || consultation.original_content}`
        ).join('\n\n');
        
        setDischargeNoteData(prev => ({
          ...prev,
          specialistConsultation: consultationSummary
        }));
      }
    } catch (error) {
      console.error('Failed to fetch consultations for discharge note:', error);
    }
  };

  // Fetch and populate nursing notes for discharge note
  const fetchNursingNotesForDischarge = async () => {
    if (!patientInfo?.id) return;
    
    try {
      const response = await fetchWithAuth(`/api/patients/${patientInfo.id}/nursing-notes?limit=10`);
      if (response.ok) {
        const data = await response.json();
        const nursingNotesSummary = data.items.map((note: any) => 
          `[${note.record_time}]\n${note.record_type}: ${note.content}`
        ).join('\n\n');
        
        setDischargeNoteData(prev => ({
          ...prev,
          nursingNote: nursingNotesSummary
        }));
      }
    } catch (error) {
      console.error('Failed to fetch nursing notes for discharge note:', error);
    }
  };

  // Fetch discharge note data for this patient
  const fetchDischargeNoteData = async () => {
    if (!patientInfo?.id) return;
    
    try {
      const response = await fetchWithAuth(`/api/patients/${patientInfo.id}/discharge-note`);
      if (response.ok) {
        const dischargeNote = await response.json();
        setDischargeNoteData(prev => ({
          ...prev,
          chiefComplaint: dischargeNote.chief_complaint || '',
          diagnosis: normalizeDiagnosis(dischargeNote.diagnosis) || prev.diagnosis
        }));
        
        // Also set the treatment course if it exists
        if (dischargeNote.treatment_course) {
          setTreatmentCourse(dischargeNote.treatment_course);
        }
      }
    } catch (error) {
      console.error('Failed to fetch discharge note data:', error);
      // If no discharge note exists yet, that's okay - fields will remain empty
    }
  };

  // Update discharge note data when patient info changes
  useEffect(() => {
    if (patientInfo) {
      // Fetch discharge note data instead of using patient data
      fetchDischargeNoteData();
      
      // Fetch additional data for discharge note
      fetchConsultationRecordsForDischarge();
      fetchNursingNotesForDischarge();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patientInfo]);

  // Fetch consultation records when patient changes
  useEffect(() => {
    if (patientInfo?.id) {
      fetchConsultationRecords();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patientInfo?.id]);

  // Reload discharge note data when switching to discharge note tab
  useEffect(() => {
    if (activeTab === 0 && patientInfo?.id) {
      // Tab index 0 is the Discharge Note tab
      fetchDischargeNoteData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, patientInfo?.id]);

  const handleOriginalContentChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setOriginalContent(e.target.value);
  };

  const handleNurseConfirmationChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setNurseConfirmation(e.target.value);
  };

  const handleSubmitOriginalContent = async () => {
    // Validate content is not empty
    if (!originalContent.trim()) {
      toast({
        title: "Error",
        description: "Please enter consultation content before generating summary",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      return;
    }
    
    setIsLoading(true);
    setLLamaResult("");
    let accumulatedResult = "";
    let accumulatedJson = "";

    try {
      const response = await fetchWithAuth('/gen-summary', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          content: originalContent
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API request failed: ${response.status} ${response.statusText}. Error details: ${errorText}`);
      }
      
      const reader = response.body?.getReader();
      if (!reader) throw new Error('Failed to get reader from response');

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = new TextDecoder().decode(value);
        console.log(chunk);
        accumulatedJson += chunk;

        try {
          const lastNewlineIndex = accumulatedJson.lastIndexOf('\n');
          if (lastNewlineIndex !== -1) {
            const completeJson = accumulatedJson.substring(0, lastNewlineIndex);
            const lines = completeJson.split('\n').filter(line => line.trim() !== '');

            for (const line of lines) {
              const data: ResponseData = JSON.parse(line);
              accumulatedResult += data.response;
              const currentResult = accumulatedResult.replace(/\\n/g, '\n');
              setLLamaResult(currentResult);
              
              // Don't update nurse confirmation during streaming - wait until complete
              
              if (data.done) break;
            }

            accumulatedJson = accumulatedJson.substring(lastNewlineIndex + 1);
          }
        } catch (jsonError) {
          // JSON incomplete, continue accumulating
        }
      }

      if (accumulatedJson.trim() !== '') {
        try {
          const data: ResponseData = JSON.parse(accumulatedJson);
          accumulatedResult += data.response;
          setLLamaResult(accumulatedResult.replace(/\\n/g, '\n'));
        } catch (jsonError) {
          console.error('Final JSON parse error:', jsonError);
        }
      }

      const finalResult = accumulatedResult.replace(/\\n/g, '\n');
      setLLamaResult(finalResult);
      
      // Parse the AI response to extract answer content for nurse confirmation
      const parsedResponse = parseAIResponse(finalResult);
      setNurseConfirmation(parsedResponse.answer);

      // Second API call to localhost:8000
      try {
        const response = await fetchWithAuth('/gen-validation', {
          method: 'POST',
          body: JSON.stringify({
            original: originalContent,
            summary: finalResult,
            user_id: 1
          }),
        });
        
        if (!response.ok) {
          throw new Error(`Failed to get relevant text: ${response.status}`);
        }

        const relevantTextData = await response.json();
        setRelevantText(relevantTextData.relevant_text);
        console.log(relevantTextData.relevant_text);
      } catch (error) {
        console.error('Error fetching relevant text:', error);
        toast({
          title: "Warning",
          description: "Cannot get relevant text. Highlighting may not work.",
          status: "warning",
          duration: 5000,
          isClosable: true,
          position: "top",
        });
        // Optionally, set relevantText to an empty array or handle the error as needed
        setRelevantText([]);
      }

      setIsOriginalContentStatic(true);

    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to generate summary",
        status: "error",
        duration: 3000,
        isClosable: true,
        position: "top",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmitNurseConfirmation = async () => {
    if (!nurseConfirmation || !originalContent || !llamaResult) {
      toast({
        title: "Error",
        description: "Please ensure all required fields are filled",
        status: "error",
        duration: 3000,
        isClosable: true,
        position: "top",
      });
      return;
    }

    try {
      const requestData = {
        user_id: 1,  // or other appropriate user ID
        patient_id: patientInfo?.id || null,  // Include current patient ID
        original_content: originalContent,
        nurse_confirmation: nurseConfirmation,
        ai_generated_result: llamaResult,
        relevant_text: relevantText || []  // Ensure it's not undefined
      };

      console.log('Sending data:', requestData); // For debugging

      const response = await fetchWithAuth('/api/submit-confirmation', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
      });
      
      if (!response.ok) {
        // Don't try to read body again, it might have been consumed by fetchWithAuth
        throw new Error('API request failed');
      }
      
      toast({
        title: "Success",
        description: "Nurse confirmation submitted successfully",
        status: "success",
        duration: 3000,
        isClosable: true,
        position: "top",
      });
      
      // Refresh consultation records after successful submission
      fetchConsultationRecords();
      // Also refresh discharge note data to reflect new consultation
      fetchConsultationRecordsForDischarge();
      fetchNursingNotesForDischarge();
    } catch (error) {
      console.error('Error submitting confirmation:', error);
      // Don't show another toast if it's a demo mode error (already shown by fetchWithAuth)
      if (error instanceof Error && error.message === 'Demo mode restriction') {
        return;
      }
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Nurse confirmation submission failed",
        status: "error",
        duration: 3000,
        isClosable: true,
        position: "top",
      });
    }
  };

  const handleResetOriginalContent = () => {
    setIsOriginalContentStatic(false);
    setRelevantText([]);
    setLLamaResult("");
    setNurseConfirmation("");
  };

  const renderPatientInfoHeader = () => {
    if (!patientInfo) {
      return (
        <Box 
          borderWidth={2} 
          borderRadius="md" 
          p={3} 
          backgroundColor="orange.50" 
          mb={3}
          borderColor="orange.200"
          textAlign="center"
        >
          <Text fontSize="sm" color="orange.700">
            No patient selected. Please select a patient from the patient list.
          </Text>
        </Box>
      );
    }
    
    return (
    <Box 
      borderWidth={2} 
      borderRadius="md" 
      p={3} 
      backgroundColor="gray.50" 
      mb={3}
      borderColor="blue.200"
    >
      <HStack spacing={3} wrap="wrap" justify="space-between" align="center">
        {/* Medical Record No. */}
        <Box>
          <Text fontSize="xs" color="gray.600">Medical Record No.</Text>
          <Text fontWeight="medium" fontSize="sm" backgroundColor="blue.100" px={2} py={1} borderRadius="md">
            {patientInfo?.medicalRecordNo || patientInfo?.medical_record_no || 'N/A'}
          </Text>
        </Box>

        {/* Patient Category */}
        <Box>
          <Text fontSize="xs" color="gray.600">Patient Category</Text>
          <Badge colorScheme={getCategoryColor(patientInfo?.patientCategory || patientInfo?.patient_category || '')} size="sm">
            {patientInfo?.patientCategory || patientInfo?.patient_category || 'N/A'}
          </Badge>
        </Box>

        {/* Patient Info */}
        <Box>
          <Text fontSize="xs" color="gray.600">Patient Info</Text>
          <Text fontWeight="medium" fontSize="sm">
            {patientInfo?.name || 'N/A'}({patientInfo?.gender || 'N/A'}) {patientInfo?.weight || 'N/A'}kg
          </Text>
        </Box>

        {/* Department */}
        <Box>
          <Text fontSize="xs" color="gray.600">Department</Text>
          <Text fontWeight="medium" fontSize="sm">{patientInfo?.department || 'N/A'}</Text>
        </Box>

        {/* Birthday */}
        <Box>
          <Text fontSize="xs" color="gray.600">Birthday</Text>
          <Text fontWeight="medium" fontSize="sm">
            {patientInfo?.birthday ? `${patientInfo.birthday} (${calculateAge(patientInfo.birthday)})` : 'N/A'}
          </Text>
        </Box>

        {/* Admission Time */}
        <Box>
          <Text fontSize="xs" color="gray.600">Admission Time</Text>
          <Text fontWeight="medium" fontSize="sm">{formatAdmissionTime(patientInfo?.admissionTime || patientInfo?.admission_time || '')}</Text>
        </Box>

        {/* Bed Number */}
        <Box>
          <Text fontSize="xs" color="gray.600">Bed Number</Text>
          <Text fontWeight="medium" fontSize="sm">{patientInfo?.bedNumber || patientInfo?.bed_number || 'N/A'}</Text>
        </Box>

        {/* Status */}
        <Box>
          <Text fontSize="xs" color="gray.600">Status</Text>
          <Badge colorScheme={getStatusColor(patientInfo?.status || '')} size="sm">
            {patientInfo?.status || 'N/A'}
          </Badge>
        </Box>
      </HStack>
    </Box>
    );
  };

  const renderConsultationTab = () => (
    <HStack spacing={4} align="stretch" height="100vh">
      {/* Column 1: Consultation Records */}
      <Box
        width="25%"
        borderWidth={1}
        borderRadius="md"
        p={3}
        backgroundColor="white"
        overflowY="auto"
      >
        <VStack spacing={2} align="stretch">
          <HStack justify="space-between" align="center">
            <VStack align="start" spacing={0}>
              <Heading as="h3" size="sm">Consultation Records</Heading>
              {patientInfo?.id ? (
                <Text fontSize="xs" color="gray.500">
                  For: {patientInfo.name} ({patientInfo.medicalRecordNo || patientInfo.medical_record_no})
                </Text>
              ) : (
                <Text fontSize="xs" color="orange.500">
                  No patient selected - showing all records
                </Text>
              )}
            </VStack>
            <Button
              size="sm"
              colorScheme="gray"
              variant="outline"
              onClick={fetchConsultationRecords}
              isLoading={isLoadingRecords}
              aria-label="Refresh consultation records"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M23 4v6h-6M1 20v-6h6" />
                <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
              </svg>
            </Button>
          </HStack>
          <Button
            size="sm"
            colorScheme="blue"
            variant="solid"
            onClick={() => {
              // Clear the form for new consultation
              setOriginalContent('');
              setLLamaResult('');
              setNurseConfirmation('');
              setRelevantText([]);
              setIsOriginalContentStatic(false);
            }}
            width="100%"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '8px' }}>
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            New Consultation
          </Button>
        </VStack>
        <Box mb={3} />
        <VStack spacing={2} align="stretch">
          {isLoadingRecords ? (
            <Box textAlign="center" py={4}>
              <Text color="gray.500" fontSize="sm">Loading consultation records...</Text>
            </Box>
          ) : consultationRecords.length > 0 ? (
            consultationRecords.map((record, index) => (
              <Box
                key={record.id || index}
                borderWidth={1}
                borderRadius="md"
                p={3}
                backgroundColor="gray.50"
                _hover={{ backgroundColor: "gray.100" }}
                cursor="pointer"
                onClick={() => {
                  // Load this record into the form
                  setOriginalContent(record.original_content || '');
                  // Handle both AI inference and consultation record field names
                  const aiResult = record.ai_summary || record.ai_generated_result || '';
                  setLLamaResult(aiResult);
                  
                  // If nurse confirmation exists, use it; otherwise parse from AI result
                  if (record.nurse_confirmation) {
                    setNurseConfirmation(record.nurse_confirmation);
                  } else {
                    const parsedResponse = parseAIResponse(aiResult);
                    setNurseConfirmation(parsedResponse.answer);
                  }
                  
                  setRelevantText(record.relevant_highlights?.relevant_highlights || record.relevant_text?.relevant_highlights || []);
                  setIsOriginalContentStatic(true);
                }}
              >
                <VStack align="start" spacing={1}>
                  <HStack justify="space-between" width="100%">
                    <Text fontSize="xs" color="gray.600" fontWeight="medium">
                      {new Date(record.consultation_date || record.created_at || '').toLocaleDateString()} {new Date(record.consultation_date || record.created_at || '').toLocaleTimeString()}
                    </Text>
                    <Badge
                      colorScheme={record.status === 'confirmed' ? 'green' : record.status === 'completed' ? 'blue' : 'gray'}
                      size="sm"
                    >
                      {record.status}
                    </Badge>
                  </HStack>
                  <Text fontSize="sm" color="gray.700" noOfLines={2}>
                    {record.original_content?.substring(0, 100)}...
                  </Text>
                  {record.nurse_confirmation && (
                    <Text fontSize="xs" color="blue.600" fontWeight="medium">
                      ✓ Nurse Confirmed
                    </Text>
                  )}
                </VStack>
              </Box>
            ))
          ) : (
            <Box textAlign="center" py={8}>
              <Text color="gray.500" fontSize="sm">
                No consultation records found
              </Text>
              <Text color="gray.400" fontSize="xs">
                Submit a consultation to see records here
              </Text>
            </Box>
          )}
        </VStack>
      </Box>

      {/* Column 2: Original Content and Nurse Confirmation Content */}
      <Box
        width="40%"
        borderWidth={1}
        borderRadius="md"
        p={3}
        backgroundColor="white"
        overflowY="auto"
      >
        <VStack spacing={3} align="stretch" height="100%">
          {/* Original Content Section */}
          <Box flex="1">
            <Heading as="h3" size="sm" mb={2}>Original Content</Heading>
            {isOriginalContentStatic ? (
              <>
                <Box
                  borderWidth={1}
                  borderRadius="md"
                  p={3}
                  minHeight="250px"
                  maxHeight="300px"
                  overflowY="auto"
                  backgroundColor="gray.50"
                  fontSize="sm"
                >
                  <HighlightedText text={originalContent} highlights={relevantText} />
                </Box>
                <Button
                  mt={2}
                  size="sm"
                  colorScheme="gray"
                  onClick={handleResetOriginalContent}
                >
                  Re-enter
                </Button>
              </>
            ) : (
              <>
                <Textarea
                  value={originalContent}
                  onChange={handleOriginalContentChange}
                  minHeight="250px"
                  backgroundColor="white"
                  fontSize="sm"
                  placeholder="Enter original consultation content here..."
                />
                <Box display="flex" alignItems="center" gap={2}>
                  <Button
                    mt={2}
                    size="sm"
                    colorScheme="blue"
                    onClick={handleSubmitOriginalContent}
                    isLoading={isLoading}
                    isDisabled={!originalContent.trim() || !activeModels.consultationSummaryModel || !activeModels.consultationValidationModel}
                  >
                    Generate Summary
                  </Button>
                  {(!activeModels.consultationSummaryModel || !activeModels.consultationValidationModel) && (
                    <Text color="red.500" fontSize="xs" mt={2}>
                      Model settings not configured
                    </Text>
                  )}
                </Box>
              </>
            )}
          </Box>

          <Divider />

          {/* Nurse Confirmation Content Section */}
          <Box flex="1">
            <Heading as="h3" size="sm" mb={2}>Nurse Confirmation Content</Heading>
            <Textarea
              value={nurseConfirmation}
              onChange={handleNurseConfirmationChange}
              minHeight="200px"
              backgroundColor="white"
              fontSize="sm"
              placeholder="Review and edit the AI-generated summary here..."
            />
            <Button
              mt={2}
              size="sm"
              colorScheme="green"
              onClick={handleSubmitNurseConfirmation}
            >
              Confirm & Submit
            </Button>
          </Box>
        </VStack>
      </Box>

      {/* Column 3: AI Summary Result */}
      <Box
        width="35%"
        borderWidth={1}
        borderRadius="md"
        p={3}
        backgroundColor="white"
        display="flex"
        flexDirection="column"
      >
        <Heading as="h3" size="sm" mb={3} flexShrink={0}>AI Summary Result</Heading>
        <Box
          ref={aiSummaryBoxRef}
          borderWidth={1}
          borderRadius="md"
          p={3}
          backgroundColor="gray.50"
          fontSize="sm"
          overflowY="auto"
          flex="1"
          minHeight="0"
          css={{
            '&::-webkit-scrollbar': {
              width: '6px',
            },
            '&::-webkit-scrollbar-track': {
              background: '#f1f1f1',
              borderRadius: '10px',
            },
            '&::-webkit-scrollbar-thumb': {
              background: '#c1c1c1',
              borderRadius: '10px',
            },
            '&::-webkit-scrollbar-thumb:hover': {
              background: '#a8a8a8',
            },
          }}
        >
          {llamaResult ? (
            <AIResponseDisplay response={llamaResult} />
          ) : (
            <Text color="gray.500" fontStyle="italic">
              AI summary will appear here after processing original content...
            </Text>
          )}
        </Box>

        {/* Model Information */}
        <Box mt={3} p={2} backgroundColor="blue.50" borderRadius="md" flexShrink={0} overflow="hidden">
          <Text fontSize="xs" fontWeight="medium" mb={1}>Current AI Models:</Text>
          <Text fontSize="xs" color="gray.600" noOfLines={1} wordBreak="break-word">
            Summary: {activeModels.consultationSummaryModel || 'Not configured'}
          </Text>
          <Text fontSize="xs" color="gray.600" noOfLines={1} wordBreak="break-word">
            Validation: {activeModels.consultationValidationModel || 'Not configured'}
          </Text>
        </Box>
      </Box>
    </HStack>
  );

  const renderDischargeNoteTab = () => {
    return (
      <HStack spacing={4} align="stretch" height="100vh">
        {/* Column 1: Chief Complaint and Lab Report */}
        <VStack width="33%" spacing={4} align="stretch">
            {/* Chief Complaint Block */}
            <Box
              borderWidth={1}
              borderRadius="lg"
              p={4}
              backgroundColor="white"
              borderColor="gray.300"
            >
              <Heading as="h3" size="sm" mb={2}>
                Chief Complaint
              </Heading>
              <Box
                p={3}
                backgroundColor="gray.50"
                borderRadius="md"
                minHeight="100px"
                fontSize="sm"
              >
                {dischargeNoteRelevantText.length > 0 && dischargeNoteData.chiefComplaint ? (
                  <HighlightedText text={dischargeNoteData.chiefComplaint} highlights={dischargeNoteRelevantText} />
                ) : (
                  <Text color={dischargeNoteData.chiefComplaint ? "gray.800" : "gray.500"} whiteSpace="pre-wrap">
                    {dischargeNoteData.chiefComplaint || "Chief complaint will be loaded from patient data..."}
                  </Text>
                )}
              </Box>
            </Box>

            {/* Lab Report Block */}
            <Box 
              borderWidth={1}
              borderRadius="lg" 
              p={4} 
              backgroundColor="white"
              borderColor="gray.300"
              flex="1"
              display="flex"
              flexDirection="column"
              overflow="hidden"
            >
              <Heading as="h3" size="sm" mb={2}>
                Lab Report
              </Heading>
              <Box 
                flex="1" 
                overflowY="auto" 
                backgroundColor="gray.50"
                borderRadius="md"
                p={2}
                minHeight={0}
                css={{
                  '&::-webkit-scrollbar': {
                    width: '6px',
                  },
                  '&::-webkit-scrollbar-track': {
                    background: '#f1f1f1',
                    borderRadius: '10px',
                  },
                  '&::-webkit-scrollbar-thumb': {
                    background: '#c1c1c1',
                    borderRadius: '10px',
                  },
                  '&::-webkit-scrollbar-thumb:hover': {
                    background: '#a8a8a8',
                  },
                }}
              >
                <VStack spacing={1} align="stretch" minHeight="100%">
                  {dischargeNoteData.labReport.length > 0 ? dischargeNoteData.labReport.map((lab, index) => {
                    const getStatusColors = (flag: string) => {
                      if (flag === 'HIGH') return { cardBg: 'orange.50', borderColor: 'orange.300', text: 'orange.800', valueColor: 'orange.600' };
                      if (flag === 'LOW') return { cardBg: 'blue.50', borderColor: 'blue.300', text: 'blue.800', valueColor: 'blue.600' };
                      return { cardBg: 'green.50', borderColor: 'green.300', text: 'green.800', valueColor: 'green.600' };
                    };

                    const statusColors = getStatusColors(lab.flag);
                    const value = lab.resultValue;
                    const unit = lab.resultUnit || '';
                    console.log('Lab result:', lab.testName, 'resultValue:', lab.resultValue, 'resultUnit:', lab.resultUnit);
                    const displayStatus = lab.flag === 'NORMAL' ? 'NORM' : lab.flag;
                    
                    // Check if this is a new date compared to previous lab
                    const currentDate = new Date(lab.testDate).toDateString();
                    const previousDate = index > 0 ? new Date(dischargeNoteData.labReport[index - 1].testDate).toDateString() : null;
                    const isNewDate = currentDate !== previousDate;

                    return (
                      <Box key={index}>
                        {/* Date Separator */}
                        {isNewDate && (
                          <Text 
                            fontSize="xs" 
                            fontWeight="bold" 
                            color="blue.600" 
                            bg="blue.50" 
                            px={2} 
                            py={1} 
                            borderRadius="md" 
                            mb={1}
                            textAlign="center"
                          >
                            {new Date(lab.testDate).toLocaleDateString('en-US', { 
                              weekday: 'short', 
                              year: 'numeric', 
                              month: 'short', 
                              day: 'numeric' 
                            })}
                          </Text>
                        )}
                        
                        <Box 
                          bg={statusColors.cardBg}
                          borderWidth={1}
                          borderColor={statusColors.borderColor}
                          borderRadius="md"
                          p={2}
                        >
                        {/* Header Row - Test Name and Date/Time */}
                        <HStack justify="space-between" align="center" mb={2}>
                          {dischargeNoteRelevantText.length > 0 ? (
                            <Box flex={1}>
                              <HighlightedText 
                                text={lab.testName} 
                                highlights={dischargeNoteRelevantText} 
                                fontSize="xs"
                                fontWeight="bold"
                                color="gray.700"
                              />
                            </Box>
                          ) : (
                            <Text fontSize="xs" fontWeight="bold" color="gray.700" noOfLines={1} flex={1}>
                              {lab.testName}
                            </Text>
                          )}
                          <Text fontSize="xs" color="gray.500" fontWeight="medium">
                            {new Date(lab.testDate).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </Text>
                        </HStack>
                        
                        {/* Content Row - Results and Status */}
                        <HStack justify="space-between" align="center">
                          {/* Left Side - Result Values */}
                          <VStack align="start" spacing={0} flex={1} minWidth={0}>
                            <HStack spacing={1} align="baseline">
                              {dischargeNoteRelevantText.length > 0 ? (
                                <>
                                  <HighlightedText 
                                    text={value} 
                                    highlights={dischargeNoteRelevantText}
                                    fontSize="sm"
                                    fontWeight="bold"
                                    color={statusColors.valueColor}
                                  />
                                  {unit && (
                                    <Text fontSize="xs" color="gray.500">
                                      {unit}
                                    </Text>
                                  )}
                                </>
                              ) : (
                                <>
                                  <Text fontSize="sm" fontWeight="bold" color={statusColors.valueColor}>
                                    {value}
                                  </Text>
                                  {unit && (
                                    <Text fontSize="xs" color="gray.500">
                                      {unit}
                                    </Text>
                                  )}
                                </>
                              )}
                            </HStack>
                            <Text fontSize="xs" color="gray.400">
                              Normal: {lab.normalRange}
                            </Text>
                          </VStack>

                          {/* Right Side - Status */}
                          <Box minWidth="50px" textAlign="center">
                            <Text 
                              fontSize="xs" 
                              fontWeight="bold" 
                              color={statusColors.text}
                              px={1}
                            >
                              {displayStatus}
                            </Text>
                          </Box>
                        </HStack>
                        </Box>
                      </Box>
                    );
                  }) : (
                    <Box 
                      textAlign="center" 
                      py={8}
                      display="flex"
                      flexDirection="column"
                      justifyContent="center"
                      alignItems="center"
                      minHeight="300px"
                    >
                      <Text color="gray.500" fontSize="sm">
                        No lab results available
                      </Text>
                      <Text color="gray.400" fontSize="xs">
                        Lab results will appear here when available
                      </Text>
                    </Box>
                  )}
                </VStack>
              </Box>
            </Box>
          </VStack>
        {/* Column 2: Diagnosis and Treatment Course */}
          <VStack width="34%" spacing={4} align="stretch">
            {/* Diagnosis Block */}
            <Box 
              borderWidth={1}
              borderRadius="lg" 
              p={4}
              backgroundColor="white"
              borderColor="gray.300"
              height="400px"
              display="flex"
              flexDirection="column"
            >
              <Box display="flex" flexDirection="column" height="100%">
                <HStack mb={4} justifyContent="space-between">
                  <Heading as="h3" size="sm">
                    Diagnoses ({normalizeDiagnosis(dischargeNoteData.diagnosis).length})
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
                    {normalizeDiagnosis(dischargeNoteData.diagnosis).length > 0 ? (
                      normalizeDiagnosis(dischargeNoteData.diagnosis).map((diagnosis, index) => {
                        const getCategoryColor = (category: string) => {
                          switch (category) {
                            case 'Primary': return 'red';
                            case 'Secondary': return 'orange';
                            case 'Past': return 'gray';
                            case 'Current': return 'blue';
                            case 'Present': return 'blue'; // Handle 'Present' as well
                            default: return 'gray';
                          }
                        };

                        return (
                          <Box key={index} p={4} borderWidth={1} borderRadius="md" bg="white" shadow="sm">
                            <Flex align="start">
                              <VStack align="start" spacing={2} flex={1}>
                                <HStack spacing={3}>
                                  <Badge colorScheme={getCategoryColor(diagnosis.category)} size="md">
                                    {diagnosis.category}
                                  </Badge>
                                  {diagnosis.code && (
                                    dischargeNoteRelevantText.length > 0 ? (
                                      <Box>
                                        <HighlightedText 
                                          text={diagnosis.code} 
                                          highlights={dischargeNoteRelevantText}
                                          fontSize="sm"
                                          color="gray.600"
                                          fontFamily="mono"
                                        />
                                      </Box>
                                    ) : (
                                      <Text fontSize="sm" color="gray.600" fontFamily="mono">
                                        {diagnosis.code}
                                      </Text>
                                    )
                                  )}
                                  {diagnosis.date_diagnosed && (
                                    <Text fontSize="sm" color="gray.500">
                                      {new Date(diagnosis.date_diagnosed).toLocaleDateString()}
                                    </Text>
                                  )}
                                </HStack>
                                {dischargeNoteRelevantText.length > 0 ? (
                                  <HighlightedText 
                                    text={diagnosis.diagnosis} 
                                    highlights={dischargeNoteRelevantText}
                                    fontSize="md"
                                    fontWeight="medium"
                                  />
                                ) : (
                                  <Text fontSize="md" fontWeight="medium">
                                    {diagnosis.diagnosis}
                                  </Text>
                                )}
                              </VStack>
                            </Flex>
                          </Box>
                        );
                      })
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
            </Box>

            {/* Treatment Course */}
            <Box
                borderWidth={1}
                borderRadius="lg"
                p={3}
                backgroundColor="white"
                flex="1"
                display="flex"
                flexDirection="column"
            >
              <HStack justify="space-between" align="center" mb={3}>
                <Heading as="h3" size="sm">
                  Treatment Course
                </Heading>
                <Button
                    size="sm"
                    colorScheme="blue"
                    onClick={handleGenerateTreatmentCourse}
                    isLoading={isGeneratingTreatmentCourse}
                    isDisabled={!activeModels.dischargeNoteSummaryModel}
                >
                  Generate AI Summary
                </Button>
              </HStack>

              {/* Show model status */}
              {(!activeModels.dischargeNoteSummaryModel || !activeModels.dischargeNoteValidationModel) && (
                  <Text color="red.500" fontSize="xs" mb={2}>
                    Discharge note models not configured in admin panel
                  </Text>
              )}

              {/* Treatment Course - no highlighting on the treatment course itself */}
              <Textarea
                  value={treatmentCourse}
                  onChange={(e) => setTreatmentCourse(e.target.value)}
                  minHeight="200px"
                  maxHeight="350px"
                  backgroundColor="white"
                  fontSize="sm"
                  placeholder="Treatment course will be generated here, or you can enter manually..."
                  resize="vertical"
                  isReadOnly={dischargeNoteRelevantText.length > 0}
                  overflowY="auto"
                  flex="1"
              />

              {/* Action buttons */}
              <HStack spacing={2} mt={3}>
                <Button
                    size="sm"
                    colorScheme="green"
                    onClick={handleSubmitDischargeNote}
                    isLoading={isSubmittingDischargeNote}
                    isDisabled={isDischargeNoteLocked || !treatmentCourse.trim() || !patientInfo?.id}
                >
                  {isDischargeNoteLocked ? 'Discharge Note Locked ✓' : 'Submit Discharge Note'}
                </Button>
              </HStack>
            </Box>
          </VStack>

        {/* Column 3: Specialist Consultation and Nursing Note */}
        <VStack width="33%" spacing={3} align="stretch">
          {/* Specialist Consultation Block */}
          <Box 
            borderWidth={1}
            borderRadius="lg" 
            p={4}
            backgroundColor="white"
            borderColor="gray.300"
          >
            <Heading as="h3" size="sm" mb={3}>
              Specialist Consultation
            </Heading>
            <Box
              p={3}
              backgroundColor="gray.50"
              borderRadius="md"
              minHeight="120px"
              maxHeight="200px"
              fontSize="sm"
              overflowY="auto"
            >
              {dischargeNoteRelevantText.length > 0 && dischargeNoteData.specialistConsultation ? (
                <HighlightedText text={dischargeNoteData.specialistConsultation} highlights={dischargeNoteRelevantText} />
              ) : (
                <Text color={dischargeNoteData.specialistConsultation ? "gray.800" : "gray.500"} whiteSpace="pre-wrap">
                  {dischargeNoteData.specialistConsultation || "Specialist consultation records will be loaded automatically..."}
                </Text>
              )}
            </Box>
          </Box>

          {/* Nursing Note Block */}
          <Box 
            borderWidth={1}
            borderRadius="lg" 
            p={4}
            backgroundColor="white"
            borderColor="gray.300"
            flex="1"
            display="flex"
            flexDirection="column"
          >
            <Heading as="h3" size="sm" mb={3}>
              Nursing Note Summary
            </Heading>
            <Box
              p={3}
              backgroundColor="gray.50"
              borderRadius="md"
              minHeight="160px"
              maxHeight="300px"
              fontSize="sm"
              flex="1"
              overflowY="auto"
            >
              {dischargeNoteRelevantText.length > 0 && dischargeNoteData.nursingNote ? (
                <HighlightedText text={dischargeNoteData.nursingNote} highlights={dischargeNoteRelevantText} />
              ) : (
                <Text color={dischargeNoteData.nursingNote ? "gray.800" : "gray.500"} whiteSpace="pre-wrap">
                  {dischargeNoteData.nursingNote || "Nursing notes will be loaded automatically..."}
                </Text>
              )}
            </Box>
          </Box>

          {/* Model Information */}
          <Box p={2} backgroundColor="blue.50" borderRadius="md" overflow="hidden">
            <Text fontSize="xs" fontWeight="medium" mb={1}>Current AI Models:</Text>
            <Text fontSize="xs" color="gray.600" noOfLines={1} wordBreak="break-word">
              Summary: {activeModels.dischargeNoteSummaryModel || 'Not configured'}
            </Text>
            <Text fontSize="xs" color="gray.600" noOfLines={1} wordBreak="break-word">
              Validation: {activeModels.dischargeNoteValidationModel || 'Not configured'}
            </Text>
          </Box>
        </VStack>
      </HStack>
    );
  };

  const renderNursingNoteTab = () => {

    return (
      <VStack spacing={3} align="stretch" height="600px">
        {/* Top Row: Record Time, Record Type, and Speech-To-Text Input */}
        <Box 
          borderWidth={1} 
          borderRadius="lg" 
          p={4} 
          backgroundColor="white"
          height="200px"
          minHeight="200px"
        >
          <HStack spacing={3} align="stretch" height="100%">
            {/* Block 1: Record Time and Record Type */}
            <Box 
              width="30%" 
              borderWidth={1} 
              borderRadius="md" 
              p={4} 
              backgroundColor="gray.50"
            >
              <VStack spacing={3} align="stretch">
                <Box>
                  <Text fontSize="sm" fontWeight="medium" color="gray.700" mb={2}>
                    Record Time
                  </Text>
                  <Text 
                    fontSize="lg" 
                    fontWeight="bold" 
                    color="blue.600"
                    backgroundColor="blue.50"
                    px={3}
                    py={2}
                    borderRadius="md"
                    textAlign="center"
                  >
                    {recordTime}
                  </Text>
                </Box>

                <Box>
                  <Text fontSize="sm" fontWeight="medium" color="gray.700" mb={2}>
                    Record Type
                  </Text>
                  <Select 
                    placeholder="Select record type"
                    value={recordType}
                    onChange={(e) => setRecordType(e.target.value)}
                    backgroundColor="white"
                    size="sm"
                  >
                    <option value="Vital Signs">Vital Signs</option>
                    <option value="Medication Administration">Medication Administration</option>
                    <option value="Assessment">Assessment</option>
                    <option value="Care Plan">Care Plan</option>
                    <option value="Patient Education">Patient Education</option>
                    <option value="Discharge Planning">Discharge Planning</option>
                    <option value="Incident Report">Incident Report</option>
                  </Select>
                </Box>
              </VStack>
            </Box>

            {/* Block 2: Speech-To-Text Content */}
            <Box 
              width="70%" 
              borderWidth={1} 
              borderRadius="md" 
              p={4} 
              backgroundColor="gray.50"
              height="100%"
            >
              <HStack spacing={4} align="stretch" height="100%">
                {/* Left side - Controls */}
                <VStack align="start" spacing={3} minWidth="150px">
                  <Text fontSize="sm" fontWeight="medium" color="gray.700">
                    Speech-To-Text Content
                  </Text>
                  
                  <Button
                    size="sm"
                    colorScheme={isRecording ? "red" : "blue"}
                    onClick={isRecording ? handleStopRecording : handleStartRecording}
                    leftIcon={
                      isRecording ? (
                        <Box as="span" animation="pulse 1.5s infinite">
                          ⏹️
                        </Box>
                      ) : (
                        <span>🎤</span>
                      )
                    }
                  >
                    {isRecording ? "Stop Recording" : "Start Recording"}
                  </Button>
                  
                  <Button
                    size="sm"
                    colorScheme="green"
                    onClick={handleSubmitNursingNote}
                    isLoading={isSubmittingNote}
                    isDisabled={!speechToTextContent.trim() || !recordType || !patientInfo?.id}
                  >
                    Submit Note
                  </Button>
                </VStack>
                
                {/* Right side - Textarea */}
                <Box flex="1" height="100%">
                  <Textarea
                    value={speechToTextContent}
                    onChange={(e) => setSpeechToTextContent(e.target.value)}
                    placeholder="Speech-to-text content will appear here, or you can type manually..."
                    backgroundColor="white"
                    fontSize="sm"
                    resize="none"
                    height="100%"
                  />
                </Box>
              </HStack>
            </Box>
          </HStack>
        </Box>

        {/* Bottom Row: Nursing Note History */}
        <Box 
          borderWidth={1} 
          borderRadius="lg" 
          p={4} 
          backgroundColor="white"
          height="300px"
          minHeight="300px"
          overflowY="auto"
        >
          <Heading as="h3" size="sm" mb={3}>
            Nursing Note History
          </Heading>

          <VStack spacing={2} align="stretch">
            {nursingNoteHistory.map((note) => (
              <Box 
                key={note.id}
                borderWidth={1} 
                borderRadius="md" 
                p={3} 
                backgroundColor="gray.50"
                _hover={{ backgroundColor: "gray.100" }}
                cursor="pointer"
              >
                <HStack justify="space-between" align="start" mb={2}>
                  <VStack align="start" spacing={1}>
                    <Text fontSize="sm" fontWeight="bold" color="blue.600">
                      {note.timestamp}
                    </Text>
                    <Badge colorScheme="purple" size="sm">
                      {note.type}
                    </Badge>
                  </VStack>
                  <Text fontSize="xs" color="gray.600">
                    {note.nurse}
                  </Text>
                </HStack>
                
                <Text fontSize="sm" color="gray.700" lineHeight="1.5" whiteSpace="pre-wrap">
                  {note.content}
                </Text>
              </Box>
            ))}
          </VStack>
        </Box>
      </VStack>
    );
  };

  return (
      <OverlayComponent>
        <Box 
          width="100%"
          maxWidth="1400px" 
          backgroundColor="white" 
          borderRadius="lg" 
          boxShadow="lg"
          p={6}
          my={3}
        >
          <Heading as="h1" size="md" mb={3}>PrivNurse AI Assistant System</Heading>
          
          {/* Patient Information Header */}
          {renderPatientInfoHeader()}
          
          <Tabs index={activeTab} onChange={setActiveTab} variant="enclosed">
            <TabList>
              <Tab>Discharge Note</Tab>
              <Tab>Consultation</Tab>
              <Tab>Nursing Note (STT)</Tab>
            </TabList>

            <TabPanels>
              <TabPanel>
                {renderDischargeNoteTab()}
              </TabPanel>
              <TabPanel>
                {renderConsultationTab()}
              </TabPanel>
              <TabPanel>
                {renderNursingNoteTab()}
              </TabPanel>
            </TabPanels>
          </Tabs>
        </Box>
      </OverlayComponent>
  );
}
