import React, { createContext, useState, useContext, useCallback } from 'react';
import styled from 'styled-components/macro';

// Styled components for notifications
const NotificationContainer = styled.div`
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 9999;
`;

const NotificationItem = styled.div`
  background-color: ${props => props.type === 'error' ? '#f44336' : '#4caf50'};
  color: white;
  padding: 12px 16px;
  margin-bottom: 10px;
  border-radius: 4px;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-width: 250px;
  max-width: 400px;
  animation: slideIn 0.3s ease-out forwards;
  font-size: 14px;

  @keyframes slideIn {
    from {
      transform: translateX(100%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }
`;

const CloseButton = styled.button`
  background: transparent;
  border: none;
  color: white;
  font-size: 18px;
  cursor: pointer;
  margin-left: 10px;
  padding: 0;
  line-height: 1;
`;

// Create the context
const NotificationContext = createContext();

// Custom hook for using the notification system
export const useNotification = () => {
  return useContext(NotificationContext);
};

// The notification component used internally
const NotificationComponent = ({ notifications, removeNotification }) => {
  return (
    <NotificationContainer>
      {notifications.map((notification) => (
        <NotificationItem key={notification.id} type={notification.type}>
          <span>{notification.message}</span>
          <CloseButton onClick={() => removeNotification(notification.id)}>×</CloseButton>
        </NotificationItem>
      ))}
    </NotificationContainer>
  );
};

// The provider component that wraps your app
export const NotificationProvider = ({ children }) => {
  const [notifications, setNotifications] = useState([]);

  const addNotification = useCallback((message, type = 'success', duration = 5000) => {
    const id = Date.now();
    setNotifications(prev => [...prev, { id, message, type }]);

    if (duration > 0) {
      setTimeout(() => {
        removeNotification(id);
      }, duration);
    }

    return id;
  }, []);

  const removeNotification = useCallback((id) => {
    setNotifications(prev => prev.filter(notification => notification.id !== id));
  }, []);

  return (
    <NotificationContext.Provider 
      value={{ 
        addNotification, 
        removeNotification 
      }}
    >
      {children}
      <NotificationComponent 
        notifications={notifications} 
        removeNotification={removeNotification} 
      />
    </NotificationContext.Provider>
  );
};

export default NotificationContext;