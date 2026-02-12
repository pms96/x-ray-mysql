import React, { useState, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '../components/ui/resizable';
import { Button } from '../components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '../components/ui/avatar';
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
    Loader2
} from 'lucide-react';
import SQLEditor from '../components/SQLEditor';
import ConfigPanel from '../components/ConfigPanel';
import OutputTabs from '../components/OutputTabs';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const Dashboard = () => {
    const { user, logout } = useAuth();
    const [query, setQuery] = useState(`-- Write your SQL query here
SELECT 
    u.name,
    u.email,
    COUNT(o.id) as total_orders,
    SUM(o.amount) as total_spent
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
WHERE o.created_at > '2024-01-01'
GROUP BY u.id, u.name, u.email
ORDER BY total_spent DESC
LIMIT 100;`);
    
    const [dialect, setDialect] = useState('postgresql');
    const [schemas, setSchemas] = useState([]);
    const [explainOutput, setExplainOutput] = useState('');
    const [mode, setMode] = useState('advanced');
    const [growthSimulation, setGrowthSimulation] = useState(null);
    
    const [analysisResult, setAnalysisResult] = useState(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [error, setError] = useState(null);

    const analyzeQuery = useCallback(async () => {
        if (!query.trim()) return;
        
        setIsAnalyzing(true);
        setError(null);
        
        try {
            const response = await fetch(`${API_URL}/api/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    query,
                    dialect,
                    schemas,
                    explain_output: explainOutput || null,
                    mode,
                    growth_simulation: growthSimulation
                })
            });
            
            if (!response.ok) {
                throw new Error('Analysis failed');
            }
            
            const result = await response.json();
            setAnalysisResult(result);
        } catch (err) {
            setError(err.message);
            console.error('Analysis error:', err);
        } finally {
            setIsAnalyzing(false);
        }
    }, [query, dialect, schemas, explainOutput, mode, growthSimulation]);

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
                    </div>
                    <div className="h-6 w-px bg-border" />
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span>{lines} lines</span>
                        <span className={`font-medium ${color}`}>{complexity}</span>
                    </div>
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
                            <DropdownMenuItem 
                                onClick={() => window.location.href = '/history'}
                                data-testid="history-menu-item"
                            >
                                <History className="w-4 h-4 mr-2" />
                                Query History
                            </DropdownMenuItem>
                            <DropdownMenuItem data-testid="settings-menu-item">
                                <Settings className="w-4 h-4 mr-2" />
                                Settings
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem 
                                onClick={logout}
                                className="text-destructive"
                                data-testid="logout-menu-item"
                            >
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
                                <span className="text-xs text-muted-foreground font-mono">{dialect}</span>
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

                    {/* Center: Config Panel */}
                    <ResizablePanel defaultSize={25} minSize={20}>
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
                    </ResizablePanel>

                    <ResizableHandle />

                    {/* Right: Output Tabs */}
                    <ResizablePanel defaultSize={40} minSize={30}>
                        <OutputTabs 
                            result={analysisResult}
                            isLoading={isAnalyzing}
                            error={error}
                        />
                    </ResizablePanel>
                </ResizablePanelGroup>
            </main>
        </div>
    );
};

export default Dashboard;
