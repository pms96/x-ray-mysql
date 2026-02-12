import React, { useState } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Switch } from './ui/switch';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Alert, AlertDescription } from './ui/alert';
import { 
    Database, 
    Loader2, 
    CheckCircle, 
    XCircle, 
    Server,
    Lock,
    Eye,
    EyeOff
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const DatabaseConnector = ({ onConnectionSuccess, connection, setConnection }) => {
    const [testing, setTesting] = useState(false);
    const [testResult, setTestResult] = useState(null);
    const [showPassword, setShowPassword] = useState(false);

    const testConnection = async () => {
        setTesting(true);
        setTestResult(null);
        
        try {
            const response = await fetch(`${API_URL}/api/db/test-connection`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(connection)
            });
            
            if (response.ok) {
                const data = await response.json();
                setTestResult({ success: true, data });
                onConnectionSuccess?.(connection);
            } else {
                const error = await response.json();
                setTestResult({ success: false, error: error.detail });
            }
        } catch (err) {
            setTestResult({ success: false, error: err.message });
        } finally {
            setTesting(false);
        }
    };

    const updateConnection = (field, value) => {
        setConnection(prev => ({ ...prev, [field]: value }));
        setTestResult(null);
    };

    return (
        <Card className="border-border bg-card" data-testid="database-connector">
            <CardHeader className="pb-4">
                <CardTitle className="text-lg flex items-center gap-2">
                    <Database className="w-5 h-5 text-primary" />
                    Cloud SQL Connection
                </CardTitle>
                <CardDescription>
                    Connect to your MySQL 8.0 database (read-only access)
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                    <div className="col-span-2">
                        <Label htmlFor="host" className="text-xs">Host / IP Address</Label>
                        <Input
                            id="host"
                            value={connection.host}
                            onChange={(e) => updateConnection('host', e.target.value)}
                            placeholder="xxx.xxx.xxx.xxx or hostname"
                            className="font-mono text-sm"
                            data-testid="db-host-input"
                        />
                    </div>
                    <div>
                        <Label htmlFor="port" className="text-xs">Port</Label>
                        <Input
                            id="port"
                            type="number"
                            value={connection.port}
                            onChange={(e) => updateConnection('port', parseInt(e.target.value) || 3306)}
                            className="font-mono text-sm"
                            data-testid="db-port-input"
                        />
                    </div>
                    <div>
                        <Label htmlFor="database" className="text-xs">Database Name</Label>
                        <Input
                            id="database"
                            value={connection.database}
                            onChange={(e) => updateConnection('database', e.target.value)}
                            placeholder="mydb"
                            className="font-mono text-sm"
                            data-testid="db-database-input"
                        />
                    </div>
                    <div>
                        <Label htmlFor="user" className="text-xs">Username</Label>
                        <Input
                            id="user"
                            value={connection.user}
                            onChange={(e) => updateConnection('user', e.target.value)}
                            placeholder="readonly_user"
                            className="font-mono text-sm"
                            data-testid="db-user-input"
                        />
                    </div>
                    <div>
                        <Label htmlFor="password" className="text-xs">Password</Label>
                        <div className="relative">
                            <Input
                                id="password"
                                type={showPassword ? 'text' : 'password'}
                                value={connection.password}
                                onChange={(e) => updateConnection('password', e.target.value)}
                                className="font-mono text-sm pr-10"
                                data-testid="db-password-input"
                            />
                            <Button
                                type="button"
                                variant="ghost"
                                size="icon"
                                className="absolute right-0 top-0 h-full px-3"
                                onClick={() => setShowPassword(!showPassword)}
                            >
                                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                            </Button>
                        </div>
                    </div>
                </div>

                <div className="flex items-center justify-between pt-2">
                    <div className="flex items-center gap-2">
                        <Switch
                            id="ssl"
                            checked={connection.ssl}
                            onCheckedChange={(checked) => updateConnection('ssl', checked)}
                            data-testid="db-ssl-toggle"
                        />
                        <Label htmlFor="ssl" className="text-xs flex items-center gap-1">
                            <Lock className="w-3 h-3" />
                            SSL Connection
                        </Label>
                    </div>
                    <Button
                        onClick={testConnection}
                        disabled={testing || !connection.host || !connection.user}
                        className="rounded-sm"
                        data-testid="test-connection-btn"
                    >
                        {testing ? (
                            <>
                                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                Testing...
                            </>
                        ) : (
                            <>
                                <Server className="w-4 h-4 mr-2" />
                                Test Connection
                            </>
                        )}
                    </Button>
                </div>

                {testResult && (
                    <Alert className={testResult.success ? 'border-success/50 bg-success/10' : 'border-destructive/50 bg-destructive/10'}>
                        <div className="flex items-start gap-2">
                            {testResult.success ? (
                                <CheckCircle className="w-4 h-4 text-success mt-0.5" />
                            ) : (
                                <XCircle className="w-4 h-4 text-destructive mt-0.5" />
                            )}
                            <AlertDescription className="text-sm">
                                {testResult.success ? (
                                    <>
                                        <span className="font-medium text-success">Connected!</span>
                                        <span className="text-muted-foreground ml-2">
                                            MySQL {testResult.data?.version} - {testResult.data?.database}
                                        </span>
                                    </>
                                ) : (
                                    <span className="text-destructive">{testResult.error}</span>
                                )}
                            </AlertDescription>
                        </div>
                    </Alert>
                )}

                <p className="text-[10px] text-muted-foreground pt-2 border-t border-border">
                    Tip: Use a read-only user with access to performance_schema and information_schema for full analysis
                </p>
            </CardContent>
        </Card>
    );
};

export default DatabaseConnector;
