import { create } from 'zustand';
import { FaultConfig, SystemHealth } from '../types';
import { isMockMode, setMockMode } from '../services/apiClient';

interface NotificationItem {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  timestamp: string;
}

interface AppStore {
  isCommandPaletteOpen: boolean;
  setCommandPaletteOpen: (open: boolean) => void;
  toggleCommandPalette: () => void;

  mockMode: boolean;
  setMockMode: (enabled: boolean) => void;

  backendConnected: boolean;
  setBackendConnected: (connected: boolean) => void;

  health: SystemHealth | null;
  setHealth: (health: SystemHealth | null) => void;

  activeFault: FaultConfig | null;
  setActiveFault: (fault: FaultConfig | null) => void;

  notifications: NotificationItem[];
  addNotification: (type: NotificationItem['type'], title: string, message: string) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;
}

export const useAppStore = create<AppStore>((set) => ({
  isCommandPaletteOpen: false,
  setCommandPaletteOpen: (open) => set({ isCommandPaletteOpen: open }),
  toggleCommandPalette: () => set((state) => ({ isCommandPaletteOpen: !state.isCommandPaletteOpen })),

  mockMode: isMockMode(),
  setMockMode: (enabled) => {
    setMockMode(enabled);
    set({ mockMode: enabled });
  },

  backendConnected: true,
  setBackendConnected: (connected) => set({ backendConnected: connected }),

  health: null,
  setHealth: (health) => set({ health }),

  activeFault: null,
  setActiveFault: (fault) => set({ activeFault: fault }),

  notifications: [],
  addNotification: (type, title, message) =>
    set((state) => ({
      notifications: [
        {
          id: Math.random().toString(36).substring(2, 9),
          type,
          title,
          message,
          timestamp: new Date().toLocaleTimeString(),
        },
        ...state.notifications.slice(0, 19),
      ],
    })),
  removeNotification: (id) =>
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    })),
  clearNotifications: () => set({ notifications: [] }),
}));
