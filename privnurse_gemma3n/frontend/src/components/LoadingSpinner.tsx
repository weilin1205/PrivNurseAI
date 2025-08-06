'use client'

import { Box, Spinner } from '@chakra-ui/react'

export default function LoadingSpinner() {

  return (
    <Box
      position="fixed"
      top={0}
      left={'15rem'}
      right={0}
      bottom={0}
      backgroundColor="rgba(255, 255, 255, 0.5)"
      backdropFilter="blur(5px)"
      display="flex"
      alignItems="center"
      justifyContent="center"
      zIndex={9998}
      transition="left 0.3s"
    >
      <Spinner
        thickness="4px"
        speed="0.65s"
        emptyColor="gray.200"
        color="blue.500"
        size="xl"
      />
    </Box>
  )
}