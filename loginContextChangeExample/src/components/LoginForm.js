import React, { useEffect } from 'react';
import { useLDClient, useFlags } from 'launchdarkly-react-client-sdk';
import styled from 'styled-components';

const FormContainer = styled.div`
  background-color: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 400px;
`;

const FormGroup = styled.div`
  margin-bottom: 1rem;
`;

const Label = styled.label`
  display: block;
  margin-bottom: 0.5rem;
  color: #333;
`;

const Input = styled.input`
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
`;

const Button = styled.button`
  width: 100%;
  padding: 0.75rem;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  transition: background-color 0.2s;

  &:hover {
    background-color: #0056b3;
  }
`;

const ErrorMessage = styled.div`
  color: #dc3545;
  margin-top: 1rem;
  display: ${props => props.show ? 'block' : 'none'};
`;

const LoginForm = () => {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    role: ''
  });
  const [error, setError] = useState('');
  
  const ldClient = useLDClient();
  const flags = useFlags();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    try {
      // Update the LaunchDarkly context with the user's information
      await ldClient.identify({
        kind: 'user',
        key: formData.username,
        email: formData.email,
        role: formData.role
      });

      // Check if access is granted based on the flag
      if (flags.accessGranted) {
        console.log('Access granted for role:', formData.role);
        // Handle successful login
        alert('Login successful!');
      } else {
        console.log('Access denied for role:', formData.role);
        setError('Access denied for this role');
      }
    } catch (err) {
      console.error('Error during login:', err);
      setError('An error occurred during login');
    }
  };

  return (
    <FormContainer>
      <h2>Login</h2>
      <form onSubmit={handleSubmit}>
        <FormGroup>
          <Label htmlFor="username">Username</Label>
          <Input
            type="text"
            id="username"
            name="username"
            value={formData.username}
            onChange={handleChange}
            required
          />
        </FormGroup>
        <FormGroup>
          <Label htmlFor="email">Email</Label>
          <Input
            type="email"
            id="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            required
          />
        </FormGroup>
        <FormGroup>
          <Label htmlFor="role">Role</Label>
          <Input
            type="text"
            id="role"
            name="role"
            value={formData.role}
            onChange={handleChange}
            required
          />
        </FormGroup>
        <Button type="submit">Login</Button>
      </form>
      <ErrorMessage show={!!error}>{error}</ErrorMessage>
    </FormContainer>
  );
};

export default LoginForm; 