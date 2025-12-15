
import { useState, useEffect } from 'react';
import { Github, Layers, Play, CheckCircle, AlertTriangle, Terminal, UploadCloud, Edit2, Lock, Hexagon } from 'lucide-react';
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
    const [activeTab, setActiveTab] = useState<'preview' | 'diff' | 'json'>('preview');

    // Refinement state
    const [refinePrompt, setRefinePrompt] = useState('');
    const [refining, setRefining] = useState(false);

    // Visual style selection
    const [visualStyle, setVisualStyle] = useState('auto');
    const STYLE_OPTIONS = [
        { value: 'auto', label: 'Auto (AI Decides)' },
        { value: 'minimalist', label: 'Minimalist Clean' },
        { value: 'cyberpunk', label: 'Cyberpunk Neon' },
        { value: 'corporate', label: 'Corporate Professional' },
        { value: 'sketch', label: 'Hand-drawn Sketch' },
        { value: 'glassmorphism', label: '3D Glassmorphism' }
    ];

    // Persistent architecture JSON state
    const [forceReanalyze, setForceReanalyze] = useState(false);

    useEffect(() => {
        // 1. Handle Auth Callback safely
        const params = new URLSearchParams(window.location.search);
        const accessToken = params.get('access_token');

        if (accessToken) {
            setToken(accessToken);
            localStorage.setItem('gh_token', accessToken); // Persist token
            // Clean URL without reloading
            window.history.replaceState({}, document.title, window.location.pathname);
        } else {
            // Recover from localStorage
            const stored = localStorage.getItem('gh_token');
            if (stored) setToken(stored);
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
                gemini_api_key: useEnvKey ? "" : apiKey,
                force_reanalyze: forceReanalyze,
                style: visualStyle
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
                    image_data_b64: preview.image_b64, // Send b64 as required by backend
                    architecture_json: preview.architecture // Send architecture JSON for persistence
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

    const handleRefine = async () => {
        if (!refinePrompt.trim() || !preview) return;

        setRefining(true);
        setError(null);

        try {
            const payload = {
                repo_url: repoUrl,
                edit_prompt: refinePrompt,
                gemini_api_key: useEnvKey ? "" : apiKey,
                force_reanalyze: forceReanalyze,
                style: visualStyle
            };

            const res = await fetch('/api/refine-image', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: res.statusText }));
                throw new Error(err.detail || `Refinement failed (${res.status})`);
            }

            const data = await res.json();
            // Update preview with new image
            setPreview({
                ...preview,
                image_b64: data.image_b64,
                image_url: data.image_url
            });
            setRefinePrompt(''); // Clear the input
        } catch (e: any) {
            setError(e.message);
        } finally {
            setRefining(false);
        }
    };

    return (
        <div className="app-container">
            {/* Sidebar */}
            <aside className="sidebar">
                <div className="logo-text">
                    <Layers size={28} />
                    <span>REPO-ARTIST</span>
                </div>

                <div style={{ marginBottom: '20px' }}>
                    {token ? (
                        <div style={{ padding: '10px', background: 'rgba(0,255,0,0.1)', border: '1px solid rgba(0,255,0,0.2)', borderRadius: '8px', color: '#4ade80', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <CheckCircle size={14} />
                            <span>GitHub Linked</span>
                        </div>
                    ) : (
                        <button onClick={handleLogin} style={{ width: '100%', padding: '10px', background: 'transparent', border: '1px solid #ffffff22', color: 'white', borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                            <Github size={16} />
                            <span>Connect GitHub</span>
                        </button>
                    )}
                </div>

                <h3>Configuration</h3>

                <div>
                    <label>Repository URL</label>
                    <input
                        type="text"
                        placeholder="https://github.com/owner/repo"
                        value={repoUrl}
                        onChange={(e) => setRepoUrl(e.target.value)}
                    />
                </div>

                <div>
                    <label>Gemini API Key</label>
                    <div style={{ position: 'relative' }}>
                        <input
                            type="password"
                            placeholder="sk-..."
                            value={useEnvKey ? "Using Server-Side Key" : apiKey}
                            disabled={useEnvKey}
                            onChange={(e) => setApiKey(e.target.value)}
                        />
                        {hasEnvKey && (
                            <button
                                onClick={() => setUseEnvKey(!useEnvKey)}
                                style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
                                title={useEnvKey ? "Edit Key" : "Use Server Key"}
                            >
                                {useEnvKey ? <Edit2 size={14} /> : <Lock size={14} />}
                            </button>
                        )}
                    </div>
                </div>

                {/* Visual Style Dropdown */}
                <div>
                    <label>Visual Style</label>
                    <select
                        value={visualStyle}
                        onChange={(e) => setVisualStyle(e.target.value)}
                        style={{
                            width: '100%',
                            padding: '10px 14px',
                            background: 'rgba(0,0,0,0.3)',
                            border: '1px solid var(--glass-border)',
                            borderRadius: '8px',
                            color: 'white',
                            fontSize: '0.9rem',
                            cursor: 'pointer'
                        }}
                    >
                        {STYLE_OPTIONS.map(opt => (
                            <option key={opt.value} value={opt.value} style={{ background: '#1a1a2e', color: 'white' }}>
                                {opt.label}
                            </option>
                        ))}
                    </select>
                </div>

                {/* Force Re-analyze Checkbox */}
                <div style={{ marginTop: '12px' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        <input
                            type="checkbox"
                            checked={forceReanalyze}
                            onChange={(e) => setForceReanalyze(e.target.checked)}
                            style={{ cursor: 'pointer' }}
                        />
                        <span>Force re-analyze (ignore cached architecture)</span>
                    </label>
                </div>

                <div style={{ marginTop: 'auto' }}>
                    <button
                        className="primary-btn"
                        onClick={handlePreview}
                        disabled={loading || !repoUrl || (!useEnvKey && !apiKey)}
                    >
                        {loading ? "PROCESSING..." : "GENERATE PREVIEW"}
                    </button>
                </div>

                {/* Status Messages - Inline style for simplicity to match urgency */}
                {error && (
                    <div style={{ marginTop: '10px', padding: '10px', background: 'rgba(255,0,0,0.1)', border: '1px solid rgba(255,0,0,0.2)', borderRadius: '8px', color: '#ffaaaa', fontSize: '0.8rem' }}>
                        {error}
                    </div>
                )}
                {successLink && (
                    <div style={{ marginTop: '10px', padding: '10px', background: 'rgba(0,255,0,0.1)', border: '1px solid rgba(0,255,0,0.2)', borderRadius: '8px', color: '#aaffaa', fontSize: '0.8rem' }}>
                        <a href={successLink} target="_blank" rel="noreferrer" style={{ color: 'inherit' }}>View Commit &rarr;</a>
                    </div>
                )}

            </aside>

            {/* Main Content */}
            <main className="main-content">
                {!preview ? (
                    <div className="preview-box empty">
                        {loading ? (
                            <>
                                <div className="ai-icon-placeholder" style={{ animation: 'spin 2s linear infinite' }}>
                                    <Terminal size={64} />
                                </div>
                                <p style={{ marginTop: '20px', fontSize: '1.2rem', color: 'var(--neon-cyan)', fontFamily: 'monospace', fontWeight: 'bold' }}>
                                    Processing Repository...
                                </p>
                                <p style={{ marginTop: '10px', fontSize: '0.9rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                                    Analyzing code structure • Generating architecture • Creating visual
                                </p>
                            </>
                        ) : (
                            <>
                                <div className="ai-icon-placeholder">
                                    <Hexagon size={64} />
                                </div>
                                <p style={{ marginTop: '20px', fontSize: '1.2rem', color: 'var(--neon-cyan)', fontFamily: 'monospace' }}>
                                    Awaiting Neural Link...
                                </p>
                            </>
                        )}
                    </div>
                ) : (
                    <div className="preview-box" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'flex-start', padding: '20px', overflow: 'auto', height: '100%' }}>
                        <img
                            src={preview.image_url || `data:image/png;base64,${preview.image_b64}`}
                            alt="Generated Architecture"
                            style={{ maxWidth: '100%', borderRadius: '12px', border: '1px solid var(--glass-border)', boxShadow: '0 0 20px rgba(0,0,0,0.5)', flexShrink: 0, marginBottom: '20px' }}
                        />

                        {/* Refine Image Section - Only show if API key is available */}
                        {hasEnvKey && (
                            <div style={{ width: '100%', marginBottom: '20px', padding: '16px', background: 'rgba(0, 243, 255, 0.05)', border: '1px solid rgba(0, 243, 255, 0.2)', borderRadius: '12px', flexShrink: 0 }}>
                                <h3 style={{ margin: '0 0 12px 0', fontSize: '0.9rem', color: 'var(--neon-cyan)', fontFamily: 'monospace', textTransform: 'uppercase', letterSpacing: '1px' }}>
                                    ✨ Refine Image
                                </h3>
                                <textarea
                                    value={refinePrompt}
                                    onChange={(e) => setRefinePrompt(e.target.value)}
                                    placeholder="Describe changes (e.g., 'Make the database red', 'Add a cloud icon', 'Use neon colors')"
                                    disabled={refining}
                                    style={{
                                        width: '100%',
                                        minHeight: '80px',
                                        padding: '12px',
                                        background: 'rgba(0,0,0,0.3)',
                                        border: '1px solid var(--glass-border)',
                                        borderRadius: '8px',
                                        color: 'white',
                                        fontSize: '0.9rem',
                                        fontFamily: 'monospace',
                                        resize: 'vertical',
                                        marginBottom: '12px',
                                        boxSizing: 'border-box'
                                    }}
                                />
                                <button
                                    onClick={handleRefine}
                                    disabled={refining || !refinePrompt.trim()}
                                    style={{
                                        padding: '10px 20px',
                                        background: refining || !refinePrompt.trim() ? 'rgba(128,128,128,0.3)' : 'linear-gradient(135deg, var(--neon-cyan), var(--neon-purple))',
                                        border: 'none',
                                        borderRadius: '8px',
                                        color: 'white',
                                        fontWeight: 'bold',
                                        cursor: refining || !refinePrompt.trim() ? 'not-allowed' : 'pointer',
                                        fontSize: '0.85rem',
                                        textTransform: 'uppercase',
                                        letterSpacing: '0.5px'
                                    }}
                                >
                                    {refining ? 'UPDATING...' : 'UPDATE VISUALS'}
                                </button>
                            </div>
                        )}

                        <div style={{ width: '100%', display: 'flex', flexDirection: 'column', minHeight: '300px', flexShrink: 0 }}>
                            <div style={{ display: 'flex', gap: '10px', marginBottom: '10px', flexShrink: 0 }}>
                                <button onClick={() => setActiveTab('preview')} style={{ padding: '8px 16px', background: activeTab === 'preview' ? 'rgba(255,255,255,0.1)' : 'transparent', border: '1px solid var(--glass-border)', color: 'white', borderRadius: '6px', cursor: 'pointer' }}>Preview</button>
                                <button onClick={() => setActiveTab('diff')} style={{ padding: '8px 16px', background: activeTab === 'diff' ? 'rgba(255,255,255,0.1)' : 'transparent', border: '1px solid var(--glass-border)', color: 'white', borderRadius: '6px', cursor: 'pointer' }}>Code</button>
                                <button onClick={() => setActiveTab('json')} style={{ padding: '8px 16px', background: activeTab === 'json' ? 'rgba(255,255,255,0.1)' : 'transparent', border: '1px solid var(--glass-border)', color: 'white', borderRadius: '6px', cursor: 'pointer' }}>Architecture JSON</button>

                                <button
                                    onClick={handleApply}
                                    disabled={!token}
                                    style={{
                                        marginLeft: 'auto',
                                        padding: '8px 24px',
                                        background: !token ? 'rgba(128,128,128,0.3)' : 'var(--neon-purple)',
                                        border: 'none',
                                        borderRadius: '6px',
                                        color: 'white',
                                        fontWeight: 'bold',
                                        cursor: !token ? 'not-allowed' : 'pointer',
                                        position: 'relative',
                                        zIndex: 10,
                                        pointerEvents: 'auto'
                                    }}
                                >
                                    {token ? "APPLY" : "Connect GitHub to Apply"}
                                </button>
                            </div>

                            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '20px', borderRadius: '12px', border: '1px solid var(--glass-border)', minHeight: '200px', color: '#eee', overflow: 'auto', flex: 1 }}>
                                {activeTab === 'preview' ? (
                                    <div style={{ lineHeight: '1.6' }}><ReactMarkdown>{preview.new_readme}</ReactMarkdown></div>
                                ) : activeTab === 'diff' ? (
                                    <pre style={{ fontSize: '0.8rem', fontFamily: 'monospace' }}>{preview.new_readme}</pre>
                                ) : (
                                    <pre style={{ fontSize: '0.75rem', fontFamily: 'monospace', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                                        {JSON.stringify(preview.architecture, null, 2)}
                                    </pre>
                                )}
                            </div>
                        </div>
                    </div>
                )}
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
