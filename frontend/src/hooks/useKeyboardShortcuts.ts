import { useEffect, useCallback } from 'react';

export interface KeyboardShortcut {
  key: string;
  ctrlKey?: boolean;
  metaKey?: boolean;
  shiftKey?: boolean;
  altKey?: boolean;
  handler: () => void;
  description: string;
}

export function useKeyboardShortcuts(shortcuts: KeyboardShortcut[]) {
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    for (const shortcut of shortcuts) {
      const matches = 
        event.key.toLowerCase() === shortcut.key.toLowerCase() &&
        (shortcut.ctrlKey === undefined || event.ctrlKey === shortcut.ctrlKey) &&
        (shortcut.metaKey === undefined || event.metaKey === shortcut.metaKey) &&
        (shortcut.shiftKey === undefined || event.shiftKey === shortcut.shiftKey) &&
        (shortcut.altKey === undefined || event.altKey === shortcut.altKey);

      if (matches) {
        event.preventDefault();
        shortcut.handler();
        break;
      }
    }
  }, [shortcuts]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
}

export const SHORTCUTS: Record<string, KeyboardShortcut> = {
  SEARCH: {
    key: 'k',
    metaKey: true,
    handler: () => {},  // Will be overridden
    description: 'Focus search (Cmd+K or Ctrl+K)'
  },
  IMPORT: {
    key: 'i',
    metaKey: true,
    handler: () => {},
    description: 'Go to import (Cmd+I or Ctrl+I)'
  },
  DOCUMENTS: {
    key: 'd',
    metaKey: true,
    handler: () => {},
    description: 'Go to documents (Cmd+D or Ctrl+D)'
  },
  ESCAPE: {
    key: 'Escape',
    handler: () => {},
    description: 'Close modals / Clear search (Esc)'
  },
  HELP: {
    key: '?',
    shiftKey: true,
    handler: () => {},
    description: 'Show keyboard shortcuts (Shift+?)'
  }
};

