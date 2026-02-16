import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Progress } from './ui/progress';
import { Badge } from './ui/badge';
import { ScrollArea } from './ui/scroll-area';
import { 
    Play, 
    Pause,
    RefreshCw,
    CheckCircle, 
    AlertCircle,
    Loader2,
    Activity,
    BarChart3,
    Database,
    Zap
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const WorkloadAnalyzerPanel = ({ connection, isConnected }) => {
    const [analysisId, setAnalysisId] = useState(null);
    const [status, setStatus] = useState(null);
    const [isStarting, setIsStarting] = useState(false);
    const [error, setError] = useState(null);
    const pollingRef = useRef(null);

    const pollStatus = useCallback(async (id) => {
        if (!id) return;
        
        try {
            const response = await fetch(`${API_URL}/api/workload/status/${id}`, {
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                setStatus(data);
                
                if (data.status === 'completed' || data.status === 'failed') {
                    if (pollingRef.current) {
                        clearInterval(pollingRef.current);
                        pollingRef.current = null;
                    }
                }
            }
        } catch (err) {
            console.error('Poll error:', err);
        }
    }, []);

    const startAnalysis = async () => {
        if (!isConnected || !connection.host) {
            setError('Please connect to a database first');
            return;
        }
        
        setIsStarting(true);
        setError(null);
        
        try {
            const response = await fetch(`${API_URL}/api/workload/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ connection })
            });
            
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Failed to start analysis');
            }
            
            const data = await response.json();
            setAnalysisId(data.analysis_id);
            
            pollingRef.current = setInterval(() => pollStatus(data.analysis_id), 2000);
            await pollStatus(data.analysis_id);
            
        } catch (err) {
            setError(err.message);
        } finally {
            setIsStarting(false);
        }
    };

    const cancelAnalysis = async () => {
        if (!analysisId) return;
        
        try {
            await fetch(`${API_URL}/api/workload/cancel/${analysisId}`, {
                method: 'POST',
                credentials: 'include'
            });
            
            if (pollingRef.current) {
                clearInterval(pollingRef.current);
                pollingRef.current = null;
            }
        } catch (err) {
            console.error('Cancel error:', err);
        }
    };

    useEffect(() => {
        return () => {
            if (pollingRef.current) {
                clearInterval(pollingRef.current);
            }
        };
    }, []);

    const getStatusIcon = (s) => {
        switch (s) {
            case 'completed': return <CheckCircle className="w-4 h-4 text-success" />;
            case 'analyzing':
            case 'collecting': return <Loader2 className="w-4 h-4 text-primary animate-spin" />;
            case 'failed': return <AlertCircle className="w-4 h-4 text-destructive" />;
            default: return <Activity className="w-4 h-4 text-muted-foreground" />;
        }
    };

    return (
        <div className="space-y-4" data-testid="workload-analyzer-panel">
            <Card className="bg-card border-border">
                <CardHeader className="p-4 pb-2">
                    <div className="flex items-center justify-between">
                        <CardTitle className="text-sm flex items-center gap-2">
                            <BarChart3 className="w-4 h-4 text-info" />
                            Workload Analyzer
                        </CardTitle>
                        {status && (
                            <div className="flex items-center gap-2">
                                {getStatusIcon(status.status)}
                                <Badge variant="outline">{status.status}</Badge>
                            </div>
                        )}
                    </div>
                </CardHeader>
                <CardContent className="p-4 pt-2 space-y-4">
                    {/* Progress */}
                    {status && status.status !== 'completed' && status.status !== 'failed' && (
                        <div className="space-y-2">
                            <div className="flex items-center justify-between text-xs">
                                <span className="text-muted-foreground">{status.current_phase}</span>
                                <span className="font-medium">{status.progress_percentage?.toFixed(0)}%</span>
                            </div>
                            <Progress value={status.progress_percentage || 0} className="h-2" />
                        </div>
                    )}

                    {/* Summary */}
                    {status?.status === 'completed' && status.summary && (
                        <div className="space-y-3">
                            {status.summary.query_digest && (
                                <div className="p-3 bg-background rounded-sm border border-border">
                                    <div className="flex items-center gap-2 mb-2">
                                        <Database className="w-4 h-4 text-primary" />
                                        <span className="text-sm font-medium">Query Patterns</span>
                                    </div>
                                    <p className="text-xs text-muted-foreground">
                                        {status.summary.query_digest.total_patterns || 0} patterns analyzed
                                    </p>
                                </div>
                            )}

                            {status.summary.slow_queries && (
                                <div className="p-3 bg-warning/5 rounded-sm border border-warning/20">
                                    <div className="flex items-center gap-2 mb-2">
                                        <Zap className="w-4 h-4 text-warning" />
                                        <span className="text-sm font-medium text-warning">Slow Queries</span>
                                    </div>
                                    <p className="text-xs text-muted-foreground">
                                        {status.summary.slow_queries.slow_query_count || 0} slow query patterns found
                                    </p>
                                </div>
                            )}

                            {status.summary.index_usage && (
                                <div className="p-3 bg-background rounded-sm border border-border">
                                    <div className="flex items-center gap-2 mb-2">
                                        <Activity className="w-4 h-4 text-info" />
                                        <span className="text-sm font-medium">Index Usage</span>
                                    </div>
                                    <p className="text-xs text-muted-foreground">
                                        {status.summary.index_usage.indexes_analyzed || 0} indexes analyzed
                                        {status.summary.index_usage.unused_indexes > 0 && (
                                            <span className="text-warning ml-2">
                                                ({status.summary.index_usage.unused_indexes} unused)
                                            </span>
                                        )}
                                    </p>
                                </div>
                            )}

                            {status.summary.recommendations?.recommendations?.length > 0 && (
                                <div className="p-3 bg-primary/5 rounded-sm border border-primary/20">
                                    <p className="text-sm font-medium text-primary mb-2">Recommendations</p>
                                    <ScrollArea className="h-[100px]">
                                        {status.summary.recommendations.recommendations.map((rec, idx) => (
                                            <div key={idx} className="mb-2 text-xs">
                                                <Badge variant="outline" className="mb-1">{rec.priority}</Badge>
                                                <p className="text-muted-foreground">{rec.message}</p>
                                            </div>
                                        ))}
                                    </ScrollArea>
                                </div>
                            )}
                        </div>
                    )}

                    {error && (
                        <div className="p-3 bg-destructive/10 border border-destructive/30 rounded-sm text-xs text-destructive">
                            {error}
                        </div>
                    )}

                    {/* Actions */}
                    <div className="flex gap-2">
                        {(!status || status.status === 'completed' || status.status === 'failed') && (
                            <Button
                                onClick={startAnalysis}
                                disabled={isStarting || !isConnected}
                                className="flex-1 rounded-sm"
                                data-testid="start-workload-btn"
                            >
                                {isStarting ? (
                                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                ) : (
                                    <Play className="w-4 h-4 mr-2" />
                                )}
                                {status?.status === 'completed' ? 'Reanalyze' : 'Start Analysis'}
                            </Button>
                        )}

                        {(status?.status === 'analyzing' || status?.status === 'collecting') && (
                            <Button
                                onClick={cancelAnalysis}
                                variant="destructive"
                                className="flex-1 rounded-sm"
                            >
                                <Pause className="w-4 h-4 mr-2" />
                                Cancel
                            </Button>
                        )}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
};

export default WorkloadAnalyzerPanel;
