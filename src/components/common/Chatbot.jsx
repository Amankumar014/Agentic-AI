import React, { useState, useRef, useEffect } from 'react';
import { askChatbot, getChatbotStatus, formatErrorMessage } from '../../services/ApiService';

/**
 * Chatbot Component - AI-powered baby care assistant
 * Features a cute baby icon and provides helpful responses
 */
function Chatbot() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      id: 1,
      text: "Hi! I'm Lalla Care Assistant 👶 How can I help you today?",
      sender: 'bot',
      timestamp: new Date()
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [chatbotReady, setChatbotReady] = useState(true);
  const [statusMessage, setStatusMessage] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Focus input when chat opens and check chatbot status
  useEffect(() => {
    if (isOpen) {
      if (inputRef.current) {
      inputRef.current.focus();
      }
      checkChatbotStatus();
    }
  }, [isOpen]);

  // Check if chatbot is ready
  const checkChatbotStatus = async () => {
    try {
      const status = await getChatbotStatus();
      if (status.status === 'ready' && status.index_exists) {
        setChatbotReady(true);
        setStatusMessage('');
      } else {
        setChatbotReady(false);
        setStatusMessage(status.message || 'Chatbot is initializing. Please try again later.');
      }
    } catch (error) {
      console.error('Error checking chatbot status:', error);
      setChatbotReady(false);
      setStatusMessage('Unable to connect to chatbot service.');
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const toggleChat = () => {
    setIsOpen(!isOpen);
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    
    if (!inputMessage.trim()) return;
    if (!chatbotReady) return;

    const questionText = inputMessage.trim();

    // Validate question length
    if (questionText.length > 500) {
      const errorMessage = {
        id: Date.now(),
        text: "❌ Question is too long. Please keep it under 500 characters.",
        sender: 'bot',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
      return;
    }

    // Add user message
    const userMessage = {
      id: Date.now(),
      text: questionText,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsTyping(true);

    // Call backend API
    try {
      const response = await askChatbot(questionText);
      
      // Format bot response with sources if available
      let botText = response.answer;
      
      if (response.sources && response.sources.length > 0) {
        botText += '\n\n📚 Sources: ';
        const sourceTexts = response.sources.slice(0, 3).map(source => {
          if (source.document_name && source.page) {
            return `${source.document_name} (p.${source.page})`;
          }
          return source.document_name || 'Document';
        });
        botText += sourceTexts.join(', ');
      }

      const botMessage = {
        id: Date.now() + 1,
        text: botText,
        sender: 'bot',
        timestamp: new Date(),
        sources: response.sources,
        chunks_found: response.chunks_found
      };
      
      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      console.error('Error asking chatbot:', error);
      const errorMessage = {
        id: Date.now() + 1,
        text: `❌ ${formatErrorMessage(error)}`,
        sender: 'bot',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };


  const quickQuestions = [
    { id: 1, text: "Sleep tips", icon: "😴" },
    { id: 2, text: "Crying causes", icon: "😢" },
    { id: 3, text: "Feeding schedule", icon: "🍼" },
    { id: 4, text: "Temperature check", icon: "🌡️" }
  ];

  const handleQuickQuestion = (question) => {
    if (!chatbotReady) return;
    setInputMessage(question);
    // Trigger send after a brief delay
    setTimeout(() => {
      const event = { preventDefault: () => {} };
      handleSendMessage(event);
    }, 100);
  };

  return (
    <>
      {/* Chat Window */}
      <div
        className={`fixed bottom-24 right-6 w-96 bg-white rounded-3xl shadow-2xl transition-all duration-300 transform z-50 ${
          isOpen ? 'scale-100 opacity-100' : 'scale-95 opacity-0 pointer-events-none'
        }`}
        style={{ maxHeight: '600px', height: '80vh' }}
      >
        {/* Header */}
        <div className="bg-gradient-to-r from-primary-500 to-primary-600 text-white p-5 rounded-t-3xl flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center text-2xl shadow-lg">
              👶
            </div>
            <div>
              <h3 className="font-bold text-lg">Lalla Care Assistant</h3>
              <p className="text-xs text-primary-100">
                {chatbotReady ? 'Always here to help' : 'Initializing...'}
              </p>
            </div>
          </div>
          <button
            onClick={toggleChat}
            className="w-8 h-8 rounded-full bg-white/20 hover:bg-white/30 transition-colors flex items-center justify-center"
          >
            <span className="text-xl">×</span>
          </button>
        </div>

        {/* Status Message */}
        {!chatbotReady && statusMessage && (
          <div className="px-5 pt-4 pb-2">
            <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-3 text-xs text-yellow-800">
              ⚠️ {statusMessage}
            </div>
          </div>
        )}

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4" style={{ height: 'calc(80vh - 220px)' }}>
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                  message.sender === 'user'
                    ? 'bg-primary-500 text-white'
                    : 'bg-slate-100 text-slate-800'
                }`}
              >
                <p className="text-sm leading-relaxed">{message.text}</p>
                <p
                  className={`text-xs mt-1 ${
                    message.sender === 'user' ? 'text-primary-100' : 'text-slate-500'
                  }`}
                >
                  {message.timestamp.toLocaleTimeString('en-US', {
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </p>
              </div>
            </div>
          ))}

          {/* Typing Indicator */}
          {isTyping && (
            <div className="flex justify-start">
              <div className="bg-slate-100 rounded-2xl px-4 py-3">
                <div className="flex space-x-2">
                  <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
              </div>
            </div>
          )}

          {/* Quick Questions (shown when chat is empty or few messages) */}
          {messages.length <= 2 && !isTyping && (
            <div className="space-y-2 pt-2">
              <p className="text-xs text-slate-500 font-semibold uppercase tracking-wide">
                Quick Questions:
              </p>
              <div className="grid grid-cols-2 gap-2">
                {quickQuestions.map((q) => (
                  <button
                    key={q.id}
                    onClick={() => handleQuickQuestion(q.text)}
                    className="p-3 bg-slate-50 hover:bg-slate-100 rounded-xl text-left transition-colors border border-slate-200"
                  >
                    <span className="text-lg block mb-1">{q.icon}</span>
                    <span className="text-xs text-slate-700 font-medium">{q.text}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <form onSubmit={handleSendMessage} className="p-4 border-t border-slate-200">
          <div className="flex items-center space-x-2">
            <input
              ref={inputRef}
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder={chatbotReady ? "Type your question..." : "Chatbot is initializing..."}
              disabled={!chatbotReady}
              className="flex-1 px-4 py-3 rounded-2xl bg-slate-100 text-slate-800 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <button
              type="submit"
              disabled={!inputMessage.trim() || !chatbotReady}
              className="w-12 h-12 rounded-2xl bg-primary-500 text-white hover:bg-primary-600 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center shadow-lg"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                />
              </svg>
            </button>
          </div>
        </form>
      </div>

      {/* Floating Button with 3D Animation */}
      <div className="fixed bottom-6 right-6 z-50">
        {/* Animated pulse rings */}
        {!isOpen && (
          <>
            <div className="absolute inset-0 w-20 h-20 bg-primary-400 rounded-full chatbot-pulse-ring opacity-20"></div>
            <div className="absolute inset-0 w-20 h-20 bg-primary-300 rounded-full chatbot-pulse-ring opacity-10" style={{ animationDelay: '0.5s' }}></div>
          </>
        )}
        
        <button
          onClick={toggleChat}
          className="relative w-20 h-20 bg-gradient-to-br from-primary-500 to-primary-600 text-white rounded-full shadow-2xl flex items-center justify-center group chatbot-wiggle-bulge chatbot-hover-grow overflow-hidden"
          style={{
            boxShadow: '0 10px 30px rgba(74, 145, 134, 0.4), 0 0 0 3px rgba(74, 145, 134, 0.1)'
          }}
        >
          {/* 3D Shine Effect */}
          <div className="absolute inset-0 bg-gradient-to-br from-white/30 to-transparent rounded-full"></div>
          
          {/* Icon Container */}
          <div className="relative z-10 chatbot-icon-3d">
            {isOpen ? (
              <span className="text-4xl font-bold">×</span>
            ) : (
              <span className="chatbot-baby-emoji text-4xl">👶</span>
            )}
          </div>
          
          {/* Notification Pulse */}
          {!isOpen && (
            <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full z-20">
              <span className="absolute inset-0 bg-red-500 rounded-full animate-ping"></span>
              <span className="relative block w-4 h-4 bg-red-500 rounded-full"></span>
            </span>
          )}
          
          {/* Tooltip */}
          <div className="absolute bottom-full right-0 mb-3 px-4 py-2 bg-slate-800 text-white text-xs rounded-xl opacity-0 group-hover:opacity-100 transition-all duration-300 whitespace-nowrap shadow-xl transform group-hover:translate-y-0 translate-y-2">
            <div className="font-semibold">{isOpen ? 'Close Chat' : '👋 Chat with Lalla Care'}</div>
            {!isOpen && <div className="text-slate-300 text-[10px] mt-0.5">I'm here to help!</div>}
            {/* Tooltip arrow */}
            <div className="absolute top-full right-4 w-0 h-0 border-l-4 border-r-4 border-t-4 border-l-transparent border-r-transparent border-t-slate-800"></div>
          </div>
        </button>
      </div>
    </>
  );
}

export default Chatbot;

