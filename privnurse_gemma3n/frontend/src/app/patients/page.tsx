'use client'

import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Heading, 
  Table, 
  Thead, 
  Tbody, 
  Tr, 
  Th, 
  Td, 
  Badge, 
  Button, 
  HStack, 
  VStack, 
  Input, 
  Select, 
  useToast,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  useDisclosure,
  FormControl,
  FormLabel,
  Textarea,
  Text,
  Divider,
  IconButton,
  Tooltip,
  InputGroup,
  InputLeftElement,
  Grid,
  GridItem,
  Spacer
} from '@chakra-ui/react';
import { EditIcon, DeleteIcon, ViewIcon, SearchIcon, AddIcon } from '@chakra-ui/icons';
import OverlayComponent from "@/components/Overlay";
import AuthGuard from '@/components/AuthGuard';
import DiagnosisList, { Diagnosis } from '@/components/DiagnosisList';
import { fetchWithAuth } from '@/utils/api';
import { useRouter } from 'next/navigation';

// Helper function to convert diagnosis data to array format
const normalizeDiagnosis = (diagnosis: any): Diagnosis[] => {
  if (Array.isArray(diagnosis)) {
    return diagnosis;
  }
  if (typeof diagnosis === 'string' && diagnosis.trim()) {
    // Convert old string format to array format
    return [{ category: 'Main', diagnosis: diagnosis.trim() }];
  }
  return [];
};

interface PatientInfo {
  id: number;
  medical_record_no: string;
  patient_category: 'NHI General' | 'NHI Injury' | 'Self-Pay';
  name: string;
  gender: 'M' | 'F';
  weight: number;
  department: string;
  birthday: string;
  admission_time: string;
  discharge_time?: string;
  bed_number: string;
  status: 'HOSPITALIZED' | 'DISCHARGED' | 'TRANSFERRED';
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  insurance_number?: string;
  created_at: string;
  updated_at: string;
  created_by?: number;
}

export default function PatientsPage() {
  return (
    <AuthGuard>
      <PatientsPageContent />
    </AuthGuard>
  );
}

