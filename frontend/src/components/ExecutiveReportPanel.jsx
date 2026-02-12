import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import { 
    FileText,
    Download,
    AlertCircle,
    CheckCircle,
    TrendingUp,
    Clock,
    Target
} from 'lucide-react';

const ExecutiveReportPanel = ({ data }) => {
    if (!data) {
        return (
            <div className="text-center py-8 text-muted-foreground">
                Run full analysis to generate executive report
            </div>
        );
    }

    const { executive_summary, sections } = data;

    const downloadReport = () => {
        const reportText = JSON.stringify(data, null, 2);
        const blob = new Blob([reportText], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `sql-xray-report-${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);
    };

    const getGradeColor = (grade) => {
        switch (grade) {
            case 'A': return 'text-success bg-success/10 border-success/30';
            case 'B': return 'text-emerald-400 bg-emerald-400/10 border-emerald-400/30';
            case 'C': return 'text-warning bg-warning/10 border-warning/30';
            case 'D': return 'text-orange-400 bg-orange-400/10 border-orange-400/30';
            case 'F': return 'text-destructive bg-destructive/10 border-destructive/30';
            default: return 'text-muted-foreground bg-muted/10 border-border';
        }
    };

    return (
        <div className="space-y-4" data-testid="executive-report-panel">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <FileText className="w-5 h-5 text-primary" />
                    <h3 className="font-semibold">Executive Report</h3>
                </div>
                <Button 
                    onClick={downloadReport}
                    variant="outline"
                    size="sm"
                    className="rounded-sm"
                    data-testid="download-report-btn"
                >
                    <Download className="w-4 h-4 mr-2" />
                    Download JSON
                </Button>
            </div>

            {/* Executive Summary */}
            {executive_summary && (
                <Card className={`border-2 ${getGradeColor(executive_summary.health_grade)}`}>
                    <CardHeader className="p-4 pb-2">
                        <CardTitle className="text-sm">Executive Summary</CardTitle>
                    </CardHeader>
                    <CardContent className="p-4 pt-2">
                        <div className="grid grid-cols-4 gap-4 mb-4">
                            <div className="text-center">
                                <p className={`text-3xl font-bold ${getGradeColor(executive_summary.health_grade).split(' ')[0]}`}>
                                    {executive_summary.health_grade}
                                </p>
                                <p className="text-xs text-muted-foreground">Grade</p>
                            </div>
                            <div className="text-center">
                                <p className="text-3xl font-bold">{executive_summary.health_score}</p>
                                <p className="text-xs text-muted-foreground">Score</p>
                            </div>
                            <div className="text-center">
                                <p className="text-3xl font-bold text-destructive">{executive_summary.critical_issues}</p>
                                <p className="text-xs text-muted-foreground">Critical</p>
                            </div>
                            <div className="text-center">
                                <p className="text-3xl font-bold text-orange-400">{executive_summary.high_priority_issues}</p>
                                <p className="text-xs text-muted-foreground">High Priority</p>
                            </div>
                        </div>
                        <p className="text-sm text-muted-foreground">{executive_summary.assessment}</p>
                        {executive_summary.immediate_actions_required && (
                            <div className="mt-3 p-2 rounded-sm bg-destructive/10 border border-destructive/30 flex items-center gap-2">
                                <AlertCircle className="w-4 h-4 text-destructive" />
                                <span className="text-xs text-destructive font-medium">Immediate action required</span>
                            </div>
                        )}
                    </CardContent>
                </Card>
            )}

            {/* Action Plan */}
            {sections?.action_plan?.length > 0 && (
                <Card className="bg-background border-border">
                    <CardHeader className="p-4 pb-2">
                        <CardTitle className="text-sm flex items-center gap-2">
                            <Target className="w-4 h-4 text-primary" />
                            Priority Action Plan
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="p-4 pt-2">
                        <ScrollArea className="h-[200px]">
                            <div className="space-y-2">
                                {sections.action_plan.map((action, idx) => (
                                    <div 
                                        key={idx}
                                        className={`p-3 rounded-sm border text-xs ${
                                            action.priority === 1 
                                                ? 'bg-destructive/5 border-destructive/20' 
                                                : 'bg-warning/5 border-warning/20'
                                        }`}
                                    >
                                        <div className="flex items-start justify-between gap-2">
                                            <div className="flex-1">
                                                <div className="flex items-center gap-2 mb-1">
                                                    <Badge variant="outline" className="text-[10px]">
                                                        P{action.priority}
                                                    </Badge>
                                                    <span className="font-mono font-medium">{action.table}</span>
                                                </div>
                                                <p className="text-muted-foreground">{action.issue}</p>
                                                <p className="text-primary mt-1">→ {action.recommendation}</p>
                                            </div>
                                            <Badge 
                                                variant="outline" 
                                                className={action.estimated_impact === 'High' ? 'text-success border-success/30' : 'text-warning border-warning/30'}
                                            >
                                                {action.estimated_impact} Impact
                                            </Badge>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </ScrollArea>
                    </CardContent>
                </Card>
            )}

            {/* Strategic Recommendations */}
            {sections?.strategic_recommendations?.length > 0 && (
                <Card className="bg-primary/5 border-primary/30">
                    <CardHeader className="p-4 pb-2">
                        <CardTitle className="text-sm flex items-center gap-2">
                            <TrendingUp className="w-4 h-4 text-primary" />
                            Strategic Recommendations
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="p-4 pt-2">
                        <div className="space-y-3">
                            {sections.strategic_recommendations.map((rec, idx) => (
                                <div key={idx} className="p-3 rounded-sm bg-background border border-border">
                                    <div className="flex items-center gap-2 mb-1">
                                        <Badge variant="outline" className="text-[10px] text-primary border-primary/30">
                                            {rec.category}
                                        </Badge>
                                    </div>
                                    <p className="text-sm font-medium">{rec.recommendation}</p>
                                    <p className="text-xs text-muted-foreground mt-1">{rec.rationale}</p>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Generated timestamp */}
            <p className="text-[10px] text-muted-foreground text-center">
                <Clock className="w-3 h-3 inline mr-1" />
                Generated: {new Date(data.generated_at).toLocaleString()}
            </p>
        </div>
    );
};

export default ExecutiveReportPanel;
