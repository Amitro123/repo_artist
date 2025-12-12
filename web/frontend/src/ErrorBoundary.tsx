
import { Component, ErrorInfo, ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface Props {
    children?: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
    public state: State = {
        hasError: false,
        error: null
    };

    public static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error("Uncaught error:", error, errorInfo);
    }

    public render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen flex items-center justify-center bg-[#0f172a] text-slate-200 p-4">
                    <div className="glass-panel p-8 max-w-md w-full text-center space-y-4 border border-red-500/30">
                        <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center mx-auto text-red-400">
                            <AlertTriangle size={32} />
                        </div>
                        <h2 className="text-xl font-bold text-red-400">Something went wrong</h2>
                        <p className="text-sm text-slate-400 font-mono bg-black/30 p-3 rounded text-left overflow-auto max-h-32">
                            {this.state.error?.message}
                        </p>
                        <button
                            onClick={() => window.location.reload()}
                            className="btn btn-secondary w-full"
                        >
                            <RefreshCw size={16} />
                            Reload Application
                        </button>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}