function PatientsPageContent() {
  const [patients, setPatients] = useState<PatientInfo[]>([]);
  const [filteredPatients, setFilteredPatients] = useState<PatientInfo[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [departmentFilter, setDepartmentFilter] = useState('');
  const [selectedPatient, setSelectedPatient] = useState<PatientInfo | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [departments, setDepartments] = useState<string[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalPatients, setTotalPatients] = useState(0);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const toast = useToast();
  const router = useRouter();

  // Fetch patients from API
  const fetchPatients = async (page: number = 1) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        limit: '10'
      });
      
      if (searchTerm) params.append('search_term', searchTerm);
      if (statusFilter) params.append('status', statusFilter);
      if (departmentFilter) params.append('department', departmentFilter);

      const response = await fetchWithAuth(`/api/patients?${params}`);
      
      if (response.ok) {
        const data = await response.json();
        setPatients(data.items);
        setFilteredPatients(data.items);
        setTotalPages(data.pages);
        setTotalPatients(data.total);
        setCurrentPage(page);
      } else {
        throw new Error('Failed to fetch patients');
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to load patients",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };

  // Fetch departments for filter
  const fetchDepartments = async () => {
    try {
      const response = await fetchWithAuth('/api/departments');
      if (response.ok) {
        const data = await response.json();
        setDepartments(data);
      }
    } catch (error) {
      console.error('Failed to fetch departments:', error);
    }
  };

  useEffect(() => {
    fetchPatients();
    fetchDepartments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      fetchPatients(1);
    }, 500);

    return () => clearTimeout(timeoutId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchTerm, statusFilter, departmentFilter]);

  const handleViewPatient = (patient: PatientInfo) => {
    setSelectedPatient(patient);
    setIsEditing(false);
    onOpen();
  };

  const handleEditPatient = (patient: PatientInfo) => {
    setSelectedPatient(patient);
    setIsEditing(true);
    onOpen();
  };

  const handleLoadInSummary = (patient: PatientInfo) => {
    // Store patient data in localStorage for use in summary page
    localStorage.setItem('selectedPatient', JSON.stringify(patient));
    
    toast({
      title: "Patient Loaded",
      description: `${patient.name} data loaded for summary page`,
      status: "success",
      duration: 3000,
      isClosable: true,
    });

    // Navigate to summary page
    router.push('/summary');
  };

  const handleSavePatient = async () => {
    if (!selectedPatient) return;

    // Validate required fields
    if (!selectedPatient.medical_record_no.trim()) {
      toast({
        title: "Validation Error",
        description: "Medical Record Number is required",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    if (!selectedPatient.name.trim()) {
      toast({
        title: "Validation Error",
        description: "Patient name is required",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    if (!selectedPatient.department.trim()) {
      toast({
        title: "Validation Error",
        description: "Department is required",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    if (!selectedPatient.birthday.trim()) {
      toast({
        title: "Validation Error",
        description: "Birthday is required",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    try {
      setLoading(true);
      
      if (isEditing && selectedPatient.id !== 0) {
        // Update existing patient
        const response = await fetchWithAuth(`/api/patients/${selectedPatient.id}`, {
          method: 'PUT',
          body: JSON.stringify({
            medical_record_no: selectedPatient.medical_record_no,
            patient_category: selectedPatient.patient_category,
            name: selectedPatient.name,
            gender: selectedPatient.gender,
            weight: selectedPatient.weight,
            department: selectedPatient.department,
            birthday: selectedPatient.birthday,
            admission_time: selectedPatient.admission_time,
            discharge_time: selectedPatient.discharge_time,
            bed_number: selectedPatient.bed_number,
            status: selectedPatient.status,
            emergency_contact_name: selectedPatient.emergency_contact_name,
            emergency_contact_phone: selectedPatient.emergency_contact_phone,
            insurance_number: selectedPatient.insurance_number
          })
        });

        if (response.ok) {
          toast({
            title: "Patient Updated",
            description: "Patient information has been updated successfully",
            status: "success",
            duration: 3000,
            isClosable: true,
          });
          fetchPatients(currentPage);
        } else {
          throw new Error('Failed to update patient');
        }
      } else {
        // Create new patient
        const response = await fetchWithAuth('/api/patients', {
          method: 'POST',
          body: JSON.stringify({
            medical_record_no: selectedPatient.medical_record_no,
            patient_category: selectedPatient.patient_category,
            name: selectedPatient.name,
            gender: selectedPatient.gender,
            weight: selectedPatient.weight,
            department: selectedPatient.department,
            birthday: selectedPatient.birthday,
            admission_time: selectedPatient.admission_time,
            bed_number: selectedPatient.bed_number,
            status: selectedPatient.status,
            emergency_contact_name: selectedPatient.emergency_contact_name,
            emergency_contact_phone: selectedPatient.emergency_contact_phone,
            insurance_number: selectedPatient.insurance_number
          })
        });

        if (response.ok) {
          toast({
            title: "Patient Added",
            description: "New patient has been added successfully",
            status: "success",
            duration: 3000,
            isClosable: true,
          });
          fetchPatients(currentPage);
        } else {
          throw new Error('Failed to create patient');
        }
      }
      
      onClose();
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to save patient information",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDeletePatient = async (patientId: number) => {
    if (!confirm('Are you sure you want to delete this patient?')) return;
    
    try {
      setLoading(true);
      const response = await fetchWithAuth(`/api/patients/${patientId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        toast({
          title: "Patient Deleted",
          description: "Patient record has been deleted",
          status: "warning",
          duration: 3000,
          isClosable: true,
        });
        fetchPatients(currentPage);
      } else {
        throw new Error('Failed to delete patient');
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to delete patient",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'NHI General': return 'blue';
      case 'NHI Injury': return 'orange';
      case 'Self-Pay': return 'purple';
      default: return 'gray';
    }
  };

  const getStatusColor = (status: string) => {
    return status === 'HOSPITALIZED' ? 'red' : 'green';
  };

  const calculateAge = (birthDate: string) => {
    const birth = new Date(birthDate);
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
        <Heading as="h1" size="lg" mb={6}>Patient Management System</Heading>
        
        {/* Search and Filters Section */}
        <Box mb={6}>
          <Grid templateColumns="1fr auto" gap={6} alignItems="end">
            <GridItem>
              <HStack spacing={4} wrap="wrap">
                <FormControl maxWidth="400px">
                  <FormLabel>Search Patients</FormLabel>
                  <InputGroup>
                    <InputLeftElement pointerEvents="none">
                      <SearchIcon color="gray.300" />
                    </InputLeftElement>
                    <Input 
                      placeholder="Name, Medical Record No., Bed No..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                    />
                  </InputGroup>
                </FormControl>
                
                <FormControl maxWidth="200px">
                  <FormLabel>Department Filter</FormLabel>
                  <Select 
                    placeholder="All Departments"
                    value={departmentFilter}
                    onChange={(e) => setDepartmentFilter(e.target.value)}
                  >
                    {departments.map(dept => (
                      <option key={dept} value={dept}>{dept}</option>
                    ))}
                  </Select>
                </FormControl>

                <FormControl maxWidth="200px">
                  <FormLabel>Status Filter</FormLabel>
                  <Select 
                    placeholder="All Status"
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                  >
                    <option value="HOSPITALIZED">Hospitalized</option>
                    <option value="DISCHARGED">Discharged</option>
                    <option value="TRANSFERRED">Transferred</option>
                  </Select>
                </FormControl>
              </HStack>
            </GridItem>
            
            <GridItem>
              <Button 
                colorScheme="blue"
                leftIcon={<AddIcon />}
                onClick={() => {
                  const now = new Date();
                  const currentDateTime = now.toISOString().slice(0, 16);
                  
                  setSelectedPatient({
                    id: 0,
                    medical_record_no: '',
                    patient_category: 'NHI General',
                    name: '',
                    gender: 'M',
                    weight: 0,
                    department: '',
                    birthday: '',
                    admission_time: currentDateTime + ':00',
                    bed_number: '',
                    status: 'HOSPITALIZED',
                    emergency_contact_name: '',
                    emergency_contact_phone: '',
                    insurance_number: '',
                    created_at: '',
                    updated_at: ''
                  });
                  setIsEditing(true);
                  onOpen();
                }}
              >
                Add Patient
              </Button>
            </GridItem>
          </Grid>
        </Box>

        {/* Patients Table */}
        <Box overflowX="auto">
          <Table variant="simple">
            <Thead>
              <Tr>
                <Th>Medical Record No.</Th>
                <Th>Name</Th>
                <Th>Gender/Age</Th>
                <Th>Patient Category</Th>
                <Th>Department</Th>
                <Th>Bed No.</Th>
                <Th>Admission Date</Th>
                <Th>Status</Th>
                <Th>Actions</Th>
              </Tr>
            </Thead>
            <Tbody>
              {filteredPatients.map((patient) => (
                <Tr key={patient.id}>
                  <Td fontWeight="medium">{patient.medical_record_no}</Td>
                  <Td fontWeight="medium">{patient.name}</Td>
                  <Td>
                    <Text fontSize="sm">
                      {patient.gender} / {calculateAge(patient.birthday)}
                    </Text>
                  </Td>
                  <Td>
                    <Badge colorScheme={getCategoryColor(patient.patient_category)} size="sm">
                      {patient.patient_category}
                    </Badge>
                  </Td>
                  <Td>{patient.department}</Td>
                  <Td>{patient.bed_number}</Td>
                  <Td>
                    <Text fontSize="sm">
                      {new Date(patient.admission_time).toLocaleDateString()}
                    </Text>
                  </Td>
                  <Td>
                    <Badge colorScheme={getStatusColor(patient.status)} size="sm">
                      {patient.status}
                    </Badge>
                  </Td>
                  <Td>
                    <HStack spacing={2}>
                      <Tooltip label="View Details">
                        <IconButton
                          icon={<ViewIcon />}
                          size="sm"
                          colorScheme="blue"
                          variant="ghost"
                          onClick={() => handleViewPatient(patient)}
                          aria-label="View patient"
                        />
                      </Tooltip>
                      
                      <Tooltip label="Edit Patient">
                        <IconButton
                          icon={<EditIcon />}
                          size="sm"
                          colorScheme="green"
                          variant="ghost"
                          onClick={() => handleEditPatient(patient)}
                          aria-label="Edit patient"
                        />
                      </Tooltip>
                      
                      <Button
                        size="sm"
                        colorScheme="purple"
                        onClick={() => handleLoadInSummary(patient)}
                      >
                        Load in Summary
                      </Button>
                      
                      <Tooltip label="Delete Patient">
                        <IconButton
                          icon={<DeleteIcon />}
                          size="sm"
                          colorScheme="red"
                          variant="ghost"
                          onClick={() => handleDeletePatient(patient.id)}
                          aria-label="Delete patient"
                        />
                      </Tooltip>
                    </HStack>
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>

        {loading && (
          <Box textAlign="center" py={10}>
            <Text color="gray.500">Loading patients...</Text>
          </Box>
        )}

        {!loading && filteredPatients.length === 0 && (
          <Box textAlign="center" py={10}>
            <Text color="gray.500">No patients found matching the criteria</Text>
          </Box>
        )}

        {/* Pagination Controls */}
        {totalPages > 1 && (
          <Box mt={6} display="flex" justifyContent="space-between" alignItems="center">
            <Text fontSize="sm" color="gray.600">
              Showing {(currentPage - 1) * 10 + 1} to {Math.min(currentPage * 10, totalPatients)} of {totalPatients} patients
            </Text>
            <HStack spacing={2}>
              <Button 
                size="sm" 
                disabled={currentPage === 1}
                onClick={() => fetchPatients(currentPage - 1)}
              >
                Previous
              </Button>
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                const pageNum = Math.max(1, currentPage - 2) + i;
                if (pageNum > totalPages) return null;
                return (
                  <Button
                    key={pageNum}
                    size="sm"
                    variant={pageNum === currentPage ? "solid" : "outline"}
                    colorScheme={pageNum === currentPage ? "blue" : "gray"}
                    onClick={() => fetchPatients(pageNum)}
                  >
                    {pageNum}
                  </Button>
                );
              })}
              <Button 
                size="sm" 
                disabled={currentPage === totalPages}
                onClick={() => fetchPatients(currentPage + 1)}
              >
                Next
              </Button>
            </HStack>
          </Box>
        )}

        {/* Patient Details Modal */}
        <Modal isOpen={isOpen} onClose={onClose} size="xl">
          <ModalOverlay />
          <ModalContent>
            <ModalHeader>
              {isEditing ? 'Edit Patient' : 'Patient Details'}
            </ModalHeader>
            <ModalCloseButton />
            <ModalBody>
              {selectedPatient && (
                <VStack spacing={4} align="stretch">
                  <HStack spacing={4}>
                    <FormControl isRequired>
                      <FormLabel>Medical Record No.</FormLabel>
                      <Input 
                        value={selectedPatient.medical_record_no}
                        isReadOnly={!isEditing}
                        onChange={(e) => setSelectedPatient({
                          ...selectedPatient,
                          medical_record_no: e.target.value
                        })}
                      />
                    </FormControl>
                    
                    <FormControl isRequired>
                      <FormLabel>Name</FormLabel>
                      <Input 
                        value={selectedPatient.name}
                        isReadOnly={!isEditing}
                        onChange={(e) => setSelectedPatient({
                          ...selectedPatient,
                          name: e.target.value
                        })}
                      />
                    </FormControl>
                  </HStack>

                  <HStack spacing={4}>
                    <FormControl>
                      <FormLabel>Gender</FormLabel>
                      <Select 
                        value={selectedPatient.gender}
                        isDisabled={!isEditing}
                        onChange={(e) => setSelectedPatient({
                          ...selectedPatient,
                          gender: e.target.value as 'M' | 'F'
                        })}
                      >
                        <option value="M">Male</option>
                        <option value="F">Female</option>
                      </Select>
                    </FormControl>
                    
                    <FormControl>
                      <FormLabel>Weight (kg)</FormLabel>
                      <Input 
                        type="number"
                        value={selectedPatient.weight}
                        isReadOnly={!isEditing}
                        onChange={(e) => setSelectedPatient({
                          ...selectedPatient,
                          weight: parseFloat(e.target.value)
                        })}
                      />
                    </FormControl>
                  </HStack>

                  <HStack spacing={4}>
                    <FormControl isRequired>
                      <FormLabel>Department</FormLabel>
                      <Input 
                        value={selectedPatient.department}
                        isReadOnly={!isEditing}
                        onChange={(e) => setSelectedPatient({
                          ...selectedPatient,
                          department: e.target.value
                        })}
                      />
                    </FormControl>
                    
                    <FormControl>
                      <FormLabel>Bed Number</FormLabel>
                      <Input 
                        value={selectedPatient.bed_number}
                        isReadOnly={!isEditing}
                        onChange={(e) => setSelectedPatient({
                          ...selectedPatient,
                          bed_number: e.target.value
                        })}
                      />
                    </FormControl>
                  </HStack>

                  <HStack spacing={4}>
                    <FormControl>
                      <FormLabel>Status</FormLabel>
                      <Select 
                        value={selectedPatient.status}
                        isDisabled={!isEditing}
                        onChange={(e) => setSelectedPatient({
                          ...selectedPatient,
                          status: e.target.value as 'HOSPITALIZED' | 'DISCHARGED'
                        })}
                      >
                        <option value="HOSPITALIZED">Hospitalized</option>
                        <option value="DISCHARGED">Discharged</option>
                      </Select>
                    </FormControl>
                    
                    <FormControl>
                      <FormLabel>Category</FormLabel>
                      <Select 
                        value={selectedPatient.patient_category}
                        isDisabled={!isEditing}
                        onChange={(e) => setSelectedPatient({
                          ...selectedPatient,
                          patient_category: e.target.value as 'NHI General' | 'NHI Injury' | 'Self-Pay'
                        })}
                      >
                        <option value="NHI General">NHI General</option>
                        <option value="NHI Injury">NHI Injury</option>
                        <option value="Self-Pay">Self-Pay</option>
                      </Select>
                    </FormControl>
                  </HStack>

                  <HStack spacing={4}>
                    <FormControl isRequired>
                      <FormLabel>Birthday</FormLabel>
                      <Input 
                        type="date"
                        value={selectedPatient.birthday}
                        isReadOnly={!isEditing}
                        onChange={(e) => setSelectedPatient({
                          ...selectedPatient,
                          birthday: e.target.value
                        })}
                      />
                    </FormControl>
                    
                    <FormControl>
                      <FormLabel>Admission Time</FormLabel>
                      <Input 
                        type="datetime-local"
                        value={selectedPatient.admission_time ? selectedPatient.admission_time.slice(0, 16) : ''}
                        isReadOnly={!isEditing}
                        onChange={(e) => setSelectedPatient({
                          ...selectedPatient,
                          admission_time: e.target.value ? e.target.value + ':00' : ''
                        })}
                      />
                    </FormControl>
                  </HStack>

                  <HStack spacing={4}>
                    <FormControl>
                      <FormLabel>Emergency Contact Name</FormLabel>
                      <Input 
                        value={selectedPatient.emergency_contact_name || ''}
                        isReadOnly={!isEditing}
                        onChange={(e) => setSelectedPatient({
                          ...selectedPatient,
                          emergency_contact_name: e.target.value
                        })}
                      />
                    </FormControl>
                    
                    <FormControl>
                      <FormLabel>Emergency Contact Phone</FormLabel>
                      <Input 
                        value={selectedPatient.emergency_contact_phone || ''}
                        isReadOnly={!isEditing}
                        onChange={(e) => setSelectedPatient({
                          ...selectedPatient,
                          emergency_contact_phone: e.target.value
                        })}
                      />
                    </FormControl>
                  </HStack>

                  <FormControl>
                    <FormLabel>Insurance Number</FormLabel>
                    <Input 
                      value={selectedPatient.insurance_number || ''}
                      isReadOnly={!isEditing}
                      onChange={(e) => setSelectedPatient({
                        ...selectedPatient,
                        insurance_number: e.target.value
                      })}
                    />
                  </FormControl>

                  <Divider />


                </VStack>
              )}
            </ModalBody>

            <ModalFooter>
              <HStack spacing={3}>
                {!isEditing && selectedPatient && (
                  <Button 
                    colorScheme="purple"
                    onClick={() => handleLoadInSummary(selectedPatient)}
                  >
                    Load in Summary
                  </Button>
                )}
                
                {isEditing ? (
                  <Button colorScheme="blue" onClick={handleSavePatient}>
                    Save Changes
                  </Button>
                ) : (
                  <Button colorScheme="green" onClick={() => setIsEditing(true)}>
                    Edit Patient
                  </Button>
                )}
                
                <Button variant="ghost" onClick={onClose}>
                  Close
                </Button>
              </HStack>
            </ModalFooter>
          </ModalContent>
        </Modal>
      </Box>
    </OverlayComponent>
  );
}