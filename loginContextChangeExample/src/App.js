import React from 'react';
import { asyncWithLDProvider } from 'launchdarkly-react-client-sdk';
import LoginForm from './components/LoginForm';
import styled from 'styled-components';

const AppContainer = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: #f5f5f5;
`;

(async () => {
    const LDProvider = await asyncWithLDProvider({
      clientSideID: 'client-side-id-123abc',
      context: {
        "kind": "user",
        "key": "user-key-123abc",
        "name": "Sandy Smith",
        "email": "sandy@example.com"
      },
      options: { /* ... */ }
    });
    render(
      <LDProvider>
        <AppContainer>
        <LoginForm />
      </AppContainer>
      </LDProvider>,
      document.getElementById('reactDiv'),
    );
  })();

  export default App;
