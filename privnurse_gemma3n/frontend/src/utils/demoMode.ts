import { createStandaloneToast } from '@chakra-ui/react';

const { toast } = createStandaloneToast();

interface DemoModeError {
  error: string;
  message: string;
  demo_mode: boolean;
}

export function isDemoModeError(error: any): error is DemoModeError {
  return error?.demo_mode === true;
}

export function showDemoModeAlert(message?: string) {
  const defaultMessage = "Thank you for your interest! This application is currently in demo mode and does not support data submissions or changes.";
  
  toast({
    title: "Write Access Restricted",
    description: message || defaultMessage,
    status: "warning",
    duration: 5000,
    isClosable: true,
    position: "top",
  });
}

export async function handleApiResponse(response: Response) {
  if (response.status === 403) {
    const data = await response.json();
    if (isDemoModeError(data.detail)) {
      showDemoModeAlert(data.detail.message);
      throw new Error('Demo mode restriction');
    }
  }
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  
  return response;
}