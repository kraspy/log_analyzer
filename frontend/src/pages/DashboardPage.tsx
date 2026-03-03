/**
 * Dashboard page — lists uploaded log files with stats and actions.
 * @module DashboardPage
 */
import { useCallback, useEffect, useState } from 'react';
import { Typography, Card, Table, Empty, Spin, Tag, Statistic, Row, Col, Button, Popconfirm, Space, App, Result } from 'antd';
import {
    FileTextOutlined, CheckCircleOutlined, WarningOutlined,
    DeleteOutlined, DownloadOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router';
import type { LogFile } from '../api/client';
import { listLogFiles, deleteLogFile, getExportCsvUrl } from '../api/client';

const { Title, Paragraph } = Typography;

/**
 * Dashboard page — lists uploaded files with key metrics.
 *
 * Features:
 * - Summary stat cards (responsive grid)
 * - File table with delete + CSV export actions
 * - Empty state when no files uploaded
 */
export function DashboardPage() {
    const [files, setFiles] = useState<LogFile[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const navigate = useNavigate();
    const { message } = App.useApp();

    const loadFiles = useCallback(() => {
        setLoading(true);
        listLogFiles()
            .then((data) => {
                setFiles(data.files);
                setLoading(false);
            })
            .catch((err) => {
                const msg = err.message || 'Failed to load files';
                setError(msg);
                message.error(msg);
                setLoading(false);
            });
    }, [message]);

    // Initial data fetch — setState in effect is intentional (data fetching pattern)
    // eslint-disable-next-line react-hooks/set-state-in-effect
    useEffect(() => { loadFiles(); }, [loadFiles]);

    const handleDelete = async (id: number, e?: React.MouseEvent) => {
        e?.stopPropagation(); // Don't navigate to report
        try {
            await deleteLogFile(id);
            message.success('File deleted');
            loadFiles(); // Refresh list
        } catch (err) {
            message.error(err instanceof Error ? err.message : 'Delete failed');
        }
    };

    const totalRequests = files.reduce((sum, f) => sum + f.parsed_lines, 0);
    const totalFiles = files.length;
    const totalErrors = files.reduce((sum, f) => sum + f.error_lines, 0);

    if (loading) return <Spin size="large" />;

    return (
        <div>
            <Title level={3}>Dashboard</Title>
            <Paragraph type="secondary">Overview of uploaded log files</Paragraph>

            <Row gutter={16} style={{ marginBottom: 24 }}>
                <Col xs={24} sm={8}>
                    <Card>
                        <Statistic
                            title="Log Files"
                            value={totalFiles}
                            prefix={<FileTextOutlined />}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={8}>
                    <Card>
                        <Statistic
                            title="Parsed Entries"
                            value={totalRequests}
                            prefix={<CheckCircleOutlined />}
                            valueStyle={{ color: '#3f8600' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={8}>
                    <Card>
                        <Statistic
                            title="Parse Errors"
                            value={totalErrors}
                            prefix={<WarningOutlined />}
                            valueStyle={{ color: totalErrors > 0 ? '#cf1322' : '#3f8600' }}
                        />
                    </Card>
                </Col>
            </Row>

            {error && (
                <Result
                    status="error"
                    title="Failed to load files"
                    subTitle={error}
                    extra={
                        <Button type="primary" onClick={loadFiles}>
                            Try again
                        </Button>
                    }
                />
            )}

            {files.length === 0 ? (
                <Card>
                    <Empty description="No log files uploaded yet" />
                </Card>
            ) : (
                <Card>
                    <Table
                        dataSource={files}
                        rowKey="id"
                        scroll={{ x: 800 }}
                        pagination={{ responsive: true, showSizeChanger: false }}
                        onRow={(record) => ({
                            onClick: () => navigate(`/report/${record.id}`),
                            style: { cursor: 'pointer' },
                        })}
                        columns={[
                            { title: 'Filename', dataIndex: 'filename', key: 'filename' },
                            { title: 'Format', dataIndex: 'format_name', key: 'format' },
                            {
                                title: 'Lines',
                                dataIndex: 'total_lines',
                                key: 'lines',
                                render: (v: number) => v.toLocaleString(),
                            },
                            {
                                title: 'Parsed',
                                dataIndex: 'parsed_lines',
                                key: 'parsed',
                                render: (v: number) => <Tag color="green">{v.toLocaleString()}</Tag>,
                            },
                            {
                                title: 'Errors',
                                dataIndex: 'error_lines',
                                key: 'errors',
                                render: (v: number) =>
                                    v > 0 ? <Tag color="red">{v}</Tag> : <Tag color="green">0</Tag>,
                            },
                            {
                                title: 'Uploaded',
                                dataIndex: 'uploaded_at',
                                key: 'uploaded',
                                render: (v: string) => new Date(v).toLocaleString(),
                            },
                            {
                                title: 'Actions',
                                key: 'actions',
                                render: (_: unknown, record: LogFile) => (
                                    <Space onClick={(e) => e.stopPropagation()}>
                                        <Button
                                            type="text"
                                            size="small"
                                            icon={<DownloadOutlined />}
                                            href={getExportCsvUrl(record.id)}
                                            title="Export CSV"
                                        />
                                        <Popconfirm
                                            title="Delete this file?"
                                            description="All entries and statistics will be removed."
                                            onConfirm={(e) => handleDelete(record.id, e)}
                                            okText="Delete"
                                            cancelText="Cancel"
                                            okButtonProps={{ danger: true }}
                                        >
                                            <Button
                                                type="text"
                                                size="small"
                                                danger
                                                icon={<DeleteOutlined />}
                                                title="Delete"
                                            />
                                        </Popconfirm>
                                    </Space>
                                ),
                            },
                        ]}
                    />
                </Card>
            )}
        </div>
    );
}
