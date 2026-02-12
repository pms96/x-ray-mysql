import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { 
    Database, 
    Zap, 
    BarChart3, 
    Code2, 
    ArrowRight,
    Shield,
    Layers,
    GitBranch,
    Activity
} from 'lucide-react';

const Landing = () => {
    const navigate = useNavigate();
    const { login, isAuthenticated } = useAuth();

    const handleGetStarted = () => {
        if (isAuthenticated) {
            navigate('/dashboard');
        } else {
            login();
        }
    };

    const features = [
        {
            icon: <Database className="w-5 h-5" />,
            title: 'Multi-Dialect Support',
            description: 'PostgreSQL, MySQL, SQL Server, BigQuery, Snowflake, Redshift, Athena, SQLite'
        },
        {
            icon: <Zap className="w-5 h-5" />,
            title: 'Performance Analysis',
            description: 'Analyze query cost, complexity, and scalability with AI-powered insights'
        },
        {
            icon: <BarChart3 className="w-5 h-5" />,
            title: 'Growth Simulation',
            description: 'See how your queries perform at 10x, 100x, 1000x data scale'
        },
        {
            icon: <Code2 className="w-5 h-5" />,
            title: 'Smart Refactoring',
            description: 'Get optimized query versions: pedagogical, performance, high-scale'
        },
        {
            icon: <Shield className="w-5 h-5" />,
            title: 'Anti-Pattern Detection',
            description: 'Catch SELECT *, missing indexes, correlated subqueries, and more'
        },
        {
            icon: <Layers className="w-5 h-5" />,
            title: 'Architecture Insights',
            description: 'Schema design recommendations for production-ready databases'
        }
    ];

    return (
        <div className="landing-hero" data-testid="landing-page">
            <div className="hero-grid" />
            
            {/* Header */}
            <header className="relative z-10 glass">
                <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-sm bg-primary/10 border border-primary/30 flex items-center justify-center">
                            <Activity className="w-5 h-5 text-primary" />
                        </div>
                        <div>
                            <h1 className="font-display text-lg font-bold tracking-tight">SQL X-RAY</h1>
                            <p className="text-[10px] text-muted-foreground uppercase tracking-widest">Performance Edition</p>
                        </div>
                    </div>
                    <Button 
                        onClick={handleGetStarted}
                        className="rounded-sm glow-primary"
                        data-testid="header-login-btn"
                    >
                        {isAuthenticated ? 'Go to Dashboard' : 'Sign In'}
                    </Button>
                </div>
            </header>

            {/* Hero Section */}
            <section className="relative z-10 max-w-7xl mx-auto px-6 pt-24 pb-16">
                <div className="grid lg:grid-cols-2 gap-16 items-center">
                    <div className="animate-fade-in">
                        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-sm bg-primary/10 border border-primary/30 text-primary text-xs font-medium mb-6">
                            <Zap className="w-3 h-3" />
                            AI-Powered SQL Performance Analysis
                        </div>
                        
                        <h2 className="font-display text-5xl lg:text-6xl font-bold tracking-tight mb-6 leading-tight">
                            Think Like a 
                            <span className="text-primary block">Senior DBA</span>
                        </h2>
                        
                        <p className="text-lg text-muted-foreground mb-8 max-w-xl leading-relaxed">
                            Not just a SQL tutor. A performance mentor for systems that handle 
                            <span className="text-foreground font-medium"> 500M+ rows</span>. 
                            Understand every query at the optimizer level.
                        </p>

                        <div className="flex flex-wrap gap-4">
                            <Button 
                                size="lg"
                                onClick={handleGetStarted}
                                className="rounded-sm glow-primary group"
                                data-testid="hero-get-started-btn"
                            >
                                {isAuthenticated ? 'Open Dashboard' : 'Get Started Free'}
                                <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
                            </Button>
                            <Button 
                                size="lg"
                                variant="outline"
                                className="rounded-sm"
                                data-testid="hero-learn-more-btn"
                                onClick={() => document.getElementById('features').scrollIntoView({ behavior: 'smooth' })}
                            >
                                Learn More
                            </Button>
                        </div>

                        {/* Stats */}
                        <div className="grid grid-cols-3 gap-6 mt-12 pt-8 border-t border-border">
                            <div>
                                <p className="text-2xl font-bold text-primary">8+</p>
                                <p className="text-xs text-muted-foreground">SQL Dialects</p>
                            </div>
                            <div>
                                <p className="text-2xl font-bold text-success">15+</p>
                                <p className="text-xs text-muted-foreground">Anti-Patterns</p>
                            </div>
                            <div>
                                <p className="text-2xl font-bold text-warning">1000x</p>
                                <p className="text-xs text-muted-foreground">Scale Simulation</p>
                            </div>
                        </div>
                    </div>

                    {/* Code Preview */}
                    <div className="animate-slide-in" style={{ animationDelay: '0.2s' }}>
                        <div className="bg-black rounded-sm border border-border overflow-hidden">
                            <div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-card">
                                <div className="w-3 h-3 rounded-full bg-destructive/50" />
                                <div className="w-3 h-3 rounded-full bg-warning/50" />
                                <div className="w-3 h-3 rounded-full bg-success/50" />
                                <span className="text-xs text-muted-foreground ml-2 font-mono">query.sql</span>
                            </div>
                            <pre className="p-4 text-sm font-mono overflow-x-auto">
<code className="text-foreground"><span className="text-[hsl(var(--syntax-keyword))]">SELECT</span> u.name, <span className="text-[hsl(var(--syntax-function))]">COUNT</span>(o.id) <span className="text-[hsl(var(--syntax-keyword))]">as</span> total_orders
<span className="text-[hsl(var(--syntax-keyword))]">FROM</span> users u
<span className="text-[hsl(var(--syntax-keyword))]">LEFT JOIN</span> orders o <span className="text-[hsl(var(--syntax-keyword))]">ON</span> u.id = o.user_id
<span className="text-[hsl(var(--syntax-keyword))]">WHERE</span> o.created_at {'>'} <span className="text-[hsl(var(--syntax-string))]">'2024-01-01'</span>
  <span className="text-[hsl(var(--syntax-keyword))]">AND</span> <span className="text-[hsl(var(--syntax-function))]">LOWER</span>(u.email) <span className="text-[hsl(var(--syntax-keyword))]">LIKE</span> <span className="text-[hsl(var(--syntax-string))]">'%@company.com'</span>
<span className="text-[hsl(var(--syntax-keyword))]">GROUP BY</span> u.id
<span className="text-[hsl(var(--syntax-keyword))]">ORDER BY</span> total_orders <span className="text-[hsl(var(--syntax-keyword))]">DESC</span></code>
                            </pre>
                            <div className="px-4 py-3 border-t border-border bg-card/50">
                                <div className="flex items-center gap-4 text-xs">
                                    <span className="flex items-center gap-1.5 text-warning">
                                        <span className="w-2 h-2 rounded-full bg-warning animate-pulse" />
                                        2 Anti-patterns detected
                                    </span>
                                    <span className="flex items-center gap-1.5 text-muted-foreground">
                                        <GitBranch className="w-3 h-3" />
                                        O(n log n)
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Features Section */}
            <section id="features" className="relative z-10 max-w-7xl mx-auto px-6 py-24">
                <div className="text-center mb-16">
                    <h3 className="font-display text-3xl font-bold mb-4">Performance Analysis Suite</h3>
                    <p className="text-muted-foreground max-w-2xl mx-auto">
                        Everything you need to understand, optimize, and scale your SQL queries for production workloads
                    </p>
                </div>

                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {features.map((feature, index) => (
                        <div 
                            key={index}
                            className="p-6 rounded-sm border border-border bg-card hover:border-primary/30 transition-colors duration-300 animate-fade-in"
                            style={{ animationDelay: `${index * 0.1}s` }}
                        >
                            <div className="w-10 h-10 rounded-sm bg-primary/10 border border-primary/30 flex items-center justify-center text-primary mb-4">
                                {feature.icon}
                            </div>
                            <h4 className="font-semibold mb-2">{feature.title}</h4>
                            <p className="text-sm text-muted-foreground leading-relaxed">{feature.description}</p>
                        </div>
                    ))}
                </div>
            </section>

            {/* CTA Section */}
            <section className="relative z-10 max-w-7xl mx-auto px-6 py-24">
                <div className="rounded-sm border border-primary/30 bg-primary/5 p-12 text-center">
                    <h3 className="font-display text-3xl font-bold mb-4">Ready to optimize your queries?</h3>
                    <p className="text-muted-foreground mb-8 max-w-xl mx-auto">
                        Start analyzing your SQL queries now. No credit card required.
                    </p>
                    <Button 
                        size="lg"
                        onClick={handleGetStarted}
                        className="rounded-sm glow-primary"
                        data-testid="cta-get-started-btn"
                    >
                        {isAuthenticated ? 'Go to Dashboard' : 'Get Started Free'}
                        <ArrowRight className="w-4 h-4 ml-2" />
                    </Button>
                </div>
            </section>

            {/* Footer */}
            <footer className="relative z-10 border-t border-border">
                <div className="max-w-7xl mx-auto px-6 py-8">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Activity className="w-4 h-4 text-primary" />
                            <span className="text-sm font-medium">SQL X-Ray</span>
                        </div>
                        <p className="text-xs text-muted-foreground">
                            Built for engineers who care about performance
                        </p>
                    </div>
                </div>
            </footer>
        </div>
    );
};

export default Landing;
