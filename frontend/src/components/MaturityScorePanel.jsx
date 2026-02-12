import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { 
    Award,
    CheckCircle,
    AlertTriangle,
    TrendingUp,
    Database,
    Layers,
    BarChart3,
    Shield
} from 'lucide-react';

const MaturityScorePanel = ({ data }) => {
    if (!data || data.error) {
        return (
            <div className="text-center py-8 text-muted-foreground">
                {data?.error ? `Error: ${data.error}` : 'Connect to a database to see maturity score'}
            </div>
        );
    }

    const { total_score, grade, assessment, breakdown, priority_actions } = data;

    const getGradeColor = (grade) => {
        switch (grade) {
            case 'A': return 'text-success border-success/50 bg-success/10';
            case 'B': return 'text-emerald-400 border-emerald-400/50 bg-emerald-400/10';
            case 'C': return 'text-warning border-warning/50 bg-warning/10';
            case 'D': return 'text-orange-400 border-orange-400/50 bg-orange-400/10';
            case 'F': return 'text-destructive border-destructive/50 bg-destructive/10';
            default: return 'text-muted-foreground border-border bg-muted/50';
        }
    };

    const getCategoryIcon = (category) => {
        switch (category) {
            case 'index_usage': return <Database className="w-4 h-4" />;
            case 'query_patterns': return <BarChart3 className="w-4 h-4" />;
            case 'partitioning': return <Layers className="w-4 h-4" />;
            case 'statistics_health': return <TrendingUp className="w-4 h-4" />;
            case 'anti_patterns': return <Shield className="w-4 h-4" />;
            default: return <CheckCircle className="w-4 h-4" />;
        }
    };

    const getCategoryName = (key) => {
        const names = {
            index_usage: 'Index Usage',
            query_patterns: 'Query Patterns',
            partitioning: 'Partitioning',
            statistics_health: 'Statistics Health',
            anti_patterns: 'Anti-Patterns'
        };
        return names[key] || key;
    };

    return (
        <div className="space-y-4" data-testid="maturity-score-panel">
            {/* Main Score Card */}
            <Card className={`border-2 ${getGradeColor(grade)}`}>
                <CardContent className="p-6">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <div className={`w-20 h-20 rounded-sm border-2 flex items-center justify-center ${getGradeColor(grade)}`}>
                                <span className="text-4xl font-bold">{grade}</span>
                            </div>
                            <div>
                                <p className="text-3xl font-bold">{total_score}<span className="text-lg text-muted-foreground">/100</span></p>
                                <p className="text-sm text-muted-foreground">Performance Maturity Score</p>
                            </div>
                        </div>
                        <Award className={`w-16 h-16 ${grade === 'A' ? 'text-success' : 'text-muted-foreground/30'}`} />
                    </div>
                    <p className="mt-4 text-sm">{assessment}</p>
                </CardContent>
            </Card>

            {/* Breakdown */}
            <div className="grid gap-3">
                {Object.entries(breakdown || {}).map(([key, cat]) => (
                    <Card key={key} className="bg-background border-border">
                        <CardContent className="p-4">
                            <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-2">
                                    {getCategoryIcon(key)}
                                    <span className="font-medium text-sm">{getCategoryName(key)}</span>
                                </div>
                                <span className="text-sm font-mono">
                                    {cat.score}/{cat.max}
                                </span>
                            </div>
                            <Progress 
                                value={(cat.score / cat.max) * 100} 
                                className="h-2 mb-2"
                            />
                            {cat.details?.map((detail, idx) => (
                                <p key={idx} className="text-xs text-muted-foreground">
                                    {detail}
                                </p>
                            ))}
                        </CardContent>
                    </Card>
                ))}
            </div>

            {/* Priority Actions */}
            {priority_actions?.length > 0 && (
                <Card className="bg-warning/5 border-warning/30">
                    <CardHeader className="p-4 pb-2">
                        <CardTitle className="text-sm flex items-center gap-2 text-warning">
                            <AlertTriangle className="w-4 h-4" />
                            Priority Actions
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="p-4 pt-2">
                        <ul className="space-y-1">
                            {priority_actions.map((action, idx) => (
                                <li key={idx} className="text-xs text-muted-foreground flex items-start gap-2">
                                    <span className="text-warning">•</span>
                                    {action}
                                </li>
                            ))}
                        </ul>
                    </CardContent>
                </Card>
            )}
        </div>
    );
};

export default MaturityScorePanel;
