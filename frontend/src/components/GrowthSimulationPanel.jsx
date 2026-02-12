import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { 
    TrendingUp,
    TrendingDown,
    AlertTriangle,
    CheckCircle,
    Clock,
    Zap
} from 'lucide-react';

const GrowthSimulationPanel = ({ data }) => {
    if (!data || data.error) {
        return (
            <div className="text-center py-8 text-muted-foreground">
                {data?.error ? `Error: ${data.error}` : 'Run analysis with a query to see growth simulation'}
            </div>
        );
    }

    const { simulations, overall_scalability, critical_bottlenecks } = data;

    const getScalabilityColor = (score) => {
        if (score >= 80) return 'text-success';
        if (score >= 60) return 'text-warning';
        if (score >= 40) return 'text-orange-400';
        return 'text-destructive';
    };

    const getProgressColor = (score) => {
        if (score >= 80) return 'bg-success';
        if (score >= 60) return 'bg-warning';
        if (score >= 40) return 'bg-orange-500';
        return 'bg-destructive';
    };

    return (
        <div className="space-y-4" data-testid="growth-simulation-panel">
            {/* Overall Score */}
            <Card className="bg-background border-border">
                <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                            <Zap className="w-5 h-5 text-primary" />
                            <span className="font-medium">Overall Scalability</span>
                        </div>
                        <span className={`text-2xl font-bold ${getScalabilityColor(overall_scalability)}`}>
                            {overall_scalability}%
                        </span>
                    </div>
                    <Progress 
                        value={overall_scalability} 
                        className="h-2"
                    />
                    {critical_bottlenecks?.length > 0 && (
                        <div className="mt-3 flex items-center gap-2 text-xs text-destructive">
                            <AlertTriangle className="w-3 h-3" />
                            Critical bottlenecks: {critical_bottlenecks.join(', ')}
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Simulation Results */}
            <div className="grid gap-4">
                {Object.entries(simulations || {}).map(([scale, sim]) => (
                    <Card key={scale} className="bg-background border-border">
                        <CardHeader className="p-4 pb-2">
                            <div className="flex items-center justify-between">
                                <CardTitle className="text-lg flex items-center gap-2">
                                    <TrendingUp className="w-5 h-5 text-primary" />
                                    {scale} Growth
                                </CardTitle>
                                <div className="flex items-center gap-3">
                                    <Badge 
                                        variant="outline" 
                                        className={`${getScalabilityColor(sim.scalability_score)} border-current`}
                                    >
                                        Score: {sim.scalability_score}%
                                    </Badge>
                                    <div className="flex items-center gap-1 text-sm">
                                        <Clock className="w-4 h-4 text-muted-foreground" />
                                        <span className={sim.estimated_time_increase > 100 ? 'text-destructive' : 'text-muted-foreground'}>
                                            ~{sim.estimated_time_increase}x slower
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent className="p-4 pt-2">
                            {/* Tables Analysis */}
                            <div className="space-y-2 mb-4">
                                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Tables Impact</p>
                                {sim.tables?.map((table, idx) => (
                                    <div 
                                        key={idx} 
                                        className={`p-2 rounded-sm border text-xs ${
                                            table.risk_level === 'critical' ? 'bg-destructive/5 border-destructive/20' :
                                            table.risk_level === 'high' ? 'bg-orange-500/5 border-orange-500/20' :
                                            table.risk_level === 'medium' ? 'bg-warning/5 border-warning/20' :
                                            'bg-muted/30 border-border'
                                        }`}
                                    >
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-2">
                                                <span className="font-mono font-medium">{table.table}</span>
                                                <Badge variant="outline" className="text-[10px]">
                                                    {table.access_type}
                                                </Badge>
                                            </div>
                                            <div className="flex items-center gap-3 text-muted-foreground">
                                                <span>{table.current_rows?.toLocaleString()} → {table.projected_rows?.toLocaleString()}</span>
                                                <span className={`font-medium ${
                                                    table.risk_level === 'critical' ? 'text-destructive' :
                                                    table.risk_level === 'high' ? 'text-orange-400' :
                                                    table.risk_level === 'medium' ? 'text-warning' :
                                                    'text-success'
                                                }`}>
                                                    {table.time_complexity_factor}x
                                                </span>
                                            </div>
                                        </div>
                                        <p className="text-muted-foreground mt-1">{table.risk_message}</p>
                                    </div>
                                ))}
                            </div>

                            {/* Risks */}
                            {sim.risks?.length > 0 && (
                                <div className="space-y-2">
                                    <p className="text-xs font-medium text-destructive uppercase tracking-wider">Risks</p>
                                    {sim.risks.map((risk, idx) => (
                                        <div key={idx} className="p-2 rounded-sm bg-destructive/10 border border-destructive/20 text-xs">
                                            <div className="flex items-start gap-2">
                                                <AlertTriangle className="w-4 h-4 text-destructive flex-shrink-0 mt-0.5" />
                                                <div>
                                                    <p className="font-medium text-destructive">{risk.message}</p>
                                                    <p className="text-muted-foreground mt-1">→ {risk.recommendation}</p>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {sim.risks?.length === 0 && (
                                <div className="flex items-center gap-2 text-xs text-success">
                                    <CheckCircle className="w-4 h-4" />
                                    Query should scale reasonably at {scale}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                ))}
            </div>
        </div>
    );
};

export default GrowthSimulationPanel;
