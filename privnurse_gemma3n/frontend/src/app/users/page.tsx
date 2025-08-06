'use client'

import { useState, useEffect } from 'react';
import { Box, VStack, Heading, Table, Thead, Tbody, Tr, Th, Td, Button, 
  useToast, Modal, ModalOverlay, ModalContent, ModalHeader, ModalBody, 
  ModalCloseButton, FormControl, FormLabel, Input, Select, useDisclosure } from '@chakra-ui/react';
import { fetchWithAuth } from '@/utils/api';
import AuthGuard from '@/components/AuthGuard';
import OverlayComponent from '@/components/Overlay';

interface User {
  id: number;
  username: string;
  role: string;
  created_at: string;
  updated_at: string;
}

function UsersPageContent() {
  const [users, setUsers] = useState<User[]>([]);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [newUser, setNewUser] = useState({ username: '', password: '', role: 'user' });
  const toast = useToast();

  const fetchUsers = async () => {
    try {
      const response = await fetchWithAuth('/api/users');
      if (!response.ok) throw new Error('Failed to fetch users');
      const data = await response.json();
      setUsers(data.items);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Cannot get user list',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    }
  };

  useEffect(() => {
    fetchUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCreateUser = async () => {
    try {
      const response = await fetchWithAuth('/api/users', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newUser),
      });

      if (!response.ok) throw new Error('Failed to create user');

      toast({
        title: 'Success',
        description: 'User created successfully',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });

      onClose();
      fetchUsers();
      setNewUser({ username: '', password: '', role: 'user' });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to create user',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    }
  };

  const handleResetPassword = async (userId: number) => {
    try {
      const newPassword = prompt('Please enter new password');
      if (!newPassword) return;

      const response = await fetchWithAuth(`/api/users/${userId}/reset-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_id: userId, new_password: newPassword }),
      });

      if (!response.ok) throw new Error('Failed to reset password');

      toast({
        title: 'Success',
        description: 'Password reset successfully',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Password reset failed',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    }
  };

  return (
    <Box
      width="100%"
      maxWidth="1400px"  // 稍微比 history 寬一點
      backgroundColor="white"
      borderRadius="lg"
      boxShadow="lg"
      p={6}
      my={4}
      position="relative"
    >
      <VStack spacing={6} align="stretch">
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Heading size="lg">User Management</Heading>
          <Button colorScheme="blue" onClick={onOpen}>Add User</Button>
        </Box>

        <Table variant="simple">
          <Thead>
            <Tr>
              <Th>ID</Th>
              <Th>Username</Th>
              <Th>Role</Th>
              <Th>Created At</Th>
              <Th>Actions</Th>
            </Tr>
          </Thead>
          <Tbody>
            {users.map(user => (
              <Tr key={user.id}>
                <Td>{user.id}</Td>
                <Td>{user.username}</Td>
                <Td>{user.role}</Td>
                <Td>{new Date(user.created_at).toLocaleString()}</Td>
                <Td>
                  <Button
                    size="sm"
                    colorScheme="orange"
                    onClick={() => handleResetPassword(user.id)}
                  >
                    Reset Password
                  </Button>
                </Td>
              </Tr>
            ))}
          </Tbody>
        </Table>

        <Modal isOpen={isOpen} onClose={onClose}>
          <ModalOverlay />
          <ModalContent>
            <ModalHeader>Add User</ModalHeader>
            <ModalCloseButton />
            <ModalBody pb={6}>
              <FormControl>
                <FormLabel>Username</FormLabel>
                <Input
                  value={newUser.username}
                  onChange={(e) => setNewUser({...newUser, username: e.target.value})}
                />
              </FormControl>

              <FormControl mt={4}>
                <FormLabel>Password</FormLabel>
                <Input
                  type="password"
                  value={newUser.password}
                  onChange={(e) => setNewUser({...newUser, password: e.target.value})}
                />
              </FormControl>

              <FormControl mt={4}>
                <FormLabel>Role</FormLabel>
                <Select
                  value={newUser.role}
                  onChange={(e) => setNewUser({...newUser, role: e.target.value})}
                >
                  <option value="user">Regular User</option>
                  <option value="admin">Administrator</option>
                </Select>
              </FormControl>

              <Button colorScheme="blue" mr={3} mt={4} onClick={handleCreateUser}>
                Create
              </Button>
              <Button mt={4} onClick={onClose}>Cancel</Button>
            </ModalBody>
          </ModalContent>
        </Modal>
      </VStack>
    </Box>
  );
}

export default function UsersPage() {
  return (
    <OverlayComponent>
        <AuthGuard adminRequired>
        <UsersPageContent />
        </AuthGuard>
    </OverlayComponent>
  );
}
