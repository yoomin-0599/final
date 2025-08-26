import { useEffect } from 'react';

interface KeyboardShortcuts {
  onRefresh?: () => void;
  onToggleTheme?: () => void;
  onSearch?: () => void;
  onNextTab?: () => void;
  onPrevTab?: () => void;
}

export const useKeyboardShortcuts = (shortcuts: KeyboardShortcuts) => {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Ctrl/Cmd + R: 새로고침
      if ((event.ctrlKey || event.metaKey) && event.key === 'r' && shortcuts.onRefresh) {
        event.preventDefault();
        shortcuts.onRefresh();
        return;
      }
      
      // Ctrl/Cmd + D: 다크 모드 토글
      if ((event.ctrlKey || event.metaKey) && event.key === 'd' && shortcuts.onToggleTheme) {
        event.preventDefault();
        shortcuts.onToggleTheme();
        return;
      }
      
      // Ctrl/Cmd + K: 검색
      if ((event.ctrlKey || event.metaKey) && event.key === 'k' && shortcuts.onSearch) {
        event.preventDefault();
        shortcuts.onSearch();
        return;
      }
      
      // Ctrl/Cmd + 오른쪽 화살표: 다음 탭
      if ((event.ctrlKey || event.metaKey) && event.key === 'ArrowRight' && shortcuts.onNextTab) {
        event.preventDefault();
        shortcuts.onNextTab();
        return;
      }
      
      // Ctrl/Cmd + 왼쪽 화살표: 이전 탭
      if ((event.ctrlKey || event.metaKey) && event.key === 'ArrowLeft' && shortcuts.onPrevTab) {
        event.preventDefault();
        shortcuts.onPrevTab();
        return;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [shortcuts]);
};
