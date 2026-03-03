/**
 * Upload page — file upload with format selection and preview.
 * @module UploadPage
 */
import {
    Typography, Upload, Card, Select, Space, Alert, App, Button,
    Tag, Descriptions, Spin,
} from 'antd';
import {
    FileTextOutlined, FileZipOutlined, CheckCircleOutlined,
    CloseCircleOutlined, CloudUploadOutlined,
} from '@ant-design/icons';
import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router';
import { uploadLogFile, previewLines, type PreviewResult } from '../api/client';

const { Title, Text, Paragraph } = Typography;
const { Dragger } = Upload;

/** Maximum upload size in bytes (must match nginx client_max_body_size) */
const MAX_FILE_SIZE = 200 * 1024 * 1024; // 200 MB
const MAX_FILE_SIZE_LABEL = '200 MB';
const ACCEPTED_EXTENSIONS = ['.log', '.txt', '.gz'];

/**
 * Smart Upload page — two-step flow:
 *
 * Step 1: Select file → read first 3 lines → preview them
 *         + call POST /api/logs/preview to test parsing
 * Step 2: User sees parse results, picks format, clicks Upload
 *
 * For .gz files: skip preview (can't decompress client-side)
 */
export function UploadPage() {
    const [format, setFormat] = useState('combined');
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [rawLines, setRawLines] = useState<string[]>([]);
    const [previewResults, setPreviewResults] = useState<PreviewResult[]>([]);
    const [previewLoading, setPreviewLoading] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [isCompressed, setIsCompressed] = useState(false);
    const navigate = useNavigate();
    const { message } = App.useApp();

    /** Read first 3 lines from file using FileReader */
    const readPreview = useCallback((file: File) => {
        const reader = new FileReader();
        reader.onload = async (e) => {
            const text = e.target?.result as string;
            const lines = text.split('\n').filter((l) => l.trim()).slice(0, 3);
            setRawLines(lines);

            // Call backend to test-parse these lines
            setPreviewLoading(true);
            try {
                const { results } = await previewLines(lines, format);
                setPreviewResults(results);
            } catch {
                message.error('Failed to preview lines');
            } finally {
                setPreviewLoading(false);
            }
        };
        // Read first 8KB — enough for 3 lines of any reasonable log
        reader.readAsText(file.slice(0, 8192));
    }, [format, message]);

    /** Re-run preview when format changes */
    const handleFormatChange = useCallback(async (newFormat: string) => {
        setFormat(newFormat);
        if (rawLines.length > 0) {
            setPreviewLoading(true);
            try {
                const { results } = await previewLines(rawLines, newFormat);
                setPreviewResults(results);
            } catch {
                message.error('Failed to preview lines');
            } finally {
                setPreviewLoading(false);
            }
        }
    }, [rawLines, message]);

    /** Client-side validation before file selection */
    const beforeUpload = (file: File): boolean | string => {
        const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
        if (!ACCEPTED_EXTENSIONS.includes(ext)) {
            message.error(`Unsupported type "${ext}". Allowed: ${ACCEPTED_EXTENSIONS.join(', ')}`);
            return Upload.LIST_IGNORE;
        }
        if (file.size > MAX_FILE_SIZE) {
            const sizeMB = (file.size / 1024 / 1024).toFixed(1);
            message.error(`File too large (${sizeMB} MB). Max: ${MAX_FILE_SIZE_LABEL}`);
            return Upload.LIST_IGNORE;
        }

        // Set selected file (don't upload yet)
        setSelectedFile(file);
        const compressed = ext === '.gz';
        setIsCompressed(compressed);

        if (!compressed) {
            readPreview(file);
        } else {
            setRawLines([]);
            setPreviewResults([]);
        }

        // Return false to prevent auto-upload
        return false;
    };

    /** Step 2: Upload the file */
    const handleUpload = async () => {
        if (!selectedFile) return;
        setUploading(true);
        try {
            const result = await uploadLogFile(selectedFile, format);
            message.success(
                `Parsed ${result.parsed_lines.toLocaleString()} / ${result.total_lines.toLocaleString()} lines`,
                5,
            );
            setTimeout(() => navigate(`/report/${result.log_file_id}`), 1200);
        } catch (err) {
            const error = err instanceof Error ? err : new Error(String(err));
            message.error(error.message, 6);
        } finally {
            setUploading(false);
        }
    };

    /** Reset state */
    const handleReset = () => {
        setSelectedFile(null);
        setRawLines([]);
        setPreviewResults([]);
        setIsCompressed(false);
    };

    const parsedOk = previewResults.filter((r) => r.parsed).length;
    const parsedFail = previewResults.filter((r) => !r.parsed).length;

    return (
        <div>
            <Title level={3}>Upload Log Files</Title>

            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                {/* Constraints info */}
                <Alert
                    type="info"
                    showIcon
                    message="Upload requirements"
                    description={
                        <ul style={{ margin: 0, paddingLeft: 20 }}>
                            <li>
                                <Text strong>Formats:</Text>{' '}
                                <Text code>.log</Text> <Text code>.txt</Text> <Text code>.gz</Text>{' '}
                                <Text type="secondary">(gzip auto-extracted)</Text>
                            </li>
                            <li><Text strong>Max size:</Text> {MAX_FILE_SIZE_LABEL}</li>
                            <li><Text strong>Duplicates:</Text> <Text type="secondary">rejected by SHA-256 hash</Text></li>
                        </ul>
                    }
                />

                {/* Format selector */}
                <Card
                    title={<Space><FileTextOutlined /><span>Log Format</span></Space>}
                    size="small"
                >
                    <Select
                        value={format}
                        onChange={handleFormatChange}
                        style={{ width: 240 }}
                        options={[
                            { value: 'combined', label: 'Combined (Nginx standard)' },
                        ]}
                    />
                </Card>

                {/* File drop zone — only shown when no file selected */}
                {!selectedFile && (
                    <Card>
                        <Dragger
                            name="file"
                            multiple={false}
                            accept={ACCEPTED_EXTENSIONS.join(',')}
                            maxCount={1}
                            beforeUpload={beforeUpload}
                            showUploadList={false}
                        >
                            <p className="ant-upload-drag-icon">
                                <FileZipOutlined style={{ fontSize: 48 }} />
                            </p>
                            <p className="ant-upload-text">
                                Click or drag a log file to this area
                            </p>
                            <p className="ant-upload-hint">
                                {ACCEPTED_EXTENSIONS.join(', ')} • Max {MAX_FILE_SIZE_LABEL}
                            </p>
                        </Dragger>
                    </Card>
                )}

                {/* Preview — shown after file selected */}
                {selectedFile && (
                    <>
                        {/* File info */}
                        <Card
                            title={
                                <Space>
                                    <FileTextOutlined />
                                    <span>{selectedFile.name}</span>
                                    <Text type="secondary">
                                        ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
                                    </Text>
                                </Space>
                            }
                            extra={
                                <Button size="small" onClick={handleReset}>
                                    Change file
                                </Button>
                            }
                        >
                            {isCompressed ? (
                                <Alert
                                    type="warning"
                                    showIcon
                                    message="Compressed file — preview unavailable"
                                    description="Gzip files will be decompressed on the server during upload."
                                />
                            ) : previewLoading ? (
                                <Spin tip="Analyzing..." />
                            ) : rawLines.length > 0 ? (
                                <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                                    {/* Parse stats */}
                                    <Space>
                                        <Tag color="blue">Preview: {rawLines.length} lines</Tag>
                                        {parsedOk > 0 && (
                                            <Tag icon={<CheckCircleOutlined />} color="success">
                                                {parsedOk} parsed
                                            </Tag>
                                        )}
                                        {parsedFail > 0 && (
                                            <Tag icon={<CloseCircleOutlined />} color="error">
                                                {parsedFail} failed
                                            </Tag>
                                        )}
                                    </Space>

                                    {/* Per-line results */}
                                    {rawLines.map((line, idx) => {
                                        const result = previewResults[idx];
                                        const parsed = result?.parsed ?? false;
                                        return (
                                            <Card
                                                key={idx}
                                                size="small"
                                                style={{
                                                    borderLeft: `3px solid ${parsed ? '#52c41a' : '#ff4d4f'}`,
                                                }}
                                            >
                                                <Space direction="vertical" style={{ width: '100%' }}>
                                                    <Space>
                                                        {parsed ? (
                                                            <Tag icon={<CheckCircleOutlined />} color="success">
                                                                Line {idx + 1}: Parsed OK
                                                            </Tag>
                                                        ) : (
                                                            <Tag icon={<CloseCircleOutlined />} color="error">
                                                                Line {idx + 1}: Parse Error
                                                            </Tag>
                                                        )}
                                                    </Space>
                                                    <Paragraph
                                                        code
                                                        ellipsis={{ rows: 2, expandable: true }}
                                                        style={{ margin: 0, fontSize: 12 }}
                                                    >
                                                        {line}
                                                    </Paragraph>
                                                    {result?.fields && (
                                                        <Descriptions size="small" column={3} bordered>
                                                            <Descriptions.Item label="IP">{result.fields.ip}</Descriptions.Item>
                                                            <Descriptions.Item label="Method">{result.fields.method}</Descriptions.Item>
                                                            <Descriptions.Item label="Status">{result.fields.status}</Descriptions.Item>
                                                            <Descriptions.Item label="Path" span={2}>{result.fields.path}</Descriptions.Item>
                                                            <Descriptions.Item label="Time">
                                                                {result.fields.response_time != null
                                                                    ? `${result.fields.response_time}s`
                                                                    : '—'
                                                                }
                                                            </Descriptions.Item>
                                                        </Descriptions>
                                                    )}
                                                </Space>
                                            </Card>
                                        );
                                    })}

                                    {parsedFail > 0 && parsedOk === 0 && (
                                        <Alert
                                            type="error"
                                            showIcon
                                            message="No lines could be parsed"
                                            description="Try changing the Log Format above, or check that the file contains valid Nginx logs."
                                        />
                                    )}
                                </Space>
                            ) : null}
                        </Card>

                        {/* Upload button */}
                        <Button
                            type="primary"
                            size="large"
                            icon={<CloudUploadOutlined />}
                            onClick={handleUpload}
                            loading={uploading}
                            block
                        >
                            Upload & Parse ({format})
                        </Button>
                    </>
                )}
            </Space>
        </div>
    );
}
