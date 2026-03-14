import { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
    children: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
}

class ErrorBoundary extends Component<Props, State> {
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
                <div className="min-h-screen bg-gray-900 text-white flex flex-col items-center justify-center p-8">
                    <h1 className="text-3xl font-bold text-red-500 mb-4">Something went wrong</h1>
                    <div className="bg-gray-800 p-6 rounded-lg max-w-2xl w-full overflow-auto">
                        <p className="text-xl mb-4">The application crashed with the following error:</p>
                        <pre className="text-red-300 font-mono text-sm whitespace-pre-wrap">
                            {this.state.error?.toString()}
                        </pre>
                    </div>
                    <button
                        onClick={() => window.location.reload()}
                        className="mt-8 px-6 py-3 bg-blue-600 rounded-full font-bold hover:bg-blue-500"
                    >
                        Reload Page
                    </button>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
