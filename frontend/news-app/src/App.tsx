import React, { useState, useEffect, useRef } from 'react';
import './App.css';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

function App() {
  // 세션 상태 초기화
  const [messages, setMessages] = useState<Message[]>(() => {
    // 초기 메시지 설정
    return [
      { role: 'assistant', content: '안녕하세요! 무엇을 도와드릴까요?' }
    ];
  });
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // 메시지가 추가될 때마다 스크롤
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 입력 필드에 포커스
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSendMessage = () => {
    if (inputValue.trim()) {
      // 사용자 메시지 추가
      const userMessage: Message = { role: 'user', content: inputValue };
      setMessages(prev => [...prev, userMessage]);
      
      // 입력 필드 초기화
      const userInput = inputValue;
      setInputValue('');
      
      // AI 응답 생성 (시뮬레이션)
      setTimeout(() => {
        const assistantMessage: Message = { 
          role: 'assistant', 
          content: `"${userInput}"에 대한 응답입니다. 어떻게 도와드릴까요?` 
        };
        setMessages(prev => [...prev, assistantMessage]);
      }, 1000);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="streamlit-container">
      {/* 메인 영역 */}
      <div className="main-area">
        {/* 헤더 */}
        <div className="main-header">
          <h1>💬 채팅 인터페이스</h1>
        </div>

        {/* 채팅 메시지 영역 */}
        <div className="chat-container">
          {messages.map((message, index) => (
            <div key={index} className={`chat-message-container ${message.role}`}>
              <div className="message-avatar">
                {message.role === 'user' ? '👤' : '🤖'}
              </div>
              <div className="message-content-wrapper">
                <div className="message-role">
                  {message.role === 'user' ? '사용자' : 'AI'}
                </div>
                <div className="message-content">
                  {message.content}
                </div>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* 입력 영역 */}
        <div className="chat-input-container">
          <input
            ref={inputRef}
            type="text"
            className="chat-input"
            placeholder="메시지를 입력하세요..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyPress}
          />
          <button 
            className="send-button"
            onClick={handleSendMessage}
            disabled={!inputValue.trim()}
          >
            ➤
          </button>
        </div>
      </div>

      {/* 사이드바 */}
      <div className="sidebar">
        <div className="sidebar-header">
          <h2>채팅 설정</h2>
        </div>
        
        <div className="sidebar-content">
          <div className="info-section">
            <h3>📊 세션 상태</h3>
            <div className="session-info">
              <div className="info-item">
                <span className="info-label">메시지 수:</span>
                <span className="info-value">{messages.length}</span>
              </div>
              <div className="info-item">
                <span className="info-label">사용자 메시지:</span>
                <span className="info-value">
                  {messages.filter(m => m.role === 'user').length}
                </span>
              </div>
              <div className="info-item">
                <span className="info-label">AI 응답:</span>
                <span className="info-value">
                  {messages.filter(m => m.role === 'assistant').length}
                </span>
              </div>
            </div>
          </div>

          <div className="divider"></div>

          <div className="info-section">
            <h3>ℹ️ 정보</h3>
            <p className="info-text">
              이것은 Streamlit 스타일의 채팅 인터페이스입니다. 
              메시지를 입력하고 Enter를 누르거나 전송 버튼을 클릭하세요.
            </p>
          </div>

          <div className="divider"></div>

          <div className="info-section">
            <button 
              className="clear-button"
              onClick={() => setMessages([
                { role: 'assistant', content: '안녕하세요! 무엇을 도와드릴까요?' }
              ])}
            >
              🔄 대화 초기화
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;