import React, { useState, useEffect, useRef } from 'react';
import './App.css';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

function App() {
  const [messages, setMessages] = useState<Message[]>([
    { 
      role: 'assistant', 
      content: '안녕하세요! 무엇을 도와드릴까요?', 
      timestamp: new Date() 
    }
  ]);
  const [userInput, setUserInput] = useState('');
  const [processing, setProcessing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!userInput.trim() || processing) return;

    // Add user message
    const userMessage: Message = {
      role: 'user',
      content: userInput,
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setUserInput('');
    setProcessing(true);

    // Simulate AI response (replace with actual API call)
    setTimeout(() => {
      const responses = [
        '흥미로운 질문이네요! 더 자세히 설명해 주실 수 있나요?',
        '좋은 생각입니다! 그것에 대해 더 알아보겠습니다.',
        '네, 이해했습니다. 도움이 되었길 바랍니다!',
        '그것은 정말 좋은 접근 방법입니다.',
        '더 궁금한 점이 있으시면 말씀해 주세요!'
      ];
      
      const assistantMessage: Message = {
        role: 'assistant',
        content: responses[Math.floor(Math.random() * responses.length)],
        timestamp: new Date()
      };
      
      setMessages(prev => [...prev, assistantMessage]);
      setProcessing(false);
    }, 1500);
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      const form = e.currentTarget.form;
      if (form) {
        form.requestSubmit();
      }
    }
  };

  const clearChat = () => {
    setMessages([
      { 
        role: 'assistant', 
        content: '안녕하세요! 무엇을 도와드릴까요?', 
        timestamp: new Date() 
      }
    ]);
    setUserInput('');
    setProcessing(false);
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <h1>💬 채팅 인터페이스</h1>
        <span className="version">v1.0</span>
      </header>

      {/* Main Layout */}
      <div className="main-layout">
        {/* Sidebar */}
        <aside className="sidebar">
          <div className="sidebar-content">
            <h2>채팅 설정</h2>
            
            <div className="sidebar-section">
              <h3>📊 통계</h3>
              <div className="stats-grid">
                <div className="stat-item">
                  <span className="stat-value">{messages.length}</span>
                  <span className="stat-label">총 메시지</span>
                </div>
                <div className="stat-item">
                  <span className="stat-value">
                    {messages.filter(m => m.role === 'user').length}
                  </span>
                  <span className="stat-label">사용자 메시지</span>
                </div>
                <div className="stat-item">
                  <span className="stat-value">
                    {messages.filter(m => m.role === 'assistant').length}
                  </span>
                  <span className="stat-label">AI 응답</span>
                </div>
              </div>
            </div>

            <div className="sidebar-section">
              <h3>⚙️ 옵션</h3>
              <button className="btn-secondary" onClick={clearChat}>
                🗑️ 채팅 초기화
              </button>
            </div>

            <div className="sidebar-section">
              <h3>ℹ️ 정보</h3>
              <p className="info-text">
                이 채팅 인터페이스는 Streamlit 스타일로 디자인되었습니다. 
                Enter 키를 눌러 메시지를 전송하세요.
              </p>
            </div>
          </div>
        </aside>

        {/* Chat Container */}
        <main className="chat-container">
          <div className="chat-messages">
            {messages.map((message, index) => (
              <div 
                key={index} 
                className={`message ${message.role}`}
              >
                <div className="message-header">
                  <span className="message-role">
                    {message.role === 'user' ? '👤 사용자' : '🤖 AI'}
                  </span>
                  <span className="message-time">
                    {message.timestamp.toLocaleTimeString('ko-KR', {
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </span>
                </div>
                <div className="message-content">
                  {message.content}
                </div>
              </div>
            ))}
            
            {processing && (
              <div className="message assistant">
                <div className="message-header">
                  <span className="message-role">🤖 AI</span>
                </div>
                <div className="message-content">
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>

          {/* Input Form */}
          <form className="chat-input-form" onSubmit={handleSubmit}>
            <div className="input-group">
              <input
                type="text"
                className="chat-input"
                placeholder="메시지를 입력하세요..."
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                onKeyDown={handleKeyPress}
                disabled={processing}
              />
              <button 
                type="submit" 
                className="btn-primary"
                disabled={!userInput.trim() || processing}
              >
                {processing ? '전송 중...' : '전송'}
              </button>
            </div>
          </form>
        </main>
      </div>
    </div>
  );
}

export default App;