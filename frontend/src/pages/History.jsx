import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { ScrollArea } from '../components/ui/scroll-area';
import { Badge } from '../components/ui/badge';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from '../components/ui/alert-dialog';
import { 
    ArrowLeft, 
    Activity, 
    Trash2, 
    Clock, 
    Database,
    FileCode
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const History = () => {
    const navigate = useNavigate();
    const { user } = useAuth();
    const [queries, setQueries] = useState([]);
    const [loading, setLoading] = useState(true);
    const [deleteId, setDeleteId] = useState(null);

    useEffect(() => {
        fetchQueries();
    }, []);

    const fetchQueries = async () => {
        try {
            const response = await fetch(`${API_URL}/api/queries`, {
                credentials: 'include'
            });
            if (response.ok) {
                const data = await response.json();
                setQueries(data);
            }
        } catch (err) {
            console.error('Failed to fetch queries:', err);
        } finally {
            setLoading(false);
        }
    };

    const deleteQuery = async () => {
        if (!deleteId) return;
        
        try {
            await fetch(`${API_URL}/api/queries/${deleteId}`, {
                method: 'DELETE',
                credentials: 'include'
            });
            setQueries(queries.filter(q => q.query_id !== deleteId));
        } catch (err) {
            console.error('Failed to delete query:', err);
        } finally {
            setDeleteId(null);
        }
    };

    const formatDate = (dateStr) => {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    const truncateQuery = (query, maxLength = 150) => {
        const cleaned = query.replace(/--.*$/gm, '').replace(/\s+/g, ' ').trim();
        return cleaned.length > maxLength ? cleaned.substring(0, maxLength) + '...' : cleaned;
    };

    return (
        <div className="min-h-screen bg-background" data-testid="history-page">
            {/* Header */}
            <header className="border-b border-border bg-card">
                <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => navigate('/dashboard')}
                            className="rounded-sm"
                            data-testid="back-to-dashboard-btn"
                        >
                            <ArrowLeft className="w-4 h-4" />
                        </Button>
                        <div className="flex items-center gap-2">
                            <Activity className="w-5 h-5 text-primary" />
                            <span className="font-display font-bold">SQL X-RAY</span>
                        </div>
                    </div>
                    <h1 className="text-lg font-semibold">Query History</h1>
                </div>
            </header>

            {/* Content */}
            <main className="max-w-5xl mx-auto px-6 py-8">
                {loading ? (
                    <div className="flex items-center justify-center py-20">
                        <div className="loading-spinner" />
                    </div>
                ) : queries.length === 0 ? (
                    <div className="text-center py-20">
                        <FileCode className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                        <p className="text-muted-foreground mb-4">No saved queries yet</p>
                        <Button
                            onClick={() => navigate('/dashboard')}
                            className="rounded-sm"
                            data-testid="go-to-dashboard-btn"
                        >
                            Start Analyzing
                        </Button>
                    </div>
                ) : (
                    <ScrollArea className="h-[calc(100vh-200px)]">
                        <div className="space-y-4">
                            {queries.map((q) => (
                                <div
                                    key={q.query_id}
                                    className="history-item group"
                                    data-testid={`query-item-${q.query_id}`}
                                >
                                    <div className="flex items-start justify-between gap-4">
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 mb-2">
                                                <Badge variant="outline" className="font-mono text-xs">
                                                    <Database className="w-3 h-3 mr-1" />
                                                    {q.dialect}
                                                </Badge>
                                                <span className="text-xs text-muted-foreground flex items-center gap-1">
                                                    <Clock className="w-3 h-3" />
                                                    {formatDate(q.created_at)}
                                                </span>
                                            </div>
                                            <pre className="font-mono text-sm text-foreground whitespace-pre-wrap overflow-hidden">
                                                {truncateQuery(q.query)}
                                            </pre>
                                            {q.analysis_result?.overview?.summary && (
                                                <p className="text-xs text-muted-foreground mt-2 line-clamp-2">
                                                    {q.analysis_result.overview.summary}
                                                </p>
                                            )}
                                        </div>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="opacity-0 group-hover:opacity-100 transition-opacity rounded-sm text-destructive hover:text-destructive"
                                            onClick={() => setDeleteId(q.query_id)}
                                            data-testid={`delete-query-${q.query_id}`}
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </Button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </ScrollArea>
                )}
            </main>

            {/* Delete Confirmation Dialog */}
            <AlertDialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete Query</AlertDialogTitle>
                        <AlertDialogDescription>
                            Are you sure you want to delete this saved query? This action cannot be undone.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel className="rounded-sm">Cancel</AlertDialogCancel>
                        <AlertDialogAction 
                            onClick={deleteQuery}
                            className="rounded-sm bg-destructive hover:bg-destructive/90"
                            data-testid="confirm-delete-btn"
                        >
                            Delete
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
};

export default History;
