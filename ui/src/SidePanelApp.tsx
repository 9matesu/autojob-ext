import { useEffect, useRef, useState } from 'react';
import {
  Camera,
  Loader2,
  Download,
  Maximize2,
} from 'lucide-react';
import {
  fetchHealth,
  fetchMasterProfile,
} from './services/api';
import type { AppHealth, CandidateProfile, AdaptedResult } from './services/api';
import {
  startCaptureSelection,
  onCaptureResult,
  saveStudioPayload,
  openStudioTab,
  ensureBackend,
  isExtension,
} from './chrome';
import { OnboardingWizard } from './components/onboarding/OnboardingWizard';
import { ApplicationHistory } from './components/history/ApplicationHistory';
import { SettingsPanel } from './components/settings/SettingsPanel';

type View = 'capture' | 'history' | 'settings';

const NAV: Array<{ id: View; label: string }> = [
  { id: 'capture', label: '1. Captura' },
  { id: 'history', label: '2. Arquivo' },
  { id: 'settings', label: '3. Config' },
];

export function SidePanelApp() {
  const [health, setHealth] = useState<AppHealth | null>(null);
  const [masterProfile, setMasterProfile] = useState<CandidateProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<View>('capture');
  const [busy, setBusy] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [error, setError] = useState('');
  const [result, setResult] = useState<AdaptedResult | null>(null);
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState('');
  const autoEnsured = useRef(false);

  const applyHealth = async (h: AppHealth) => {
    setHealth(h);
    if (h.has_active_candidate) {
      const p = await fetchMasterProfile();
      setMasterProfile(p.profile);
    } else {
      setMasterProfile(null);
    }
  };

  const pollHealth = async (ms: number): Promise<boolean> => {
    const deadline = Date.now() + ms;
    while (Date.now() < deadline) {
      try {
        await applyHealth(await fetchHealth());
        return true;
      } catch {
        await new Promise((r) => setTimeout(r, 500));
      }
    }
    return false;
  };

  const startBackend = async () => {
    setStarting(true);
    setStartError('');
    const res = await ensureBackend();
    const ok = await pollHealth(12000);
    if (!ok) setStartError(res.error || 'O motor nao respondeu. Execute start-backend.ps1.');
    setStarting(false);
    return ok;
  };

  const init = async (): Promise<boolean> => {
    try {
      await applyHealth(await fetchHealth());
      return true;
    } catch {
      setHealth(null);
      return false;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    init().then((ok) => {
      if (!ok && isExtension && !autoEnsured.current) {
        autoEnsured.current = true;
        void startBackend();
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const t = setInterval(() => {
      if (!busy && !starting) init();
    }, 5000);
    return () => clearInterval(t);
  }, [busy, starting]);

  useEffect(
    () =>
      onCaptureResult(
        (r) => {
          setResult(r as AdaptedResult);
          setBusy(false);
          setStatusMsg('');
          setError('');
        },
        (m) => {
          setError(m);
          setBusy(false);
          setStatusMsg('');
        },
        () => {
          setBusy(false);
          setStatusMsg('');
        }
      ),
    []
  );

  const handleDomCapture = async () => {
    setBusy(true);
    setError('');
    setResult(null);
    try {
      await startCaptureSelection();
      setStatusMsg('Clique no painel → edite a prévia se quiser → CAPTURAR (Esc cancela)');
    } catch (e: any) {
      setError(e.message || 'Falha ao iniciar a captura');
      setBusy(false);
      setStatusMsg('');
    }
  };

  const openStudio = async () => {
    if (!result) return;
    await saveStudioPayload(result);
    openStudioTab();
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center gap-3 font-mono text-xs uppercase tracking-wider">
        <Loader2 className="w-5 h-5 animate-spin" />
        Inicializando...
      </div>
    );
  }

  if (!health) {
    if (starting) {
      return (
        <div className="h-full flex flex-col items-center justify-center gap-3 font-mono text-xs uppercase tracking-wider">
          <Loader2 className="w-6 h-6 animate-spin" />
          Iniciando motor local...
        </div>
      );
    }
    return (
      <div className="h-full flex flex-col items-center justify-center p-6 text-center gap-4">
        <h1 className="font-editorial text-3xl">Motor Offline</h1>
        <p className="text-xs font-mono text-neutral-700 leading-relaxed">
          O servidor local do resuMe não respondeu em http://127.0.0.1:8322.
          {startError ? ` ${startError}` : ' Execute start-backend.ps1 na pasta do projeto e tente novamente.'}
        </p>
        <button
          onClick={() => (isExtension ? startBackend() : void init())}
          className="brutal-btn px-4 py-2 text-xs"
        >
          Tentar Novamente
        </button>
      </div>
    );
  }

  if (!health.has_active_candidate || !masterProfile) {
    return (
      <div className="h-full flex flex-col bg-white">
        <OnboardingWizard health={health} onComplete={init} />
      </div>
    );
  }

  const online = health.status === 'ok';

  return (
    <div className="h-full flex flex-col bg-white text-black select-none">
      {/* Header */}
      <header className="hairline-b px-4 py-2.5 flex items-center justify-between shrink-0">
        <span className="text-sm font-bold uppercase tracking-tight">resu<span className="font-editorial normal-case tracking-normal">Me</span></span>
        <span className="brutal-tag">
          <span className={`w-1.5 h-1.5 rounded-full ${online ? 'bg-emerald-500' : 'bg-red-600'}`} />
          {online ? 'Online' : 'Offline'}
        </span>
      </header>

      {/* Nav */}
      <nav className="hairline-b grid grid-cols-3 text-[11px] uppercase font-bold shrink-0 divide-x divide-black">
        {NAV.map((n) => (
          <button
            key={n.id}
            onClick={() => setView(n.id)}
            className={`py-2 cursor-pointer transition-colors ${
              view === n.id ? 'bg-black text-white' : 'bg-white hover:bg-neutral-100'
            }`}
          >
            {n.label}
          </button>
        ))}
      </nav>

      {/* Body */}
      <main className="flex-1 overflow-y-auto p-4">
        {view === 'capture' && (
          <div className="space-y-4">
            <button
              onClick={handleDomCapture}
              disabled={busy}
              className="w-full bg-brutal-yellow border-2 border-black shadow-[6px_6px_0px_0px_#000000] p-6 text-left active:translate-x-[2px] active:translate-y-[2px] active:shadow-none transition-all cursor-pointer disabled:opacity-60"
            >
              <div className="flex items-center gap-2">
                {busy ? <Loader2 className="w-5 h-5 animate-spin" /> : <Camera className="w-5 h-5" />}
                <span className="font-editorial text-2xl leading-none">Capturar Vaga</span>
              </div>
              <p className="text-[11px] font-mono mt-2 leading-relaxed">
                {busy
                  ? statusMsg || 'Processando...'
                  : 'Destaca os paineis da pagina: clique para ver a prévia e confirmar a captura.'}
              </p>
            </button>

            {error && (
              <div className="border-2 border-black p-3 text-xs font-mono flex items-start gap-2">
                <span className="brutal-tag brutal-tag-black shrink-0">Erro</span>
                <span>{error}</span>
              </div>
            )}

            {result && (
              <div className="brutal-card p-4 space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h2 className="font-editorial text-lg normal-case leading-tight">{result.job.title}</h2>
                    <p className="text-[11px] font-mono text-neutral-600 mt-0.5">
                      {result.job.company}
                      {result.job.location ? ` — ${result.job.location}` : ''}
                    </p>
                    {result.captured_chars != null && result.captured_chars > 0 && (
                      <p className="text-[10px] font-mono text-neutral-400 mt-0.5">
                        texto capturado: ~{result.captured_chars >= 1000 ? `${(result.captured_chars / 1000).toFixed(1).replace('.', ',')}k` : result.captured_chars} chars
                      </p>
                    )}
                  </div>
                  {result.adaptation.match_score != null && result.adaptation.match_score > 0 && (
                    <span className="brutal-tag brutal-tag-yellow shrink-0">
                      {result.adaptation.match_score.toFixed(0)}%
                    </span>
                  )}
                </div>

                {(result.adaptation.applied_keywords?.length ?? 0) > 0 && (
                  <div className="hairline-b pb-3">
                    <div className="text-[10px] font-bold uppercase mb-1.5">Palavras-chave aplicadas</div>
                    <div className="flex flex-wrap gap-1.5">
                      {result.adaptation.applied_keywords!.map((k) => (
                        <span key={k} className="brutal-tag">{k}</span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-2">
                  <a
                    href={result.adaptation.pdf_url}
                    download={`Curriculo_${result.job.company.replace(/\s+/g, '_')}.pdf`}
                    className="brutal-btn-yellow flex items-center justify-center gap-1.5 px-2 py-2 text-[11px]"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Baixar PDF
                  </a>
                  <button onClick={openStudio} className="brutal-btn flex items-center justify-center gap-1.5 px-2 py-2 text-[11px]">
                    <Maximize2 className="w-3.5 h-3.5" />
                    Abrir Estúdio
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {view === 'history' && <ApplicationHistory />}
        {view === 'settings' && <SettingsPanel />}
      </main>

      {/* Footer */}
      <footer className="hairline-t px-4 py-1.5 text-[10px] font-mono text-neutral-600 flex items-center justify-between shrink-0 uppercase">
        <span>{health.ai_provider} / {health.ai_model}</span>
        <span>{health.candidate_name}</span>
      </footer>
    </div>
  );
}

export default SidePanelApp;
