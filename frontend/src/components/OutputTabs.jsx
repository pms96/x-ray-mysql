import React, { useState, useEffect, useRef } from 'react';
import { ScrollArea } from './ui/scroll-area';
import { Badge } from './ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { 
    Eye, 
    GitBranch, 
    Code2, 
    Wrench, 
    TrendingUp, 
    Layers, 
    TestTube2, 
    Network,
    AlertTriangle,
    AlertCircle,
    Info,
    CheckCircle,
    Copy,
    Check,
    Loader2
} from 'lucide-react';
import { Button } from './ui/button';
import mermaid from 'mermaid';

// Initialize mermaid
mermaid.initialize({
    startOnLoad: false,
    theme: 'dark',
    themeVariables: {
        primaryColor: '#3B82F6',
        primaryTextColor: '#EDEDED',
        primaryBorderColor: '#262626',
        lineColor: '#52525B',
        secondaryColor: '#0A0A0A',
        tertiaryColor: '#0F0F0F'
    }
});

const OutputTabs = ({ result, isLoading, error }) => {
    const [activeTab, setActiveTab] = useState('overview');
    const [copiedCode, setCopiedCode] = useState(null);
    const mermaidRef = useRef(null);

    useEffect(() => {
        if (result?.mermaid_diagram && mermaidRef.current && activeTab === 'diagram') {
            const renderMermaid = async () => {
                try {
                    mermaidRef.current.innerHTML = '';
                    const { svg } = await mermaid.render('mermaid-diagram', result.mermaid_diagram);
                    mermaidRef.current.innerHTML = svg;
                } catch (err) {
                    console.error('Mermaid render error:', err);
                    mermaidRef.current.innerHTML = `<p class="text-destructive text-sm">Error rendering diagram</p>`;
                }
            };
            renderMermaid();
        }
    }, [result, activeTab]);

    const copyCode = (code, id) => {
        navigator.clipboard.writeText(code);
        setCopiedCode(id);
        setTimeout(() => setCopiedCode(null), 2000);
    };

    const AlertIcon = ({ type }) => {
        switch (type) {
            case 'error':
                return <AlertCircle className="w-4 h-4 text-destructive" />;
            case 'warning':
                return <AlertTriangle className="w-4 h-4 text-warning" />;
            case 'info':
                return <Info className="w-4 h-4 text-info" />;
            default:
                return <CheckCircle className="w-4 h-4 text-success" />;
        }
    };

    const SeverityBadge = ({ severity }) => {
        const colors = {
            low: 'status-low',
            medium: 'status-medium',
            high: 'status-high',
            critical: 'status-critical'
        };
        return (
            <span className={`complexity-badge border ${colors[severity] || colors.medium}`}>
                {severity}
            </span>
        );
    };

    const CodeBlock = ({ code, id, title }) => (
        <div className="relative">
            {title && <p className="text-xs text-muted-foreground mb-2">{title}</p>}
            <div className="code-block relative group">
                <Button
                    variant="ghost"
                    size="icon"
                    className="absolute top-2 right-2 h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={() => copyCode(code, id)}
                >
                    {copiedCode === id ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                </Button>
                <pre className="text-xs overflow-x-auto whitespace-pre-wrap">{code}</pre>
            </div>
        </div>
    );

    if (isLoading) {
        return (
            <div className="output-panel flex items-center justify-center" data-testid="output-loading">
                <div className="text-center">
                    <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto mb-4" />
                    <p className="text-muted-foreground">Analyzing query...</p>
                    <p className="text-xs text-muted-foreground mt-2">This may take a few seconds</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="output-panel flex items-center justify-center" data-testid="output-error">
                <div className="text-center">
                    <AlertCircle className="w-8 h-8 text-destructive mx-auto mb-4" />
                    <p className="text-destructive">Analysis failed</p>
                    <p className="text-xs text-muted-foreground mt-2">{error}</p>
                </div>
            </div>
        );
    }

    if (!result) {
        return (
            <div className="output-panel flex items-center justify-center" data-testid="output-empty">
                <div className="text-center max-w-sm">
                    <Eye className="w-8 h-8 text-muted-foreground mx-auto mb-4" />
                    <p className="text-muted-foreground mb-2">No analysis yet</p>
                    <p className="text-xs text-muted-foreground">
                        Write a SQL query and click <span className="text-primary">Analyze</span> to see performance insights
                    </p>
                </div>
            </div>
        );
    }

    const tabs = [
        { id: 'overview', label: 'Overview', icon: <Eye className="w-3 h-3" /> },
        { id: 'order', label: 'Order', icon: <GitBranch className="w-3 h-3" /> },
        { id: 'technical', label: 'Technical', icon: <Code2 className="w-3 h-3" /> },
        { id: 'refactor', label: 'Refactor', icon: <Wrench className="w-3 h-3" /> },
        { id: 'scalability', label: 'Scale', icon: <TrendingUp className="w-3 h-3" /> },
        { id: 'architecture', label: 'Arch', icon: <Layers className="w-3 h-3" /> },
        { id: 'testing', label: 'Test', icon: <TestTube2 className="w-3 h-3" /> },
        { id: 'diagram', label: 'Diagram', icon: <Network className="w-3 h-3" /> },
    ];

    return (
        <div className="output-panel" data-testid="output-panel">
            <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
                <TabsList className="output-tabs w-full justify-start rounded-none border-b bg-background p-0 h-auto">
                    {tabs.map((tab) => (
                        <TabsTrigger
                            key={tab.id}
                            value={tab.id}
                            className="tab-item rounded-none data-[state=active]:tab-active"
                            data-testid={`tab-${tab.id}`}
                        >
                            {tab.icon}
                            <span className="ml-1.5">{tab.label}</span>
                        </TabsTrigger>
                    ))}
                </TabsList>

                <ScrollArea className="flex-1">
                    {/* Overview Tab */}
                    <TabsContent value="overview" className="output-content m-0 animate-fade-in">
                        {result.overview && (
                            <div className="space-y-6">
                                <div>
                                    <h3 className="section-header">Summary</h3>
                                    <p className="text-sm leading-relaxed">{result.overview.summary}</p>
                                </div>

                                {result.overview.granularity && (
                                    <div>
                                        <h3 className="section-header">Granularity</h3>
                                        <p className="text-sm text-muted-foreground">{result.overview.granularity}</p>
                                    </div>
                                )}

                                {result.overview.final_columns?.length > 0 && (
                                    <div>
                                        <h3 className="section-header">Output Columns</h3>
                                        <div className="flex flex-wrap gap-2">
                                            {result.overview.final_columns.map((col, i) => (
                                                <Badge key={i} variant="secondary" className="font-mono text-xs">
                                                    {col}
                                                </Badge>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {result.overview.alerts?.length > 0 && (
                                    <div>
                                        <h3 className="section-header">Alerts</h3>
                                        <div className="space-y-2">
                                            {result.overview.alerts.map((alert, i) => (
                                                <div key={i} className={`alert-card alert-${alert.type}`}>
                                                    <div className="flex items-start gap-3">
                                                        <AlertIcon type={alert.type} />
                                                        <div className="flex-1">
                                                            <p className="text-sm">{alert.message}</p>
                                                        </div>
                                                        <SeverityBadge severity={alert.severity} />
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {result.overview.facts_vs_assumptions && (
                                    <div className="grid md:grid-cols-2 gap-4">
                                        <div>
                                            <h3 className="section-header text-success">Facts (from SQL)</h3>
                                            <ul className="text-sm space-y-1">
                                                {result.overview.facts_vs_assumptions.facts?.map((fact, i) => (
                                                    <li key={i} className="flex items-start gap-2">
                                                        <CheckCircle className="w-3 h-3 text-success mt-1 flex-shrink-0" />
                                                        {fact}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                        <div>
                                            <h3 className="section-header text-warning">Assumptions (missing stats)</h3>
                                            <ul className="text-sm space-y-1">
                                                {result.overview.facts_vs_assumptions.assumptions?.map((assumption, i) => (
                                                    <li key={i} className="flex items-start gap-2">
                                                        <Info className="w-3 h-3 text-warning mt-1 flex-shrink-0" />
                                                        {assumption}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </TabsContent>

                    {/* Logical vs Physical Order Tab */}
                    <TabsContent value="order" className="output-content m-0 animate-fade-in">
                        {result.logical_vs_physical_order && (
                            <div className="space-y-6">
                                <div>
                                    <h3 className="section-header">Logical Execution Order</h3>
                                    <div className="space-y-2">
                                        {result.logical_vs_physical_order.logical_order?.map((step, i) => (
                                            <div key={i} className="flex items-start gap-3 p-3 bg-background rounded-sm border border-border">
                                                <span className="w-6 h-6 rounded-sm bg-primary/10 text-primary text-xs font-bold flex items-center justify-center">
                                                    {step.step}
                                                </span>
                                                <div>
                                                    <p className="font-mono text-sm font-medium text-primary">{step.operation}</p>
                                                    <p className="text-xs text-muted-foreground mt-1">{step.description}</p>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                {result.logical_vs_physical_order.optimizer_optimizations?.length > 0 && (
                                    <div>
                                        <h3 className="section-header">Optimizer Optimizations</h3>
                                        <div className="space-y-2">
                                            {result.logical_vs_physical_order.optimizer_optimizations.map((opt, i) => (
                                                <div key={i} className="p-3 bg-background rounded-sm border border-border">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span className="font-medium text-sm">{opt.optimization}</span>
                                                        {opt.dialect_specific && (
                                                            <Badge variant="outline" className="text-[10px]">Dialect-specific</Badge>
                                                        )}
                                                    </div>
                                                    <p className="text-xs text-muted-foreground">{opt.description}</p>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </TabsContent>

                    {/* Technical Breakdown Tab */}
                    <TabsContent value="technical" className="output-content m-0 animate-fade-in">
                        {result.technical_breakdown && (
                            <div className="space-y-6">
                                {result.technical_breakdown.select && (
                                    <div>
                                        <h3 className="section-header">SELECT Analysis</h3>
                                        {result.technical_breakdown.select.expressions?.length > 0 && (
                                            <div className="mb-3">
                                                <p className="text-xs text-muted-foreground mb-2">Expressions:</p>
                                                <div className="flex flex-wrap gap-2">
                                                    {result.technical_breakdown.select.expressions.map((expr, i) => (
                                                        <Badge key={i} variant="secondary" className="font-mono text-xs">{expr}</Badge>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                        {result.technical_breakdown.select.row_by_row_impact && (
                                            <p className="text-sm text-muted-foreground">{result.technical_breakdown.select.row_by_row_impact}</p>
                                        )}
                                    </div>
                                )}

                                {result.technical_breakdown.joins?.length > 0 && (
                                    <div>
                                        <h3 className="section-header">JOINs Analysis</h3>
                                        <div className="space-y-3">
                                            {result.technical_breakdown.joins.map((join, i) => (
                                                <div key={i} className="p-3 bg-background rounded-sm border border-border">
                                                    <div className="flex items-center gap-2 mb-2">
                                                        <Badge className="bg-primary/10 text-primary">{join.type}</Badge>
                                                        <span className="font-mono text-sm">{join.tables?.join(' ⟷ ')}</span>
                                                    </div>
                                                    {join.keys && (
                                                        <p className="text-xs text-muted-foreground mb-2">Keys: <span className="font-mono">{join.keys.join(', ')}</span></p>
                                                    )}
                                                    {join.risks?.length > 0 && (
                                                        <div className="flex flex-wrap gap-1">
                                                            {join.risks.map((risk, j) => (
                                                                <Badge key={j} variant="destructive" className="text-[10px]">{risk}</Badge>
                                                            ))}
                                                        </div>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {result.technical_breakdown.where && (
                                    <div>
                                        <h3 className="section-header">WHERE Analysis</h3>
                                        {result.technical_breakdown.where.sargable_analysis?.length > 0 && (
                                            <div className="space-y-1">
                                                {result.technical_breakdown.where.sargable_analysis.map((item, i) => (
                                                    <p key={i} className="text-sm text-muted-foreground">{item}</p>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}

                                {result.technical_breakdown.subqueries?.length > 0 && (
                                    <div>
                                        <h3 className="section-header">Subqueries</h3>
                                        <div className="space-y-2">
                                            {result.technical_breakdown.subqueries.map((sq, i) => (
                                                <div key={i} className="alert-card alert-warning">
                                                    <p className="text-sm font-medium">{sq.type}</p>
                                                    <p className="text-xs text-muted-foreground mt-1">{sq.risk}</p>
                                                    {sq.rewrite_suggestion && (
                                                        <p className="text-xs text-success mt-2">Suggestion: {sq.rewrite_suggestion}</p>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </TabsContent>

                    {/* Refactor Tab */}
                    <TabsContent value="refactor" className="output-content m-0 animate-fade-in">
                        {result.refactor_suggestions && (
                            <div className="space-y-6">
                                {result.refactor_suggestions.pedagogical && (
                                    <div>
                                        <h3 className="section-header text-info">Pedagogical (Clear CTEs)</h3>
                                        <p className="text-xs text-muted-foreground mb-3">{result.refactor_suggestions.pedagogical.explanation}</p>
                                        <CodeBlock 
                                            code={result.refactor_suggestions.pedagogical.query} 
                                            id="pedagogical"
                                        />
                                    </div>
                                )}

                                {result.refactor_suggestions.performance_optimized && (
                                    <div>
                                        <h3 className="section-header text-success">Performance Optimized</h3>
                                        <p className="text-xs text-muted-foreground mb-3">{result.refactor_suggestions.performance_optimized.explanation}</p>
                                        <CodeBlock 
                                            code={result.refactor_suggestions.performance_optimized.query} 
                                            id="performance"
                                        />
                                    </div>
                                )}

                                {result.refactor_suggestions.high_scale && (
                                    <div>
                                        <h3 className="section-header text-warning">High Scale Ready</h3>
                                        <p className="text-xs text-muted-foreground mb-3">{result.refactor_suggestions.high_scale.explanation}</p>
                                        <CodeBlock 
                                            code={result.refactor_suggestions.high_scale.query} 
                                            id="highscale"
                                        />
                                    </div>
                                )}
                            </div>
                        )}
                    </TabsContent>

                    {/* Scalability Tab */}
                    <TabsContent value="scalability" className="output-content m-0 animate-fade-in">
                        {result.cost_scalability && (
                            <div className="space-y-6">
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="p-4 bg-background rounded-sm border border-border">
                                        <p className="text-xs text-muted-foreground mb-1">Estimated Cost</p>
                                        <p className="text-lg font-bold">
                                            <SeverityBadge severity={result.cost_scalability.estimated_cost} />
                                        </p>
                                    </div>
                                    <div className="p-4 bg-background rounded-sm border border-border">
                                        <p className="text-xs text-muted-foreground mb-1">Complexity</p>
                                        <p className="text-lg font-mono font-bold text-primary">{result.cost_scalability.complexity}</p>
                                    </div>
                                </div>

                                {result.cost_scalability.worst_scaling_part && (
                                    <div className="alert-card alert-warning">
                                        <p className="text-sm font-medium">Worst Scaling Part</p>
                                        <p className="text-xs mt-1">{result.cost_scalability.worst_scaling_part}</p>
                                    </div>
                                )}

                                {result.cost_scalability.growth_simulation && (
                                    <div>
                                        <h3 className="section-header">Growth Simulation</h3>
                                        <div className="space-y-2">
                                            {Object.entries(result.cost_scalability.growth_simulation).map(([scale, impact]) => (
                                                <div key={scale} className="flex items-center justify-between p-3 bg-background rounded-sm border border-border">
                                                    <span className="font-mono text-sm">{scale.replace(/_/g, ' → ')}</span>
                                                    <span className="text-xs text-muted-foreground max-w-[60%] text-right">{impact}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {result.cost_scalability.index_recommendations?.length > 0 && (
                                    <div>
                                        <h3 className="section-header text-success">Index Recommendations</h3>
                                        <div className="space-y-2">
                                            {result.cost_scalability.index_recommendations.map((idx, i) => (
                                                <div key={i} className="p-3 bg-background rounded-sm border border-success/30">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span className="font-mono text-sm">{idx.table}</span>
                                                        <Badge variant="outline" className="text-[10px]">{idx.type}</Badge>
                                                    </div>
                                                    <p className="font-mono text-xs text-primary mb-1">({idx.columns?.join(', ')})</p>
                                                    <p className="text-xs text-muted-foreground">{idx.reason}</p>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </TabsContent>

                    {/* Architecture Tab */}
                    <TabsContent value="architecture" className="output-content m-0 animate-fade-in">
                        {result.architecture && (
                            <div className="space-y-6">
                                {result.architecture.missing_pk?.length > 0 && (
                                    <div className="alert-card alert-error">
                                        <p className="text-sm font-medium">Missing Primary Keys</p>
                                        <div className="flex flex-wrap gap-1 mt-2">
                                            {result.architecture.missing_pk.map((table, i) => (
                                                <Badge key={i} variant="destructive">{table}</Badge>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {result.architecture.missing_fk_indexes?.length > 0 && (
                                    <div className="alert-card alert-warning">
                                        <p className="text-sm font-medium">Missing FK Indexes</p>
                                        <div className="flex flex-wrap gap-1 mt-2">
                                            {result.architecture.missing_fk_indexes.map((fk, i) => (
                                                <Badge key={i} variant="outline">{fk}</Badge>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {result.architecture.recommendations?.length > 0 && (
                                    <div>
                                        <h3 className="section-header">Recommendations</h3>
                                        <ul className="space-y-2">
                                            {result.architecture.recommendations.map((rec, i) => (
                                                <li key={i} className="flex items-start gap-2 text-sm">
                                                    <Layers className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
                                                    {rec}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>
                        )}
                    </TabsContent>

                    {/* Testing Tab */}
                    <TabsContent value="testing" className="output-content m-0 animate-fade-in">
                        {result.testing_validation && (
                            <div className="space-y-6">
                                {result.testing_validation.validation_queries?.length > 0 && (
                                    <div>
                                        <h3 className="section-header">Validation Queries</h3>
                                        <div className="space-y-4">
                                            {result.testing_validation.validation_queries.map((vq, i) => (
                                                <div key={i}>
                                                    <p className="text-xs text-muted-foreground mb-2">{vq.purpose}</p>
                                                    <CodeBlock code={vq.query} id={`validation-${i}`} />
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {result.testing_validation.stress_test_suggestions?.length > 0 && (
                                    <div>
                                        <h3 className="section-header">Stress Test Suggestions</h3>
                                        <ul className="space-y-2">
                                            {result.testing_validation.stress_test_suggestions.map((test, i) => (
                                                <li key={i} className="flex items-start gap-2 text-sm">
                                                    <TestTube2 className="w-4 h-4 text-info mt-0.5 flex-shrink-0" />
                                                    {test}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>
                        )}
                    </TabsContent>

                    {/* Diagram Tab */}
                    <TabsContent value="diagram" className="output-content m-0 animate-fade-in">
                        <div>
                            <h3 className="section-header">Query Flow Diagram</h3>
                            <div 
                                ref={mermaidRef} 
                                className="p-4 bg-background rounded-sm border border-border min-h-[200px] flex items-center justify-center"
                                data-testid="mermaid-diagram"
                            >
                                {!result.mermaid_diagram && (
                                    <p className="text-muted-foreground text-sm">No diagram available</p>
                                )}
                            </div>
                        </div>

                        {/* Anti-patterns */}
                        {result.anti_patterns_detected?.length > 0 && (
                            <div className="mt-6">
                                <h3 className="section-header text-destructive">Anti-Patterns Detected</h3>
                                <div className="space-y-2">
                                    {result.anti_patterns_detected.map((ap, i) => (
                                        <div key={i} className="alert-card alert-error">
                                            <div className="flex items-start justify-between gap-4">
                                                <div>
                                                    <p className="font-medium text-sm">{ap.pattern}</p>
                                                    <p className="text-xs text-muted-foreground mt-1">Location: {ap.location}</p>
                                                    <p className="text-xs text-success mt-2">Fix: {ap.fix}</p>
                                                </div>
                                                <SeverityBadge severity={ap.severity} />
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </TabsContent>
                </ScrollArea>
            </Tabs>
        </div>
    );
};

export default OutputTabs;
