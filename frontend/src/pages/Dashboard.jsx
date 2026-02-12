import React, { useState, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '../components/ui/resizable';
import { Button } from '../components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '../components/ui/avatar';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { ScrollArea } from '../components/ui/scroll-area';
import { Badge } from '../components/ui/badge';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import { 
    Play, 
    Save, 
    History, 
    Settings, 
    LogOut, 
    Activity,
    Loader2,
    Database,
    Brain,
    TrendingUp,
    Award,
    FileText,
    Zap
} from 'lucide-react';
import SQLEditor from '../components/SQLEditor';
import ConfigPanel from '../components/ConfigPanel';
import OutputTabs from '../components/OutputTabs';
import DatabaseConnector from '../components/DatabaseConnector';
import DatabaseIntelligencePanel from '../components/DatabaseIntelligencePanel';
import GrowthSimulationPanel from '../components/GrowthSimulationPanel';
import MaturityScorePanel from '../components/MaturityScorePanel';
import ExecutiveReportPanel from '../components/ExecutiveReportPanel';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const Dashboard = () => {
    const { user, logout } = useAuth();
    const [query, setQuery] = useState(`-- SQL Tutor X-Ray Enterprise Edition
-- Connect to your MySQL 8 database for real-time analysis

SELECT 
    u.name,
    u.email,
    COUNT(o.id) as total_orders,
    SUM(o.amount) as total_spent,
    AVG(o.amount) as avg_order_value
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
WHERE o.created_at > '2024-01-01'
    AND o.status = 'completed'
GROUP BY u.id, u.name, u.email
HAVING total_orders > 5
ORDER BY total_spent DESC
LIMIT 100;`);
    
    const [dialect, setDialect] = useState('mysql');
    const [schemas, setSchemas] = useState([]);
    const [explainOutput, setExplainOutput] = useState('');
    const [mode, setMode] = useState('advanced');
    const [growthSimulation, setGrowthSimulation] = useState(null);
    
    // Database connection state
    const [connection, setConnection] = useState({
        host: '',
        port: 3306,
        user: '',
        password: '',
        database: '',
        ssl: true
    });
    const [isConnected, setIsConnected] = useState(false);
    
    // Analysis results
    const [analysisResult, setAnalysisResult] = useState(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [error, setError] = useState(null);
    
    // Enterprise modules results
    const [intelligenceData, setIntelligenceData] = useState(null);
    const [growthData, setGrowthData] = useState(null);
    const [maturityData, setMaturityData] = useState(null);
    const [reportData, setReportData] = useState(null);
    const [loadingModule, setLoadingModule] = useState(null);
    
    // Active enterprise tab
    const [enterpriseTab, setEnterpriseTab] = useState('query');

    const handleConnectionSuccess = (conn) => {
        setIsConnected(true);
        setConnection(conn);
    };

    const analyzeQuery = useCallback(async () => {
        if (!query.trim()) return;
        
        setIsAnalyzing(true);
        setError(null);
        
        try {
            const payload = {
                query,
                dialect,
                schemas,
                explain_output: explainOutput || null,
                mode,
                growth_simulation: growthSimulation
            };
            
            // Include connection if available
            if (isConnected && connection.host) {
                payload.connection = connection;
            }
            
            const response = await fetch(`${API_URL}/api/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(payload)
            });
            
            if (!response.ok) throw new Error('Analysis failed');
            
            const result = await response.json();
            setAnalysisResult(result);
            
            // Also run growth simulation if connected
            if (isConnected && connection.host) {
                runGrowthSimulation();
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setIsAnalyzing(false);
        }
    }, [query, dialect, schemas, explainOutput, mode, growthSimulation, isConnected, connection]);

    const runDatabaseIntelligence = async () => {
        if (!isConnected) return;
        setLoadingModule('intelligence');
        
        try {
            const response = await fetch(`${API_URL}/api/enterprise/intelligence`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(connection)
            });
            
            if (response.ok) {
                setIntelligenceData(await response.json());
            }
        } catch (err) {
            console.error('Intelligence analysis failed:', err);
        } finally {
            setLoadingModule(null);
        }
    };

    const runGrowthSimulation = async () => {
        if (!isConnected || !query.trim()) return;
        setLoadingModule('growth');
        
        try {
            const response = await fetch(`${API_URL}/api/enterprise/growth-simulation`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    connection,
                    query,
                    factors: [10, 100]
                })
            });
            
            if (response.ok) {
                setGrowthData(await response.json());
            }
        } catch (err) {
            console.error('Growth simulation failed:', err);
        } finally {
            setLoadingModule(null);
        }
    };

    const runMaturityScore = async () => {
        if (!isConnected) return;
        setLoadingModule('maturity');
        
        try {
            const response = await fetch(`${API_URL}/api/enterprise/maturity-score`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(connection)
            });
            
            if (response.ok) {
                setMaturityData(await response.json());
            }
        } catch (err) {
            console.error('Maturity score failed:', err);
        } finally {
            setLoadingModule(null);
        }
    };

    const runExecutiveReport = async () => {
        if (!isConnected) return;
        setLoadingModule('report');
        
        try {
            const response = await fetch(`${API_URL}/api/enterprise/executive-report`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(connection)
            });
            
            if (response.ok) {
                setReportData(await response.json());
            }
        } catch (err) {
            console.error('Executive report failed:', err);
        } finally {
            setLoadingModule(null);
        }
    };

    const saveQuery = async () => {
        try {
            await fetch(`${API_URL}/api/queries`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    query,
                    dialect,
                    schemas,
                    analysis_result: analysisResult
                })
            });
        } catch (err) {
            console.error('Save failed:', err);
        }
    };

    const getComplexityIndicator = () => {
        const lines = query.split('\n').filter(l => l.trim() && !l.trim().startsWith('--')).length;
        const hasSubquery = query.toLowerCase().includes('select') && query.toLowerCase().split('select').length > 2;
        const hasJoin = query.toLowerCase().includes('join');
        const hasWindow = query.toLowerCase().includes('over(') || query.toLowerCase().includes('over (');
        
        let complexity = 'Low';
        let color = 'text-success';
        
        if (hasWindow || (hasSubquery && hasJoin) || lines > 20) {
            complexity = 'High';
            color = 'text-warning';
        } else if (hasJoin || hasSubquery || lines > 10) {
            complexity = 'Medium';
            color = 'text-info';
        }
        
        return { complexity, color, lines };
    };

    const { complexity, color, lines } = getComplexityIndicator();

    return (
        <div className="dashboard-container" data-testid="dashboard-page">
            {/* Header */}
            <header className="dashboard-header flex items-center justify-between px-4">
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                        <Activity className="w-5 h-5 text-primary" />
                        <span className="font-display font-bold">SQL X-RAY</span>
                        <Badge variant="outline" className="text-[10px] text-primary border-primary/30">
                            ENTERPRISE
                        </Badge>
                    </div>
                    <div className="h-6 w-px bg-border" />
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span>{lines} lines</span>
                        <span className={`font-medium ${color}`}>{complexity}</span>
                    </div>
                    {isConnected && (
                        <>
                            <div className="h-6 w-px bg-border" />
                            <div className="flex items-center gap-1 text-xs">
                                <Database className="w-3 h-3 text-success" />
                                <span className="text-success">Connected</span>
                                <span className="text-muted-foreground">({connection.database})</span>
                            </div>
                        </>
                    )}
                </div>

                <div className="flex items-center gap-3">
                    <Button
                        size="sm"
                        variant="outline"
                        className="rounded-sm"
                        onClick={saveQuery}
                        disabled={!analysisResult}
                        data-testid="save-query-btn"
                    >
                        <Save className="w-4 h-4 mr-2" />
                        Save
                    </Button>
                    
                    <Button
                        size="sm"
                        className="rounded-sm glow-primary"
                        onClick={analyzeQuery}
                        disabled={isAnalyzing || !query.trim()}
                        data-testid="analyze-btn"
                    >
                        {isAnalyzing ? (
                            <>
                                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                Analyzing...
                            </>
                        ) : (
                            <>
                                <Play className="w-4 h-4 mr-2" />
                                Analyze
                            </>
                        )}
                    </Button>

                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="ghost" className="rounded-sm p-1" data-testid="user-menu-btn">
                                <Avatar className="w-8 h-8">
                                    <AvatarImage src={user?.picture} alt={user?.name} />
                                    <AvatarFallback className="bg-primary/10 text-primary text-xs">
                                        {user?.name?.charAt(0) || 'U'}
                                    </AvatarFallback>
                                </Avatar>
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-48">
                            <div className="px-2 py-1.5">
                                <p className="text-sm font-medium">{user?.name}</p>
                                <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
                            </div>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem onClick={() => window.location.href = '/history'}>
                                <History className="w-4 h-4 mr-2" />
                                Query History
                            </DropdownMenuItem>
                            <DropdownMenuItem>
                                <Settings className="w-4 h-4 mr-2" />
                                Settings
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem onClick={logout} className="text-destructive">
                                <LogOut className="w-4 h-4 mr-2" />
                                Log out
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>
            </header>

            {/* Main Content */}
            <main className="dashboard-main">
                <ResizablePanelGroup direction="horizontal">
                    {/* Left: SQL Editor */}
                    <ResizablePanel defaultSize={35} minSize={25}>
                        <div className="editor-panel">
                            <div className="editor-header">
                                <span className="panel-title">SQL Editor</span>
                                <Badge variant="outline" className="text-[10px]">MySQL 8</Badge>
                            </div>
                            <div className="editor-content">
                                <SQLEditor 
                                    value={query}
                                    onChange={setQuery}
                                    dialect={dialect}
                                />
                            </div>
                        </div>
                    </ResizablePanel>

                    <ResizableHandle />

                    {/* Center: Config + Enterprise Modules */}
                    <ResizablePanel defaultSize={25} minSize={20}>
                        <div className="h-full flex flex-col bg-card">
                            <Tabs value={enterpriseTab} onValueChange={setEnterpriseTab} className="h-full flex flex-col">
                                <TabsList className="w-full justify-start rounded-none border-b bg-background p-0 h-auto flex-shrink-0">
                                    <TabsTrigger value="query" className="tab-item rounded-none data-[state=active]:tab-active">
                                        <Database className="w-3 h-3 mr-1" />
                                        Query
                                    </TabsTrigger>
                                    <TabsTrigger value="connect" className="tab-item rounded-none data-[state=active]:tab-active">
                                        <Zap className="w-3 h-3 mr-1" />
                                        Connect
                                    </TabsTrigger>
                                    <TabsTrigger value="enterprise" className="tab-item rounded-none data-[state=active]:tab-active">
                                        <Brain className="w-3 h-3 mr-1" />
                                        Enterprise
                                    </TabsTrigger>
                                </TabsList>

                                <ScrollArea className="flex-1">
                                    <TabsContent value="query" className="m-0 p-0 h-full">
                                        <ConfigPanel
                                            dialect={dialect}
                                            setDialect={setDialect}
                                            schemas={schemas}
                                            setSchemas={setSchemas}
                                            explainOutput={explainOutput}
                                            setExplainOutput={setExplainOutput}
                                            mode={mode}
                                            setMode={setMode}
                                            growthSimulation={growthSimulation}
                                            setGrowthSimulation={setGrowthSimulation}
                                        />
                                    </TabsContent>

                                    <TabsContent value="connect" className="m-0 p-4">
                                        <DatabaseConnector
                                            connection={connection}
                                            setConnection={setConnection}
                                            onConnectionSuccess={handleConnectionSuccess}
                                        />
                                    </TabsContent>

                                    <TabsContent value="enterprise" className="m-0 p-4 space-y-4">
                                        {!isConnected ? (
                                            <div className="text-center py-8">
                                                <Database className="w-12 h-12 text-muted-foreground mx-auto mb-3" />
                                                <p className="text-muted-foreground text-sm">
                                                    Connect to a database to unlock Enterprise features
                                                </p>
                                                <Button
                                                    variant="outline"
                                                    className="mt-4 rounded-sm"
                                                    onClick={() => setEnterpriseTab('connect')}
                                                >
                                                    Configure Connection
                                                </Button>
                                            </div>
                                        ) : (
                                            <div className="space-y-3">
                                                <Button
                                                    variant="outline"
                                                    className="w-full justify-start rounded-sm"
                                                    onClick={runDatabaseIntelligence}
                                                    disabled={loadingModule === 'intelligence'}
                                                    data-testid="run-intelligence-btn"
                                                >
                                                    {loadingModule === 'intelligence' ? (
                                                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                                    ) : (
                                                        <Brain className="w-4 h-4 mr-2 text-primary" />
                                                    )}
                                                    Database Intelligence
                                                    <Badge variant="outline" className="ml-auto text-[10px]">Module 1</Badge>
                                                </Button>

                                                <Button
                                                    variant="outline"
                                                    className="w-full justify-start rounded-sm"
                                                    onClick={runGrowthSimulation}
                                                    disabled={loadingModule === 'growth' || !query.trim()}
                                                    data-testid="run-growth-btn"
                                                >
                                                    {loadingModule === 'growth' ? (
                                                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                                    ) : (
                                                        <TrendingUp className="w-4 h-4 mr-2 text-warning" />
                                                    )}
                                                    Growth Simulation
                                                    <Badge variant="outline" className="ml-auto text-[10px]">Module 3</Badge>
                                                </Button>

                                                <Button
                                                    variant="outline"
                                                    className="w-full justify-start rounded-sm"
                                                    onClick={runMaturityScore}
                                                    disabled={loadingModule === 'maturity'}
                                                    data-testid="run-maturity-btn"
                                                >
                                                    {loadingModule === 'maturity' ? (
                                                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                                    ) : (
                                                        <Award className="w-4 h-4 mr-2 text-success" />
                                                    )}
                                                    Maturity Score
                                                    <Badge variant="outline" className="ml-auto text-[10px]">Module 5</Badge>
                                                </Button>

                                                <Button
                                                    variant="outline"
                                                    className="w-full justify-start rounded-sm"
                                                    onClick={runExecutiveReport}
                                                    disabled={loadingModule === 'report'}
                                                    data-testid="run-report-btn"
                                                >
                                                    {loadingModule === 'report' ? (
                                                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                                    ) : (
                                                        <FileText className="w-4 h-4 mr-2 text-info" />
                                                    )}
                                                    Executive Report
                                                    <Badge variant="outline" className="ml-auto text-[10px]">Module 6</Badge>
                                                </Button>
                                            </div>
                                        )}
                                    </TabsContent>
                                </ScrollArea>
                            </Tabs>
                        </div>
                    </ResizablePanel>

                    <ResizableHandle />

                    {/* Right: Output Tabs + Enterprise Results */}
                    <ResizablePanel defaultSize={40} minSize={30}>
                        <div className="h-full flex flex-col bg-card">
                            <Tabs defaultValue="analysis" className="h-full flex flex-col">
                                <TabsList className="w-full justify-start rounded-none border-b bg-background p-0 h-auto flex-shrink-0">
                                    <TabsTrigger value="analysis" className="tab-item rounded-none data-[state=active]:tab-active">
                                        Query Analysis
                                    </TabsTrigger>
                                    <TabsTrigger value="intelligence" className="tab-item rounded-none data-[state=active]:tab-active">
                                        Intelligence
                                        {intelligenceData && (
                                            <span className="ml-1 w-2 h-2 rounded-full bg-primary" />
                                        )}
                                    </TabsTrigger>
                                    <TabsTrigger value="growth" className="tab-item rounded-none data-[state=active]:tab-active">
                                        Growth
                                        {growthData && (
                                            <span className="ml-1 w-2 h-2 rounded-full bg-warning" />
                                        )}
                                    </TabsTrigger>
                                    <TabsTrigger value="maturity" className="tab-item rounded-none data-[state=active]:tab-active">
                                        Maturity
                                        {maturityData && (
                                            <span className="ml-1 w-2 h-2 rounded-full bg-success" />
                                        )}
                                    </TabsTrigger>
                                    <TabsTrigger value="report" className="tab-item rounded-none data-[state=active]:tab-active">
                                        Report
                                        {reportData && (
                                            <span className="ml-1 w-2 h-2 rounded-full bg-info" />
                                        )}
                                    </TabsTrigger>
                                </TabsList>

                                <TabsContent value="analysis" className="flex-1 m-0 overflow-hidden">
                                    <OutputTabs 
                                        result={analysisResult}
                                        isLoading={isAnalyzing}
                                        error={error}
                                    />
                                </TabsContent>

                                <TabsContent value="intelligence" className="flex-1 m-0 p-4 overflow-auto">
                                    <DatabaseIntelligencePanel data={intelligenceData} />
                                </TabsContent>

                                <TabsContent value="growth" className="flex-1 m-0 p-4 overflow-auto">
                                    <GrowthSimulationPanel data={growthData} />
                                </TabsContent>

                                <TabsContent value="maturity" className="flex-1 m-0 p-4 overflow-auto">
                                    <MaturityScorePanel data={maturityData} />
                                </TabsContent>

                                <TabsContent value="report" className="flex-1 m-0 p-4 overflow-auto">
                                    <ExecutiveReportPanel data={reportData} />
                                </TabsContent>
                            </Tabs>
                        </div>
                    </ResizablePanel>
                </ResizablePanelGroup>
            </main>
        </div>
    );
};

export default Dashboard;
