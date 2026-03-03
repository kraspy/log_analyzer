/**
 * AI page — summary generation and interactive SSE chat.
 * @module AIPage
 */
import { useState, useRef, useEffect } from 'react';
import { Typography, Card, Button, Input, Alert, Space, Tag } from 'antd';
import { RobotOutlined, SendOutlined, BulbOutlined } from '@ant-design/icons';
import { generateSummary, chatWithAI, getAIStatus } from '../api/client';

const { Text } = Typography;
const { TextArea } = Input;

/**
 * AI Analysis component — summary + interactive chat.
 *
 * Two modes:
 * 1. Summary — one-shot AI analysis
 * 2. Chat — streaming conversation via SSE
 */
export function AIAnalysis({ logFileId }: { logFileId: number }) {
    const [aiAvailable, setAiAvailable] = useState<boolean | null>(null);
    const [summary, setSummary] = useState<string | null>(null);
    const [summaryLoading, setSummaryLoading] = useState(false);
    const [messages, setMessages] = useState<Array<{ role: 'user' | 'ai'; content: string }>>([]);
    const [question, setQuestion] = useState('');
    const [streaming, setStreaming] = useState(false);
    const chatEndRef = useRef<HTMLDivElement>(null);

    // Check AI availability on mount
    useEffect(() => {
        getAIStatus().then((s) => setAiAvailable(s.available)).catch(() => setAiAvailable(false));
    }, []);

    // Auto-scroll chat
    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleGenerateSummary = async () => {
        setSummaryLoading(true);
        try {
            const result = await generateSummary(logFileId);
            setSummary(result.summary);
        } catch (err) {
            setSummary(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
        } finally {
            setSummaryLoading(false);
        }
    };

    const handleSendMessage = async () => {
        if (!question.trim() || streaming) return;

        const userMessage = question.trim();
        setQuestion('');
        setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
        setStreaming(true);

        // Add empty AI message that we'll build up via streaming
        setMessages((prev) => [...prev, { role: 'ai', content: '' }]);

        await chatWithAI(
            logFileId,
            userMessage,
            (chunk) => {
                // Append each chunk to the last AI message
                setMessages((prev) => {
                    const updated = [...prev];
                    const last = updated[updated.length - 1];
                    if (last.role === 'ai') {
                        updated[updated.length - 1] = {
                            ...last,
                            content: last.content + chunk,
                        };
                    }
                    return updated;
                });
            },
            () => setStreaming(false),
            (error) => {
                setMessages((prev) => {
                    const updated = [...prev];
                    const last = updated[updated.length - 1];
                    if (last.role === 'ai') {
                        updated[updated.length - 1] = {
                            ...last,
                            content: `Error: ${error.message}`,
                        };
                    }
                    return updated;
                });
                setStreaming(false);
            },
        );
    };

    if (aiAvailable === false) {
        return (
            <Alert
                type="warning"
                showIcon
                message="AI Analysis Unavailable"
                description="Configure OPENAI_API_KEY or DEEPSEEK_API_KEY in environment variables to enable AI features."
            />
        );
    }

    return (
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            {/* Summary section */}
            <Card
                title={<><BulbOutlined /> AI Summary & Anomaly Detection</>}
                extra={
                    <Button
                        type="primary"
                        onClick={handleGenerateSummary}
                        loading={summaryLoading}
                        icon={<RobotOutlined />}
                    >
                        Generate Summary
                    </Button>
                }
            >
                {summary ? (
                    <div style={{ whiteSpace: 'pre-wrap' }}>{summary}</div>
                ) : (
                    <Text type="secondary">
                        Click "Generate Summary" to get AI-powered analysis of your logs.
                    </Text>
                )}
            </Card>

            {/* Chat section */}
            <Card title={<><RobotOutlined /> Chat with AI</>}>
                <div
                    style={{
                        maxHeight: 400,
                        overflowY: 'auto',
                        marginBottom: 16,
                        padding: 8,
                        border: '1px solid #f0f0f0',
                        borderRadius: 8,
                        backgroundColor: '#fafafa',
                    }}
                >
                    {messages.length === 0 && (
                        <Text type="secondary" style={{ display: 'block', textAlign: 'center', padding: 24 }}>
                            Ask a question about your logs...
                        </Text>
                    )}
                    {messages.map((msg, i) => (
                        <div
                            key={i}
                            style={{
                                display: 'flex',
                                justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                                marginBottom: 8,
                            }}
                        >
                            <Tag
                                color={msg.role === 'user' ? 'blue' : 'green'}
                                style={{
                                    maxWidth: '80%',
                                    whiteSpace: 'pre-wrap',
                                    padding: '8px 12px',
                                    fontSize: 14,
                                    lineHeight: 1.5,
                                }}
                            >
                                {msg.content || (streaming && i === messages.length - 1 ? '...' : '')}
                            </Tag>
                        </div>
                    ))}
                    <div ref={chatEndRef} />
                </div>

                <Space.Compact style={{ width: '100%' }}>
                    <TextArea
                        value={question}
                        onChange={(e) => setQuestion(e.target.value)}
                        placeholder="e.g. What endpoints have the highest error rate?"
                        autoSize={{ minRows: 1, maxRows: 3 }}
                        onPressEnter={(e) => {
                            if (!e.shiftKey) {
                                e.preventDefault();
                                handleSendMessage();
                            }
                        }}
                        disabled={streaming}
                    />
                    <Button
                        type="primary"
                        icon={<SendOutlined />}
                        onClick={handleSendMessage}
                        loading={streaming}
                    >
                        Send
                    </Button>
                </Space.Compact>
            </Card>
        </Space>
    );
}
