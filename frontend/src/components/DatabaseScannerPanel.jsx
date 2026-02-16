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
    Database,
    Table2,
    Clock,
    AlertTriangle
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const ScanStatus = {
    PENDING: 'pending',
    RUNNING: 'running',
    COMPLETED: 'completed',
    FAILED: 'failed',
    CANCELLED: 'cancelled'
};

const DatabaseScannerPanel = ({ connection, isConnected }) => {
    const [scanId, setScanId] = useState(null);
    const [scanStatus, setScanStatus] = useState(null);
    const [scanResults, setScanResults] = useState(null);
    const [isStarting, setIsStarting] = useState(false);
    const [error, setError] = useState(null);
    const pollingRef = useRef(null);

    // Polling para progreso en tiempo real
    const pollStatus = useCallback(async (id) => {
        if (!id) return;
        
        try {
            const response = await fetch(`${API_URL}/api/scan/status/${id}`, {
                credentials: 'include'
            });
            
            if (response.ok) {
                const status = await response.json();
                setScanStatus(status);
                
                // Si completado o fallido, cargar resultados y detener polling
                if (status.status === ScanStatus.COMPLETED || status.status === ScanStatus.FAILED) {
                    if (pollingRef.current) {
                        clearInterval(pollingRef.current);
                        pollingRef.current = null;
                    }
                    
                    if (status.status === ScanStatus.COMPLETED) {
                        await loadResults(id);
                    }
                }
            }
        } catch (err) {
            console.error('Poll error:', err);
        }
    }, []);

    const loadResults = async (id) => {
        try {
            const response = await fetch(`${API_URL}/api/scan/results/${id}`, {
                credentials: 'include'
            });
            if (response.ok) {
                const results = await response.json();
                setScanResults(results);
            }
        } catch (err) {
            console.error('Load results error:', err);
        }
    };

    const startScan = async () => {
        if (!isConnected || !connection.host) {
            setError('Please connect to a database first');
            return;
        }
        
        setIsStarting(true);
        setError(null);
        setScanResults(null);
        
        try {
            const response = await fetch(`${API_URL}/api/scan/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    connection,
                    scan_type: 'intelligence'
                })
            });
            
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Failed to start scan');
            }
            
            const data = await response.json();
            setScanId(data.scan_id);
            
            // Iniciar polling cada 2 segundos
            pollingRef.current = setInterval(() => pollStatus(data.scan_id), 2000);
            
            // Primera llamada inmediata
            await pollStatus(data.scan_id);
            
        } catch (err) {
            setError(err.message);
        } finally {
            setIsStarting(false);
        }
    };

    const resumeScan = async () => {
        if (!scanId) return;
        
        setIsStarting(true);
        setError(null);
        
        try {
            const response = await fetch(`${API_URL}/api/scan/resume/${scanId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(connection)
            });
            
            if (response.ok) {
                pollingRef.current = setInterval(() => pollStatus(scanId), 2000);
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setIsStarting(false);
        }
    };

    const cancelScan = async () => {
        if (!scanId) return;
        
        try {
            await fetch(`${API_URL}/api/scan/cancel/${scanId}`, {
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

    // Cleanup polling on unmount
    useEffect(() => {
        return () => {
            if (pollingRef.current) {
                clearInterval(pollingRef.current);
            }
        };
    }, []);

    const getStatusColor = (status) => {
        switch (status) {
            case ScanStatus.COMPLETED: return 'text-success';
            case ScanStatus.RUNNING: return 'text-primary';
            case ScanStatus.FAILED: return 'text-destructive';
            default: return 'text-muted-foreground';
        }
    };

    const getStatusIcon = (status) => {
        switch (status) {
            case ScanStatus.COMPLETED: return <CheckCircle className="w-4 h-4 text-success" />;
            case ScanStatus.RUNNING: return <Loader2 className="w-4 h-4 text-primary animate-spin" />;
            case ScanStatus.FAILED: return <AlertCircle className="w-4 h-4 text-destructive" />;
            default: return <Clock className="w-4 h-4 text-muted-foreground" />;
        }
    };

    return (
        <div className="space-y-4" data-testid="database-scanner-panel">
            {/* Control Panel */}
            <Card className="bg-card border-border">
                <CardHeader className="p-4 pb-2">
                    <div className="flex items-center justify-between">
                        <CardTitle className="text-sm flex items-center gap-2">
                            <Database className="w-4 h-4 text-primary" />
                            Database Scanner
                        </CardTitle>
                        {scanStatus && (
                            <div className="flex items-center gap-2">
                                {getStatusIcon(scanStatus.status)}
                                <Badge variant="outline" className={getStatusColor(scanStatus.status)}>
                                    {scanStatus.status}
                                </Badge>
                            </div>
                        )}
                    </div>
                </CardHeader>
                <CardContent className="p-4 pt-2 space-y-4">
                    {/* Progress */}
                    {scanStatus && scanStatus.status === ScanStatus.RUNNING && (
                        <div className="space-y-2">
                            <div className="flex items-center justify-between text-xs">
                                <span className="text-muted-foreground">
                                    Scanning: <span className="font-mono text-foreground">{scanStatus.current_table || '...'}</span>
                                </span>
                                <span className="font-medium">
                                    {scanStatus.processed_tables}/{scanStatus.total_tables} tables
                                </span>
                            </div>
                            <Progress value={scanStatus.progress_percentage} className="h-2" />
                            <p className="text-xs text-muted-foreground text-center">
                                {scanStatus.progress_percentage.toFixed(1)}% complete
                            </p>
                        </div>
                    )}

                    {/* Completed Stats */}
                    {scanStatus?.status === ScanStatus.COMPLETED && scanStatus.stats && (
                        <div className="grid grid-cols-4 gap-2 text-center">
                            <div className="p-2 bg-background rounded-sm">
                                <p className="text-lg font-bold">{scanStatus.total_tables}</p>
                                <p className="text-[10px] text-muted-foreground">Tables</p>
                            </div>
                            <div className="p-2 bg-background rounded-sm">
                                <p className="text-lg font-bold">{scanStatus.stats.total_size_mb?.toFixed(0) || 0}</p>
                                <p className="text-[10px] text-muted-foreground">MB Total</p>
                            </div>
                            <div className="p-2 bg-background rounded-sm">
                                <p className="text-lg font-bold">{scanStatus.stats.total_indexes || 0}</p>
                                <p className="text-[10px] text-muted-foreground">Indexes</p>
                            </div>
                            <div className="p-2 bg-background rounded-sm">
                                <p className="text-lg font-bold text-warning">{scanStatus.stats.issues_found || 0}</p>
                                <p className="text-[10px] text-muted-foreground">Issues</p>
                            </div>
                        </div>
                    )}

                    {/* Error Display */}
                    {error && (
                        <div className="p-3 bg-destructive/10 border border-destructive/30 rounded-sm text-xs text-destructive">
                            {error}
                        </div>
                    )}

                    {/* Recent Errors from Scan */}
                    {scanStatus?.errors?.length > 0 && (
                        <div className="p-3 bg-warning/10 border border-warning/30 rounded-sm">
                            <p className="text-xs font-medium text-warning mb-2 flex items-center gap-1">
                                <AlertTriangle className="w-3 h-3" />
                                Scan Errors ({scanStatus.errors.length})
                            </p>
                            <div className="space-y-1 max-h-24 overflow-y-auto">
                                {scanStatus.errors.map((err, idx) => (
                                    <p key={idx} className="text-[10px] text-muted-foreground">
                                        {err.table && <span className="font-mono">{err.table}: </span>}
                                        {err.message}
                                    </p>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Actions */}
                    <div className="flex gap-2">
                        {(!scanStatus || scanStatus.status === ScanStatus.COMPLETED || scanStatus.status === ScanStatus.FAILED) && (
                            <Button
                                onClick={startScan}
                                disabled={isStarting || !isConnected}
                                className="flex-1 rounded-sm"
                                data-testid="start-scan-btn"
                            >
                                {isStarting ? (
                                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                ) : (
                                    <Play className="w-4 h-4 mr-2" />
                                )}
                                {scanStatus?.status === ScanStatus.COMPLETED ? 'Rescan' : 'Start Scan'}
                            </Button>
                        )}

                        {scanStatus?.status === ScanStatus.RUNNING && (
                            <Button
                                onClick={cancelScan}
                                variant="destructive"
                                className="flex-1 rounded-sm"
                            >
                                <Pause className="w-4 h-4 mr-2" />
                                Cancel
                            </Button>
                        )}

                        {(scanStatus?.status === ScanStatus.FAILED || scanStatus?.status === ScanStatus.CANCELLED) && scanId && (
                            <Button
                                onClick={resumeScan}
                                variant="outline"
                                className="flex-1 rounded-sm"
                                disabled={isStarting}
                            >
                                <RefreshCw className="w-4 h-4 mr-2" />
                                Resume
                            </Button>
                        )}
                    </div>
                </CardContent>
            </Card>

            {/* Results */}
            {scanResults?.tables?.length > 0 && (
                <Card className="bg-card border-border">
                    <CardHeader className="p-4 pb-2">
                        <CardTitle className="text-sm flex items-center gap-2">
                            <Table2 className="w-4 h-4 text-primary" />
                            Scan Results ({scanResults.tables.length} tables)
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="p-4 pt-2">
                        <ScrollArea className="h-[300px]">
                            <div className="space-y-2">
                                {scanResults.tables.map((table, idx) => (
                                    <div 
                                        key={idx}
                                        className={`p-3 rounded-sm border ${
                                            table.issues?.length > 0 
                                                ? 'bg-warning/5 border-warning/20' 
                                                : 'bg-background border-border'
                                        }`}
                                    >
                                        <div className="flex items-center justify-between mb-1">
                                            <span className="font-mono text-sm font-medium">{table.table_name}</span>
                                            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                                <span>{table.row_count?.toLocaleString()} rows</span>
                                                <span>{table.size_mb?.toFixed(1)} MB</span>
                                                {table.issues?.length > 0 && (
                                                    <Badge variant="outline" className="text-warning border-warning/30">
                                                        {table.issues.length} issues
                                                    </Badge>
                                                )}
                                            </div>
                                        </div>
                                        {table.issues?.length > 0 && (
                                            <div className="mt-2 space-y-1">
                                                {table.issues.slice(0, 3).map((issue, issueIdx) => (
                                                    <p key={issueIdx} className="text-xs text-muted-foreground">
                                                        <span className={`font-medium ${
                                                            issue.severity === 'critical' ? 'text-destructive' :
                                                            issue.severity === 'high' ? 'text-orange-400' :
                                                            'text-warning'
                                                        }`}>
                                                            [{issue.severity}]
                                                        </span>
                                                        {' '}{issue.message}
                                                    </p>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </ScrollArea>
                    </CardContent>
                </Card>
            )}
        </div>
    );
};

export default DatabaseScannerPanel;
