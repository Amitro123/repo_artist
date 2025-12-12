
import { useState, useEffect } from 'react';
import { Github, Layers, Play, CheckCircle, AlertTriangle, Terminal, UploadCloud, Edit2, Lock } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { ErrorBoundary } from './ErrorBoundary';

interface PreviewResponse {
    image_b64: string;
    image_url?: string;
    current_readme: string;
    new_readme: string;
    architecture: any;
}

function RepoArtistApp() {
    const [token, setToken] = useState<string | null>(null);
    const [repoUrl, setRepoUrl] = useState('');

    // API Key Logic
    const [apiKey, setApiKey] = useState('');
    const [hasEnvKey, setHasEnvKey] = useState(false);
    const [useEnvKey, setUseEnvKey] = useState(false);

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [successLink, setSuccessLink] = useState<string | null>(null);

    const [preview, setPreview] = useState<PreviewResponse | null>(null);
    const [activeTab, setActiveTab] = useState<'preview' | 'diff'>('preview');

    useEffect(() => {
        // 1. Handle Auth Callback safely
        const params = new URLSearchParams(window.location.search);
        const accessToken = params.get('access_token');

        if (accessToken) {
            setToken(accessToken);
            // Clean URL without reloading
            window.history.replaceState({}, document.title, window.location.pathname);
        }

        // 2. Fetch Config
        fetch('/api/config')
            .then(r => {
                if (!r.ok) throw new Error("Failed to load config");
                return r.json();
            })
            .then(data => {
                if (data.has_env_key) {
                    setHasEnvKey(true);
                    setUseEnvKey(true);
                }
            })
            .catch(err => {
                console.warn("Config fetch failed:", err);
                // Don't block app, just assume no env key
            });
    }, []);

    const handleLogin = async () => {
        try {
            const res = await fetch('/auth/login');
            if (!res.ok) throw new Error("Auth endpoint failed");
            const data = await res.json();
            // Redirect to GitHub
            window.location.href = data.url;
        } catch (e: any) {
            setError(`Login failed: ${e.message}`);
        }
    };

    const handlePreview = async () => {
        if (!repoUrl) {
            setError("Please provide Repository URL");
            return;
        }
        if (!useEnvKey && !apiKey) {
            setError("Please provide Gemini API Key");
            return;
        }

        setLoading(true);
        setError(null);
        setPreview(null);
        setSuccessLink(null);

        try {
            const payload = {
                repo_url: repoUrl,
                gemini_api_key: useEnvKey ? "" : apiKey
            };

            const res = await fetch('/api/preview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: res.statusText }));
                throw new Error(err.detail || `Preview failed (${res.status})`);
            }

            const data = await res.json();
            setPreview(data);
        } catch (e: any) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    const handleApply = async () => {
        if (!preview || !token) return;

        setLoading(true);
        setError(null);

        try {
            const res = await fetch('/api/apply', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    repo_url: repoUrl,
                    approved_readme: preview.new_readme,
                    image_data_b64: preview.image_b64 // Send b64 as required by backend
                })
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: res.statusText }));
                throw new Error(err.detail || "Apply failed");
            }

            const data = await res.json();
            setSuccessLink(data.commit_url);
        } catch (e: any) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen text-slate-200 p-4 md:p-8 flex flex-col">
            <header className="max-w-7xl mx-auto w-full mb-10 flex flex-col md:flex-row justify-between items-center pb-6 border-b border-gray-800/60">
                <div className="flex items-center gap-4 mb-4 md:mb-0">
                    <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg shadow-purple-500/20">
                        <Layers className="text-white" size={24} />
                    </div>
                    <div>
                        <h1 className="text-4xl font-extrabold tracking-tight text-white text-glow font-['Montserrat']">
                            REPO-ARTIST
                        </h1>
                        <p className="text-sm text-cyan-200/70 font-medium tracking-wide font-mono mt-1">
              // Turn Code into Art. Visualize instantly.
                        </p>
                    </div>
                </div>

                <div>
                    {token ? (
                        <div className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-emerald-500/10 to-teal-500/10 border border-emerald-500/20 rounded-full text-emerald-400 text-sm font-semibold shadow-[0_0_10px_rgba(16,185,129,0.2)]">
                            <CheckCircle size={16} />
                            <span>Connected to GitHub</span>
                        </div>
                    ) : (
                        <button onClick={handleLogin} className="btn btn-secondary text-sm">
                            <Github size={18} />
                            Connect GitHub
                        </button>
                    )}
                </div>
            </header>

            <main className="max-w-7xl mx-auto w-full grid grid-cols-1 lg:grid-cols-12 gap-8 flex-1">
                {/* Left Panel: Controls */}
                <div className="lg:col-span-4 space-y-6">
                    <div className="glass-panel p-6 space-y-6">
                        <h2 className="text-lg font-bold flex items-center gap-2 header-accent uppercase tracking-widest font-['Montserrat']">
                            <Terminal size={18} />
                            Configuration
                        </h2>

                        <div className="space-y-5">
                            <div>
                                <label className="block text-xs font-bold text-cyan-200/50 mb-2 uppercase tracking-wider font-mono">&gt; Repository URL</label>
                                <input
                                    type="text"
                                    className="input-field"
                                    placeholder="https://github.com/owner/repo"
                                    value={repoUrl}
                                    onChange={(e) => setRepoUrl(e.target.value)}
                                />
                            </div>

                            <div>
                                <label className="block text-xs font-bold text-cyan-200/50 mb-2 uppercase tracking-wider font-mono">&gt; Gemini API Key</label>
                                <div className="relative">
                                    <input
                                        type="password"
                                        className="input-field"
                                        placeholder="sk-..."
                                        value={useEnvKey ? "Using Server-Side Key" : apiKey}
                                        disabled={useEnvKey}
                                        onChange={(e) => setApiKey(e.target.value)}
                                    />
                                    {hasEnvKey && (
                                        <button
                                            onClick={() => setUseEnvKey(!useEnvKey)}
                                            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white transition-colors p-1"
                                            title={useEnvKey ? "Edit Key" : "Use Server Key"}
                                        >
                                            {useEnvKey ? <Edit2 size={14} /> : <Lock size={14} />}
                                        </button>
                                    )}
                                </div>
                                {hasEnvKey && useEnvKey && (
                                    <p className="text-[10px] text-green-400/70 mt-1.5 flex items-center gap-1">
                                        <CheckCircle size={10} /> Loaded from Environment
                                    </p>
                                )}
                            </div>
                        </div>

                        <div className="pt-4">
                            <button
                                onClick={handlePreview}
                                className="btn btn-primary w-full"
                                disabled={loading || !repoUrl || (!useEnvKey && !apiKey)}
                            >
                                {loading && !preview ? <div className="loader w-5 h-5 border-2" /> : <Play size={20} fill="currentColor" />}
                                Generate Preview
                            </button>
                        </div>
                    </div>

                    {/* Status Messages */}
                    {error && (
                        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-200 text-sm flex gap-3 items-start backdrop-blur-sm">
                            <AlertTriangle className="shrink-0 mt-0.5" size={16} />
                            <p>{error}</p>
                        </div>
                    )}

                    {successLink && (
                        <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-emerald-200 text-sm backdrop-blur-sm">
                            <h3 className="font-semibold flex items-center gap-2 mb-1 text-emerald-400">
                                <CheckCircle size={16} /> Success!
                            </h3>
                            <p className="mb-2 opacity-90">Changes committed to GitHub.</p>
                            <a
                                href={successLink}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1 text-emerald-400 hover:text-emerald-300 underline font-medium"
                            >
                                View Commit &rarr;
                            </a>
                        </div>
                    )}
                </div>

                {/* Right Panel: Preview */}
                <div className="lg:col-span-8">
                    <div className="glass-panel min-h-[600px] flex flex-col h-full animate-pulse-slow relative overflow-hidden">
                        {/* Corner decorations */}
                        <div className="absolute top-0 left-0 w-16 h-16 border-t-2 border-l-2 border-cyan-500/30 rounded-tl-xl"></div>
                        <div className="absolute bottom-0 right-0 w-16 h-16 border-b-2 border-r-2 border-purple-500/30 rounded-br-xl"></div>

                        <div className="border-b border-white/5 p-4 flex items-center justify-between bg-black/20 backdrop-blur-sm z-10">
                            <h2 className="font-bold text-white flex items-center gap-2 header-accent font-['Montserrat'] uppercase tracking-widest text-sm">
                                <span className="w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.8)] animate-pulse"></span>
                                System Output
                            </h2>

                            {preview && (
                                <div className="flex bg-black/40 rounded-lg p-1 border border-white/10">
                                    <button
                                        onClick={() => setActiveTab('preview')}
                                        className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${activeTab === 'preview' ? 'bg-blue-600/30 text-blue-300 shadow-sm' : 'text-slate-500 hover:text-slate-300'}`}
                                    >
                                        Preview
                                    </button>
                                    <button
                                        onClick={() => setActiveTab('diff')}
                                        className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${activeTab === 'diff' ? 'bg-blue-600/30 text-blue-300 shadow-sm' : 'text-slate-500 hover:text-slate-300'}`}
                                    >
                                        Raw Content
                                    </button>
                                </div>
                            )}
                        </div>

                        <div className="flex-1 p-6 overflow-hidden relative z-10">
                            {!preview ? (
                                <div className="absolute inset-0 flex flex-col items-center justify-center text-cyan-200/30 select-none pointer-events-none">
                                    {/* Wireframe Placeholder */}
                                    <div className="relative mb-8">
                                        <div className="absolute inset-0 bg-cyan-500/20 blur-xl rounded-full"></div>
                                        <svg width="240" height="240" viewBox="0 0 240 240" fill="none" xmlns="http://www.w3.org/2000/svg" className="opacity-80 animate-pulse relative z-10">
                                            <path d="M120 20L200 60V160L120 200L40 160V60L120 20Z" stroke="currentColor" strokeWidth="1" strokeDasharray="4 4" />
                                            <circle cx="120" cy="110" r="40" stroke="currentColor" strokeWidth="1" />
                                            <path d="M120 70V150M80 110H160" stroke="currentColor" strokeWidth="1" />
                                            <circle cx="120" cy="20" r="2" fill="currentColor" />
                                            <circle cx="200" cy="60" r="2" fill="currentColor" />
                                            <circle cx="200" cy="160" r="2" fill="currentColor" />
                                            <circle cx="120" cy="200" r="2" fill="currentColor" />
                                            <circle cx="40" cy="160" r="2" fill="currentColor" />
                                            <circle cx="40" cy="60" r="2" fill="currentColor" />
                                        </svg>
                                    </div>
                                    <p className="text-xl font-mono text-cyan-400 font-bold tracking-widest text-glow">Awaiting Neural Link...</p>
                                    <div className="w-32 h-1 bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent my-4"></div>
                                    <p className="text-xs uppercase tracking-widest opacity-60 font-mono">Ready for Code Analysis</p>
                                </div>
                            ) : (
                                <div className="space-y-6 h-full flex flex-col">
                                    {/* Hero Image */}
                                    <div className="rounded-xl overflow-hidden border border-gray-700/50 shadow-2xl relative group bg-black/40">
                                        <img
                                            /* Prefer image_url for performance/caching, fallback to b64 */
                                            src={preview.image_url || `data:image/png;base64,${preview.image_b64}`}
                                            className="w-full h-auto object-cover max-h-[350px] transition-transform duration-700 group-hover:scale-[1.02]"
                                            alt="Hero Preview"
                                            onError={(e) => {
                                                // Fallback if URL fails (e.g. 404), try key-based re-render? No, just log
                                                console.error("Image load failed", e);
                                            }}
                                        />
                                        <div className="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end justify-center pb-4">
                                            <p className="text-white/80 text-sm font-medium font-mono">Generated Asset</p>
                                        </div>
                                    </div>

                                    {/* Content View */}
                                    <div className="flex-1 overflow-y-auto custom-scrollbar border border-gray-700/30 rounded-xl bg-black/20 p-5 shadow-inner">
                                        {activeTab === 'preview' ? (
                                            <div className="markdown-body">
                                                <ReactMarkdown>{preview.new_readme}</ReactMarkdown>
                                            </div>
                                        ) : (
                                            <pre className="text-xs text-blue-200/70 font-mono whitespace-pre-wrap leading-relaxed">
                                                {preview.new_readme}
                                            </pre>
                                        )}
                                    </div>

                                    {/* Action Bar */}
                                    <div className="pt-4 border-t border-gray-700/30 flex justify-end">
                                        <button
                                            onClick={handleApply}
                                            disabled={loading || !token}
                                            className="btn btn-primary"
                                            title={!token ? "Login to GitHub first" : ""}
                                        >
                                            {loading ? <div className="loader w-5 h-5 border-2" /> : <UploadCloud size={20} />}
                                            Apply to README
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </main>
        </div>
    )
}

function App() {
    return (
        <ErrorBoundary>
            <RepoArtistApp />
        </ErrorBoundary>
    )
}

export default App
