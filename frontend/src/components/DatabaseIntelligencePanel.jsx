import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { ScrollArea } from './ui/scroll-area';
import { 
    AlertTriangle, 
    AlertCircle, 
    CheckCircle, 
    Info,
    Database,
    Table2,
    Key,
    Hash,
    Layers
} from 'lucide-react';

const SeverityIcon = ({ severity }) => {
    switch (severity) {
        case 'critical':
            return <AlertCircle className="w-4 h-4 text-destructive" />;
        case 'high':
            return <AlertTriangle className="w-4 h-4 text-orange-500" />;
        case 'medium':
            return <AlertTriangle className="w-4 h-4 text-warning" />;
        case 'low':
            return <Info className="w-4 h-4 text-info" />;
        default:
            return <CheckCircle className="w-4 h-4 text-success" />;
    }
};

const SeverityBadge = ({ severity }) => {
    const colors = {
        critical: 'bg-destructive/20 text-destructive border-destructive/30',
        high: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
        medium: 'bg-warning/20 text-warning border-warning/30',
        low: 'bg-info/20 text-info border-info/30'
    };
    
    return (
        <Badge variant="outline" className={`text-[10px] ${colors[severity] || ''}`}>
            {severity}
        </Badge>
    );
};

const DatabaseIntelligencePanel = ({ data }) => {
    if (!data) return null;

    const { total_tables, tables_with_issues, findings, summary } = data;

    return (
        <div className="space-y-4" data-testid="intelligence-panel">
            {/* Summary Cards */}
            <div className="grid grid-cols-4 gap-3">
                <Card className="bg-background border-border">
                    <CardContent className="p-3 text-center">
                        <p className="text-2xl font-bold">{total_tables}</p>
                        <p className="text-xs text-muted-foreground">Tables</p>
                    </CardContent>
                </Card>
                <Card className="bg-destructive/10 border-destructive/30">
                    <CardContent className="p-3 text-center">
                        <p className="text-2xl font-bold text-destructive">{summary?.critical || 0}</p>
                        <p className="text-xs text-destructive/70">Critical</p>
                    </CardContent>
                </Card>
                <Card className="bg-orange-500/10 border-orange-500/30">
                    <CardContent className="p-3 text-center">
                        <p className="text-2xl font-bold text-orange-400">{summary?.high || 0}</p>
                        <p className="text-xs text-orange-400/70">High</p>
                    </CardContent>
                </Card>
                <Card className="bg-warning/10 border-warning/30">
                    <CardContent className="p-3 text-center">
                        <p className="text-2xl font-bold text-warning">{summary?.medium || 0}</p>
                        <p className="text-xs text-warning/70">Medium</p>
                    </CardContent>
                </Card>
            </div>

            {/* Findings List */}
            <ScrollArea className="h-[400px]">
                <div className="space-y-3">
                    {findings?.map((finding, idx) => (
                        <Card key={idx} className="bg-background border-border">
                            <CardHeader className="p-3 pb-2">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <Table2 className="w-4 h-4 text-primary" />
                                        <CardTitle className="text-sm font-mono">{finding.table_name}</CardTitle>
                                    </div>
                                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                        <span>{finding.row_count?.toLocaleString() || 'N/A'} rows</span>
                                        <span>•</span>
                                        <span>{finding.size_mb?.toFixed(1) || 'N/A'} MB</span>
                                        <SeverityBadge severity={finding.max_severity} />
                                    </div>
                                </div>
                            </CardHeader>
                            <CardContent className="p-3 pt-0">
                                <div className="space-y-2">
                                    {finding.issues?.map((issue, issueIdx) => (
                                        <div 
                                            key={issueIdx} 
                                            className={`p-2 rounded-sm border text-xs ${
                                                issue.severity === 'critical' ? 'bg-destructive/5 border-destructive/20' :
                                                issue.severity === 'high' ? 'bg-orange-500/5 border-orange-500/20' :
                                                issue.severity === 'medium' ? 'bg-warning/5 border-warning/20' :
                                                'bg-muted/50 border-border'
                                            }`}
                                        >
                                            <div className="flex items-start gap-2">
                                                <SeverityIcon severity={issue.severity} />
                                                <div className="flex-1">
                                                    <p className="font-medium">{issue.message}</p>
                                                    {issue.recommendation && (
                                                        <p className="text-muted-foreground mt-1 font-mono text-[10px]">
                                                            → {issue.recommendation}
                                                        </p>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            </ScrollArea>

            {findings?.length === 0 && (
                <div className="text-center py-8">
                    <CheckCircle className="w-12 h-12 text-success mx-auto mb-3" />
                    <p className="text-muted-foreground">No structural issues detected</p>
                </div>
            )}
        </div>
    );
};

export default DatabaseIntelligencePanel;
