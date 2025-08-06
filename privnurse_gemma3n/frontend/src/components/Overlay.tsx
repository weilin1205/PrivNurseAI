import Navbar from "@/components/Navbar";
import React from "react";
import { Box, Flex } from "@chakra-ui/react";

interface OverlayComponentProps {
  children: React.ReactNode;
}

const OverlayComponent: React.FC<OverlayComponentProps> = ({ children }) => {
  return (
    <Flex h="100vh" direction="row">
      <Navbar />
      <Box
        minHeight="100vh"
        width="100%"
        display="flex"
        flexDirection="column"
        backgroundColor="rgba(255, 255, 255, 0.8)"
        alignItems="center"
        position="relative"
        overflow="auto"
        sx={{
          '&::before': {
            content: '""',
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundImage: "url('/medical-background.webp')",
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            backgroundRepeat: 'no-repeat',
            zIndex: -1,
          }
        }}
      >
        {children}
      </Box>
    </Flex>
  );
};

export default OverlayComponent;
