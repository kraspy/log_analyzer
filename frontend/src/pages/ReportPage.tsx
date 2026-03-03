/**
 * Report page — detailed statistics and per-URL breakdown for a log file.
 * @module ReportPage
 */
import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router';
import {
    Typography, Card, Spin, Tag, Statistic, Row, Col, Table, Descriptions,
    Progress, Tabs, Button, Space, App, Result, Input,
} from 'antd';
import type { FilterDropdownProps } from 'antd/es/table/interface';
import {
    ArrowLeftOutlined, ClockCircleOutlined, ApiOutlined,
    ThunderboltOutlined, AlertOutlined, RobotOutlined, DownloadOutlined,
    SearchOutlined, BarChartOutlined,
} from '@ant-design/icons';
import type { StatsResponse, LogFile, UrlStat } from '../api/client';
import { getStats, getLogFile, getExportCsvUrl } from '../api/client';

const { Title } = Typography;

/**
 * Report page — statistics and visual analytics for an uploaded log file.
 *
 * Loads both file metadata and computed statistics from the backend.
 * Charts are implemented with Ant Design Progress bars and table —
 * in production you'd add Recharts or similar.
 */
export function ReportPage() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const [file, setFile] = useState<LogFile | null>(null);
    const [stats, setStats] = useState<StatsResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const { message: toast } = App.useApp();

    const fileId = Number(id);

    useEffect(() => {
        if (!fileId) return;

        Promise.all([getLogFile(fileId), getStats(fileId)])
            .then(([fileData, statsData]) => {
                setFile(fileData);
                setStats(statsData);
            })
            .catch((err) => {
                const msg = err.message || 'Failed to load report';
                setError(msg);
                toast.error(msg);
            })
            .finally(() => setLoading(false));
    }, [fileId, toast]);

    if (loading) return <Spin size="large" />;
    if (error) return (
        <Result
            status="error"
            title="Failed to load report"
            subTitle={error}
            extra={
                <Button type="primary" onClick={() => navigate('/')}>
                    Back to Dashboard
                </Button>
            }
        />
    );
    if (!file || !stats) return (
        <Result
            status="404"
            title="File not found"
            subTitle={`Log file #${fileId} does not exist or was deleted.`}
            extra={
                <Button type="primary" onClick={() => navigate('/')}>
                    Back to Dashboard
                </Button>
            }
        />
    );

    // Status code categories
    const statusCategories = Object.entries(stats.status_distribution).reduce(
        (acc, [code, count]) => {
            const cat = Number(code) < 300 ? 'success' : Number(code) < 400 ? 'redirect' : Number(code) < 500 ? 'clientError' : 'serverError';
            acc[cat] = (acc[cat] || 0) + count;
            return acc;
        },
        {} as Record<string, number>,
    );

    const successRate = stats.total_requests > 0
        ? ((statusCategories.success || 0) / stats.total_requests * 100).toFixed(1)
        : '0';

    // Per-URL stats columns
    const urlStatsColumns = [
        {
            title: 'URL',
            dataIndex: 'url',
            key: 'url',
            ellipsis: true,
            width: 320,
            filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters }: FilterDropdownProps) => (
                <div style={{ padding: 8 }}>
                    <Input
                        placeholder="Search URL"
                        value={selectedKeys[0]}
                        onChange={(e) => setSelectedKeys(e.target.value ? [e.target.value] : [])}
                        onPressEnter={() => confirm()}
                        style={{ width: 200, marginBottom: 8, display: 'block' }}
                    />
                    <Space>
                        <Button type="primary" size="small" onClick={() => confirm()}>Filter</Button>
                        <Button size="small" onClick={() => { clearFilters?.(); confirm(); }}>Reset</Button>
                    </Space>
                </div>
            ),
            filterIcon: (filtered: boolean) => <SearchOutlined style={{ color: filtered ? '#1677ff' : undefined }} />,
            onFilter: (value: React.Key | boolean, record: UrlStat) =>
                record.url.toLowerCase().includes(String(value).toLowerCase()),
        },
        {
            title: 'Count',
            dataIndex: 'count',
            key: 'count',
            width: 90,
            sorter: (a: UrlStat, b: UrlStat) => a.count - b.count,
            render: (v: number) => v.toLocaleString(),
        },
        {
            title: 'Count %',
            dataIndex: 'count_perc',
            key: 'count_perc',
            width: 100,
            sorter: (a: UrlStat, b: UrlStat) => a.count_perc - b.count_perc,
            render: (v: number) => `${v.toFixed(2)}%`,
        },
        {
            title: 'Time Sum (s)',
            dataIndex: 'time_sum',
            key: 'time_sum',
            width: 120,
            defaultSortOrder: 'descend' as const,
            sorter: (a: UrlStat, b: UrlStat) => a.time_sum - b.time_sum,
            render: (v: number) => v.toFixed(3),
        },
        {
            title: 'Time %',
            dataIndex: 'time_perc',
            key: 'time_perc',
            width: 90,
            sorter: (a: UrlStat, b: UrlStat) => a.time_perc - b.time_perc,
            render: (v: number) => `${v.toFixed(2)}%`,
        },
        {
            title: 'Time Avg (s)',
            dataIndex: 'time_avg',
            key: 'time_avg',
            width: 110,
            sorter: (a: UrlStat, b: UrlStat) => a.time_avg - b.time_avg,
            render: (v: number) => v.toFixed(3),
        },
        {
            title: 'Time Max (s)',
            dataIndex: 'time_max',
            key: 'time_max',
            width: 115,
            sorter: (a: UrlStat, b: UrlStat) => a.time_max - b.time_max,
            render: (v: number) => v.toFixed(3),
        },
        {
            title: 'Time Med (s)',
            dataIndex: 'time_med',
            key: 'time_med',
            width: 110,
            sorter: (a: UrlStat, b: UrlStat) => a.time_med - b.time_med,
            render: (v: number) => v.toFixed(3),
        },
    ];

    return (
        <div>
            <Space>
                <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>
                    Back to Dashboard
                </Button>
                <Button
                    icon={<DownloadOutlined />}
                    href={getExportCsvUrl(fileId)}
                    target="_blank"
                >
                    Export CSV
                </Button>
            </Space>

            <Title level={3} style={{ marginTop: 16 }}>{file.filename}</Title>

            <Descriptions bordered size="small" column={3} style={{ marginBottom: 24 }}>
                <Descriptions.Item label="Format">{file.format_name}</Descriptions.Item>
                <Descriptions.Item label="Uploaded">{new Date(file.uploaded_at).toLocaleString()}</Descriptions.Item>
                <Descriptions.Item label="Hash">{file.file_hash.slice(0, 12)}...</Descriptions.Item>
                <Descriptions.Item label="Total Lines">{file.total_lines.toLocaleString()}</Descriptions.Item>
                <Descriptions.Item label="Parsed">{file.parsed_lines.toLocaleString()}</Descriptions.Item>
                <Descriptions.Item label="Errors">{file.error_lines}</Descriptions.Item>
            </Descriptions>

            <Tabs
                defaultActiveKey="overview"
                items={[
                    {
                        key: 'overview',
                        label: 'Overview',
                        children: (
                            <>
                                {/* Response time cards */}
                                <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
                                    <Col xs={12} sm={6}>
                                        <Card>
                                            <Statistic
                                                title="Total Requests"
                                                value={stats.total_requests}
                                                prefix={<ApiOutlined />}
                                            />
                                        </Card>
                                    </Col>
                                    <Col xs={12} sm={6}>
                                        <Card>
                                            <Statistic
                                                title="Avg Response"
                                                value={stats.avg_response_time ?? 'N/A'}
                                                suffix={stats.avg_response_time ? 'ms' : ''}
                                                prefix={<ClockCircleOutlined />}
                                            />
                                        </Card>
                                    </Col>
                                    <Col xs={12} sm={6}>
                                        <Card>
                                            <Statistic
                                                title="P95 Response"
                                                value={stats.p95_response_time ?? 'N/A'}
                                                suffix={stats.p95_response_time ? 'ms' : ''}
                                                prefix={<ThunderboltOutlined />}
                                                valueStyle={{ color: (stats.p95_response_time ?? 0) > 1000 ? '#cf1322' : '#3f8600' }}
                                            />
                                        </Card>
                                    </Col>
                                    <Col xs={12} sm={6}>
                                        <Card>
                                            <Statistic
                                                title="Success Rate"
                                                value={successRate}
                                                suffix="%"
                                                prefix={<AlertOutlined />}
                                                valueStyle={{ color: Number(successRate) > 95 ? '#3f8600' : '#cf1322' }}
                                            />
                                        </Card>
                                    </Col>
                                </Row>

                                {/* Status distribution — full width */}
                                <Card title="Status Code Distribution" style={{ marginBottom: 24 }}>
                                    <Table
                                        dataSource={Object.entries(stats.status_distribution)
                                            .sort(([a], [b]) => Number(a) - Number(b))
                                            .map(([code, count]) => ({ code, count, key: code }))}
                                        pagination={false}
                                        size="small"
                                        columns={[
                                            {
                                                title: 'Status',
                                                dataIndex: 'code',
                                                render: (code: string) => {
                                                    const n = Number(code);
                                                    const color = n < 300 ? 'green' : n < 400 ? 'blue' : n < 500 ? 'orange' : 'red';
                                                    return <Tag color={color}>{code}</Tag>;
                                                },
                                            },
                                            {
                                                title: 'Count',
                                                dataIndex: 'count',
                                                render: (v: number) => v.toLocaleString(),
                                            },
                                            {
                                                title: 'Percentage',
                                                dataIndex: 'count',
                                                key: 'pct',
                                                render: (v: number) => {
                                                    const pct = stats.total_requests > 0 ? (v / stats.total_requests * 100) : 0;
                                                    return <Progress percent={Number(pct.toFixed(1))} size="small" />;
                                                },
                                            },
                                        ]}
                                    />
                                </Card>
                            </>
                        ),
                    },
                    {
                        key: 'url_stats',
                        label: (
                            <span><BarChartOutlined /> Per-URL Statistics</span>
                        ),
                        children: (
                            <Card
                                title={`Per-URL Statistics (${stats.url_stats.length} URLs)`}
                            >
                                <Table<UrlStat>
                                    dataSource={stats.url_stats.map((u, i) => ({ ...u, key: i }))}
                                    columns={urlStatsColumns}
                                    size="small"
                                    scroll={{ x: 1100 }}
                                    pagination={{
                                        pageSize: 50,
                                        showSizeChanger: true,
                                        pageSizeOptions: ['20', '50', '100', '200'],
                                        showTotal: (total, range) => `${range[0]}-${range[1]} of ${total} URLs`,
                                    }}
                                />
                            </Card>
                        ),
                    },
                    {
                        key: 'ai',
                        label: (
                            <span><RobotOutlined /> AI Analysis</span>
                        ),
                        children: <AITab logFileId={fileId} />,
                    },
                ]}
            />
        </div>
    );
}

/** AI Analysis tab — summary + chat */
function AITab({ logFileId }: { logFileId: number }) {
    // Lazy import to keep this tab light
    const [AIComponent, setAIComponent] = useState<React.ComponentType<{ logFileId: number }> | null>(null);

    useEffect(() => {
        import('./AIPage').then((mod) => setAIComponent(() => mod.AIAnalysis));
    }, []);

    if (!AIComponent) return <Spin />;
    return <AIComponent logFileId={logFileId} />;
}
