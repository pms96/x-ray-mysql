import React, { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const AuthCallback = () => {
    const navigate = useNavigate();
    const { processSession } = useAuth();
    const hasProcessed = useRef(false);

    useEffect(() => {
        if (hasProcessed.current) return;
        hasProcessed.current = true;

        const processAuth = async () => {
            const hash = window.location.hash;
            const sessionIdMatch = hash.match(/session_id=([^&]+)/);
            
            if (sessionIdMatch) {
                const sessionId = sessionIdMatch[1];
                
                try {
                    const userData = await processSession(sessionId);
                    // Clear hash and navigate to dashboard with user data
                    window.history.replaceState(null, '', window.location.pathname);
                    navigate('/dashboard', { state: { user: userData }, replace: true });
                } catch (error) {
                    console.error('Auth callback error:', error);
                    navigate('/', { replace: true });
                }
            } else {
                navigate('/', { replace: true });
            }
        };

        processAuth();
    }, [navigate, processSession]);

    return (
        <div className="min-h-screen bg-background flex items-center justify-center" data-testid="auth-callback">
            <div className="text-center">
                <div className="loading-spinner mx-auto mb-4"></div>
                <p className="text-muted-foreground text-sm">Authenticating...</p>
            </div>
        </div>
    );
};

export default AuthCallback;
