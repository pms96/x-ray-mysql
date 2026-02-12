import "@/App.css";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import AuthCallback from "./components/AuthCallback";
import ProtectedRoute from "./components/ProtectedRoute";
import Landing from "./pages/Landing";
import Dashboard from "./pages/Dashboard";
import History from "./pages/History";
import { Toaster } from "./components/ui/sonner";

// Router component that handles session_id detection
function AppRouter() {
    const location = useLocation();
    
    // Check URL fragment (not query params) for session_id synchronously during render
    // This prevents race conditions by processing new session_id FIRST before checking existing session_token
    if (location.hash?.includes('session_id=')) {
        return <AuthCallback />;
    }

    return (
        <Routes>
            <Route path="/" element={<Landing />} />
            <Route 
                path="/dashboard" 
                element={
                    <ProtectedRoute>
                        <Dashboard />
                    </ProtectedRoute>
                } 
            />
            <Route 
                path="/history" 
                element={
                    <ProtectedRoute>
                        <History />
                    </ProtectedRoute>
                } 
            />
        </Routes>
    );
}

function App() {
    return (
        <div className="app-container dark">
            <BrowserRouter>
                <AuthProvider>
                    <AppRouter />
                    <Toaster position="top-right" />
                </AuthProvider>
            </BrowserRouter>
        </div>
    );
}

export default App;
