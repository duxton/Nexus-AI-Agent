'use client';

import { useState, useRef, useEffect } from 'react';

interface Message {
  id: string;
  text: string;
  isUser: boolean;
  timestamp: Date;
  intent?: string;
  action_type?: string;
  reasoning?: string;
  tools_used?: string[];
  rag_sources?: string[];
  planning_steps?: string[];
}

interface ChatResponse {
  response: string;
  session_id: string;
  turn_number: number;
  intent?: string;
  action_type?: string;
  reasoning?: string;
  tools_used?: string[];
  rag_sources?: string[];
  planning_steps?: string[];
}

const generateSessionId = (): string => {
  return 'session-' + Date.now() + '-' + Math.random().toString(36).substring(2, 11);
};

const STORAGE_KEY = 'chat-conversation';

const loadFromStorage = () => {
  if (typeof window === 'undefined') return null;
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      return {
        messages: parsed.messages.map((msg: Message) => ({
          ...msg,
          timestamp: new Date(msg.timestamp)
        })),
        sessionId: parsed.sessionId
      };
    }
  } catch (error) {
    console.error('Error loading from localStorage:', error);
  }
  return null;
};

const saveToStorage = (messages: Message[], sessionId: string) => {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ messages, sessionId }));
  } catch (error) {
    console.error('Error saving to localStorage:', error);
  }
};

