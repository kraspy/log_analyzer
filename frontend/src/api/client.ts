/**
 * API client — typed fetch wrapper for backend endpoints.
 *
 * In a real project you might auto-generate this from OpenAPI spec
 * using openapi-ts. For now, a manual typed client keeps it simple
 * and serves as a learning example.
 */

const API_BASE = import.meta.env.VITE_API_URL || '/api';

/** Generic fetch wrapper with error handling */
async function request<T>(url: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE}${url}`, {
        headers: { 'Content-Type': 'application/json', ...options?.headers },
        ...options,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
}

// ── Types ──────────────────────────────────────────────

export interface LogFile {
    id: number;
    filename: string;
    format_name: string;
    total_lines: number;
    parsed_lines: number;
    error_lines: number;
    uploaded_at: string;
    file_hash: string;
}

export interface UploadResponse {
    log_file_id: number;
    filename: string;
    total_lines: number;
    parsed_lines: number;
    error_lines: number;
    message: string;
}

export interface UrlStat {
    url: string;
    count: number;
    count_perc: number;
    time_sum: number;
    time_perc: number;
    time_avg: number;
    time_max: number;
    time_med: number;
}

export interface StatsResponse {
    total_requests: number;
    avg_response_time: number | null;
    median_response_time: number | null;
    p95_response_time: number | null;
    p99_response_time: number | null;
    status_distribution: Record<string, number>;
    top_endpoints: Array<{ path: string; count: number }>;
    url_stats: UrlStat[];
}

export interface AIStatusResponse {
    available: boolean;
    message: string;
}

export interface SummaryResponse {
    summary: string;
    ai_available: boolean;
}

// ── API Functions ──────────────────────────────────────

export interface PreviewResult {
    line_number: number;
    parsed: boolean;
    fields: Record<string, string | number | null> | null;
}

/** Preview log lines — test parsing without upload */
export async function previewLines(
    lines: string[],
    format: string,
): Promise<{ results: PreviewResult[] }> {
    return request('/logs/preview', {
        method: 'POST',
        body: JSON.stringify({ lines, format_name: format }),
    });
}

/** Upload a log file */
export async function uploadLogFile(file: File, format = 'combined'): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE}/logs/upload?format_name=${format}`, {
        method: 'POST',
        body: formData,
        // Don't set Content-Type — browser sets it with boundary for multipart
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
}

/** List all uploaded files */
export async function listLogFiles(): Promise<{ files: LogFile[]; total: number }> {
    return request('/reports');
}

/** Get details of a specific file */
export async function getLogFile(id: number): Promise<LogFile> {
    return request(`/reports/${id}`);
}

/** Delete a log file and all its entries */
export async function deleteLogFile(id: number): Promise<void> {
    const response = await fetch(`${API_BASE}/reports/${id}`, {
        method: 'DELETE',
    });
    if (!response.ok && response.status !== 204) {
        const error = await response.json().catch(() => ({ detail: 'Delete failed' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }
}

/** Get CSV export URL (for download link) */
export function getExportCsvUrl(id: number): string {
    return `${API_BASE}/export/${id}/csv`;
}

/** Get statistics for a file */
export async function getStats(logFileId: number): Promise<StatsResponse> {
    return request(`/stats/${logFileId}`);
}

/** Check AI availability */
export async function getAIStatus(): Promise<AIStatusResponse> {
    return request('/ai/status');
}

/** Generate AI summary */
export async function generateSummary(logFileId: number): Promise<SummaryResponse> {
    return request('/ai/summary', {
        method: 'POST',
        body: JSON.stringify({ log_file_id: logFileId }),
    });
}

/**
 * Chat with AI about logs via SSE (Server-Sent Events).
 *
 * SSE is a browser-native streaming protocol. Unlike WebSocket,
 * it's one-directional (server → client) and works over plain HTTP.
 * Perfect for streaming LLM responses.
 *
 * @param logFileId - ID of the log file to discuss
 * @param question - User's question
 * @param onChunk - Callback for each text chunk
 * @param onDone - Callback when streaming is complete
 * @param onError - Callback on error
 */
export async function chatWithAI(
    logFileId: number,
    question: string,
    onChunk: (text: string) => void,
    onDone: () => void,
    onError: (error: Error) => void,
): Promise<void> {
    try {
        const response = await fetch(`${API_BASE}/ai/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ log_file_id: logFileId, question }),
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const reader = response.body?.getReader();
        if (!reader) throw new Error('No response body');

        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6);
                    if (data === '[DONE]') {
                        onDone();
                        return;
                    }
                    onChunk(data);
                }
            }
        }

        onDone();
    } catch (error) {
        onError(error instanceof Error ? error : new Error(String(error)));
    }
}