export default function ChatBot() {
  const [messages, setMessages] = useState<Message[]>(() => {
    const stored = loadFromStorage();
    return stored?.messages || [
      {
        id: '1',
        text: 'Hello! I\'m your outlet assistant. How can I help you find information about our locations?',
        isUser: false,
        timestamp: new Date()
      }
    ];
  });
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>(() => {
    const stored = loadFromStorage();
    return stored?.sessionId || generateSessionId();
  });
  const [error, setError] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'online' | 'offline' | 'connecting'>('online');
  const [retryCount, setRetryCount] = useState(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [quickActions] = useState([
    { command: '/calc', description: 'Calculator - perform mathematical calculations' },
    { command: '/products', description: 'Product search - find products and inventory' },
    { command: '/outlets', description: 'Outlet finder - locate store locations' },
    { command: '/reset', description: 'Reset conversation - start fresh' }
  ]);
  const [showQuickActions, setShowQuickActions] = useState(false);
  const [filteredActions, setFilteredActions] = useState(quickActions);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    saveToStorage(messages, sessionId);
  }, [messages, sessionId]);

  useEffect(() => {
    const lastWord = inputValue.split(' ').pop() || '';
    if (inputValue.startsWith('/')) {
      const filtered = quickActions.filter(action =>
        action.command.toLowerCase().includes(lastWord.toLowerCase())
      );
      setFilteredActions(filtered);
      setShowQuickActions(filtered.length > 0 && inputValue !== lastWord);
    } else {
      setShowQuickActions(false);
    }
  }, [inputValue, quickActions]);

  const callProductsAPI = async (query: string = 'products', maxResults: number = 5): Promise<any> => {
    setConnectionStatus('connecting');

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000);

      const encodedQuery = encodeURIComponent(query);
      const response = await fetch(`http://localhost:8000/products?query=${encodedQuery}&max_results=${maxResults}`, {
        method: 'GET',
        headers: {
          'accept': 'application/json',
        },
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setConnectionStatus('online');
      setRetryCount(0);
      return data;

    } catch (error: unknown) {
      setConnectionStatus('offline');
      throw error;
    }
  };

  const callOutletsAPI = async (query: string = 'outlets'): Promise<any> => {
    setConnectionStatus('connecting');

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000);

      const encodedQuery = encodeURIComponent(query);
      const response = await fetch(`http://localhost:8000/outlets/${encodedQuery}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setConnectionStatus('online');
      setRetryCount(0);
      return data;

    } catch (error: unknown) {
      setConnectionStatus('offline');
      throw error;
    }
  };

  const sendMessageToAPI = async (message: string, attempt: number = 1): Promise<ChatResponse> => {
    setConnectionStatus('connecting');

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000);

      const response = await fetch('http://127.0.0.1:8000/chat/agentic/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: message,
          session_id: sessionId
        }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: ChatResponse = await response.json();

      if (data.session_id && data.session_id !== sessionId) {
        setSessionId(data.session_id);
      }

      setConnectionStatus('online');
      setRetryCount(0);
      return data;

    } catch (error: unknown) {
      setConnectionStatus('offline');

      const err = error as Error;
      if (err.name === 'AbortError') {
        throw new Error('Request timed out. The backend server may be overloaded.');
      }

      if (attempt < 3 && (err.message.includes('fetch') || err.message.includes('network'))) {
        console.log(`Retrying request (attempt ${attempt + 1}/3)...`);
        await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
        return sendMessageToAPI(message, attempt + 1);
      }

      throw error;
    }
  };

  const handleReset = () => {
    const resetMessages = [
      {
        id: '1',
        text: 'Hello! I\'m your outlet assistant. How can I help you find information about our locations?',
        isUser: false,
        timestamp: new Date()
      }
    ];
    setMessages(resetMessages);
    const newSessionId = generateSessionId();
    setSessionId(newSessionId);
    saveToStorage(resetMessages, newSessionId);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!inputValue.trim()) return;

    if (inputValue.trim() === '/reset') {
      handleReset();
      setInputValue('');
      return;
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputValue,
      isUser: true,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    const messageText = inputValue;
    setInputValue('');
    setIsLoading(true);
    setError(null);

    try {
      // Check if it's a /products command
      if (messageText.trim().startsWith('/products')) {
        const queryPart = messageText.trim().substring('/products'.length).trim();
        const searchQuery = queryPart || 'products';

        const productsResponse = await callProductsAPI(searchQuery, 5);

        let responseText = '';

        // Include the answer if available
        if (productsResponse.answer) {
          responseText += `${productsResponse.answer}\n\n`;
        }

        responseText += 'Here are the product search results:\n\n';

        if (productsResponse.products && productsResponse.products.length > 0) {
          productsResponse.products.forEach((product: any, index: number) => {
            responseText += `${index + 1}. **${product.name || product.title || 'Product'}**\n`;
            if (product.price) responseText += `   💰 ${product.price}\n`;
            if (product.description) responseText += `   📝 ${product.description}\n`;
            if (product.category) responseText += `   🏷️ ${product.category}\n`;
            if (product.material) responseText += `   🔧 ${product.material}\n`;
            if (product.capacity) responseText += `   📏 ${product.capacity}\n`;
            if (product.features && Array.isArray(product.features)) {
              responseText += `   ✨ ${product.features.join(', ')}\n`;
            }
            if (product.relevance_score) {
              responseText += `   📊 Relevance: ${Math.round(product.relevance_score * 100)}%\n`;
            }
            responseText += '\n';
          });

          if (productsResponse.total_found && productsResponse.total_found > productsResponse.products.length) {
            responseText += `\nShowing ${productsResponse.products.length} of ${productsResponse.total_found} results.`;
          }
        } else {
          responseText += 'No products found for your search query.';
        }

        const botResponse: Message = {
          id: (Date.now() + 1).toString(),
          text: responseText,
          isUser: false,
          timestamp: new Date(),
          intent: 'product_search',
          action_type: 'products_api_call',
          tools_used: ['products_search_api']
        };

        setMessages(prev => [...prev, botResponse]);
        setError(null);
      }
      // Check if it's an /outlets command
      else if (messageText.trim().startsWith('/outlets')) {
        const locationPart = messageText.trim().substring('/outlets'.length).trim();
        const searchLocation = locationPart || 'Kuala Lumpur'; // Default to KL if no location specified

        const outletsResponse = await callOutletsAPI(searchLocation);

        let responseText = `Here are the outlets in ${searchLocation}:\n\n`;

        if (outletsResponse && Array.isArray(outletsResponse) && outletsResponse.length > 0) {
          outletsResponse.forEach((outlet: any, index: number) => {
            responseText += `${index + 1}. **${outlet.name || outlet.outlet_name || 'Outlet'}**\n`;
            if (outlet.address || outlet.location) {
              const address = outlet.address || outlet.location;
              responseText += `   📍 ${address}\n`;
            }
            if (outlet.phone || outlet.phone_number) {
              const phone = outlet.phone || outlet.phone_number;
              responseText += `   📞 ${phone}\n`;
            }
            if (outlet.hours || outlet.operating_hours || outlet.opening_hours) {
              const hours = outlet.hours || outlet.operating_hours || outlet.opening_hours;
              responseText += `   🕒 ${hours}\n`;
            }
            if (outlet.features || outlet.amenities || outlet.services) {
              const features = outlet.features || outlet.amenities || outlet.services;
              const featureText = Array.isArray(features) ? features.join(', ') : features;
              responseText += `   ✨ ${featureText}\n`;
            }
            responseText += '\n';
          });
        } else if (outletsResponse && outletsResponse.outlets && Array.isArray(outletsResponse.outlets)) {
          // Handle case where outlets are nested in an 'outlets' property
          outletsResponse.outlets.forEach((outlet: any, index: number) => {
            responseText += `${index + 1}. **${outlet.name || outlet.outlet_name || 'Outlet'}**\n`;
            if (outlet.address || outlet.location) {
              const address = outlet.address || outlet.location;
              responseText += `   📍 ${address}\n`;
            }
            if (outlet.phone || outlet.phone_number) {
              const phone = outlet.phone || outlet.phone_number;
              responseText += `   📞 ${phone}\n`;
            }
            if (outlet.hours || outlet.operating_hours || outlet.opening_hours) {
              const hours = outlet.hours || outlet.operating_hours || outlet.opening_hours;
              responseText += `   🕒 ${hours}\n`;
            }
            if (outlet.features || outlet.amenities || outlet.services) {
              const features = outlet.features || outlet.amenities || outlet.services;
              const featureText = Array.isArray(features) ? features.join(', ') : features;
              responseText += `   ✨ ${featureText}\n`;
            }
            responseText += '\n';
          });
        } else {
          responseText += `No outlets found in ${searchLocation}. Try searching for other locations like "Selangor", "Penang", or "Johor".`;
        }

        const botResponse: Message = {
          id: (Date.now() + 1).toString(),
          text: responseText,
          isUser: false,
          timestamp: new Date(),
          intent: 'outlet_search',
          action_type: 'outlets_api_call',
          tools_used: ['outlets_location_api']
        };

        setMessages(prev => [...prev, botResponse]);
        setError(null);
      } else {
        // Normal chat API call
        const apiResponse = await sendMessageToAPI(messageText);

        const botResponse: Message = {
          id: (Date.now() + 1).toString(),
          text: apiResponse.response,
          isUser: false,
          timestamp: new Date(),
          intent: apiResponse.intent,
          action_type: apiResponse.action_type,
          reasoning: apiResponse.reasoning,
          tools_used: apiResponse.tools_used,
          rag_sources: apiResponse.rag_sources,
          planning_steps: apiResponse.planning_steps
        };

        setMessages(prev => [...prev, botResponse]);
        setError(null);
      }
    } catch (error: unknown) {
      console.error('Error sending message:', error);
      const err = error as Error;
      const currentRetry = retryCount + 1;
      setRetryCount(currentRetry);

      let errorText = 'I\'m having trouble processing your request. ';
      let systemError = 'Failed to send message. ';

      if (err.message.includes('timed out')) {
        errorText += 'The request timed out. The server might be busy processing other requests.';
        systemError += 'Request timed out.';
      } else if (err.message.includes('HTTP error! status: 500')) {
        errorText += 'There was an internal server error. Please try again.';
        systemError += 'Internal server error (500).';
      } else if (err.message.includes('HTTP error! status: 404')) {
        errorText += 'The chat endpoint was not found. Please check if the correct backend is running.';
        systemError += 'Chat endpoint not found (404).';
      } else if (err.message.includes('fetch')) {
        errorText += 'Please make sure the backend server is running on http://localhost:8000';
        systemError += 'Backend server connection failed.';
      } else {
        errorText += 'Please try again or check your connection.';
        systemError += err.message;
      }

      if (currentRetry > 1) {
        errorText += ` (Attempt ${currentRetry})`;
      }

      setError(systemError);

      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: errorText,
        isUser: false,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
      <div className="flex flex-col w-full max-w-4xl mx-auto bg-white dark:bg-gray-800 shadow-lg">
        <header className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h1 className="text-xl font-semibold text-gray-800 dark:text-white">
              Outlet Assistant
            </h1>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Session: {sessionId.split('-').slice(-1)[0]}
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${
              connectionStatus === 'online' ? 'bg-green-500' :
              connectionStatus === 'connecting' ? 'bg-yellow-500 animate-pulse' :
              'bg-red-500'
            }`}></div>
            <span className="text-sm text-gray-600 dark:text-gray-300 capitalize">
              {connectionStatus === 'connecting' ? 'Connecting...' : connectionStatus}
            </span>
            {retryCount > 0 && (
              <span className="text-xs text-orange-600 dark:text-orange-400">
                (Retry {retryCount})
              </span>
            )}
          </div>
        </header>

        {error && (
          <div className="p-3 bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800">
            <p className="text-sm text-red-600 dark:text-red-400">
              {error}
            </p>
          </div>
        )}

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex items-start space-x-3 ${message.isUser ? 'justify-end' : 'justify-start'}`}
            >
              {!message.isUser && (
                <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white text-sm font-bold">
                  AI
                </div>
              )}
              <div
                className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                  message.isUser
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-white'
                }`}
              >
                <p className="text-sm whitespace-pre-wrap">{message.text}</p>
                {!message.isUser && (message.intent || message.action_type || message.reasoning || message.tools_used || message.rag_sources || message.planning_steps) && (
                  <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-600 space-y-1">
                    {message.intent && (
                      <div className="flex items-center text-xs">
                        <span className="font-medium text-blue-600 dark:text-blue-400 mr-2">Intent:</span>
                        <span className="opacity-80">{message.intent}</span>
                      </div>
                    )}
                    {message.action_type && (
                      <div className="flex items-center text-xs">
                        <span className="font-medium text-green-600 dark:text-green-400 mr-2">Action:</span>
                        <span className="opacity-80">{message.action_type}</span>
                      </div>
                    )}
                    {message.reasoning && (
                      <div className="text-xs">
                        <span className="font-medium text-purple-600 dark:text-purple-400">Reasoning:</span>
                        <p className="opacity-80 mt-1">{message.reasoning}</p>
                      </div>
                    )}
                    {message.tools_used && message.tools_used.length > 0 && (
                      <div className="text-xs">
                        <span className="font-medium text-orange-600 dark:text-orange-400">Tools Used:</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {message.tools_used.map((tool, idx) => (
                            <span key={idx} className="bg-orange-100 dark:bg-orange-900 px-2 py-0.5 rounded text-xs">{tool}</span>
                          ))}
                        </div>
                      </div>
                    )}
                    {message.rag_sources && message.rag_sources.length > 0 && (
                      <div className="text-xs">
                        <span className="font-medium text-teal-600 dark:text-teal-400">RAG Sources:</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {message.rag_sources.map((source, idx) => (
                            <span key={idx} className="bg-teal-100 dark:bg-teal-900 px-2 py-0.5 rounded text-xs">{source}</span>
                          ))}
                        </div>
                      </div>
                    )}
                    {message.planning_steps && message.planning_steps.length > 0 && (
                      <div className="text-xs">
                        <span className="font-medium text-indigo-600 dark:text-indigo-400">Planning Steps:</span>
                        <ol className="list-decimal list-inside opacity-80 mt-1 space-y-0.5">
                          {message.planning_steps.map((step, idx) => (
                            <li key={idx}>{step}</li>
                          ))}
                        </ol>
                      </div>
                    )}
                  </div>
                )}

                <p className="text-xs mt-1 opacity-70">
                  {message.timestamp.toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </p>
              </div>
              {message.isUser && (
                <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-br from-green-500 to-blue-500 rounded-full flex items-center justify-center text-white text-sm font-bold">
                  U
                </div>
              )}
            </div>
          ))}

          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 dark:bg-gray-700 px-4 py-2 rounded-lg">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <form onSubmit={handleSubmit} className="p-4 border-t border-gray-200 dark:border-gray-700">
          <div className="relative">
            {showQuickActions && filteredActions.length > 0 && (
              <div className="absolute bottom-full mb-2 w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                {filteredActions.map((action) => (
                  <button
                    key={action.command}
                    type="button"
                    onClick={() => {
                      setInputValue(action.command + ' ');
                      setShowQuickActions(false);
                    }}
                    className="w-full px-4 py-2 text-left hover:bg-gray-100 dark:hover:bg-gray-700 border-b border-gray-100 dark:border-gray-600 last:border-b-0"
                  >
                    <div className="font-medium text-sm text-gray-800 dark:text-white">{action.command}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">{action.description}</div>
                  </button>
                ))}
              </div>
            )}
            <div className="flex space-x-2">
              <div className="flex-1 relative">
                <textarea
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSubmit(e);
                    }
                  }}
                  placeholder="Type your message... (Shift+Enter for newline)"
                  disabled={isLoading}
                  rows={inputValue.split('\n').length}
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white disabled:opacity-50 resize-none min-h-[42px] max-h-32 overflow-y-auto"
                />
              </div>
              <button
                type="submit"
                disabled={isLoading || !inputValue.trim()}
                className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors self-end"
              >
                Send
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
