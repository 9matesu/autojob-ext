import React, { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { fetchSettings, saveSettings, testAiConnection } from '../../services/api';
import type { AppSettings } from '../../services/api';

export const SettingsPanel: React.FC = () => {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [aiProvider, setAiProvider] = useState('gemini');
  const [aiModel, setAiModel] = useState('gemini-2.0-flash');
  const [aiApiKey, setAiApiKey] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [saved, setSaved] = useState(false);

  const load = async () => {
    try {
      setLoading(true);
      const data = await fetchSettings();
      setSettings(data);
      setAiProvider(data.ai_provider);
      setAiModel(data.ai_model);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      await testAiConnection({
        ai_provider: aiProvider,
        ai_api_key: aiApiKey,
        ai_model: aiModel,
      });
      setTestResult({ ok: true, message: 'Conexão com a IA verificada com sucesso.' });
    } catch (err: any) {
      setTestResult({ ok: false, message: err.message || 'Falha na conexão' });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await saveSettings({
        ai_provider: aiProvider,
        ai_model: aiModel,
        ...(aiApiKey ? { ai_api_key: aiApiKey } : {}),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (err: any) {
      alert('Falha ao salvar configurações: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-xl mx-auto w-full space-y-5 select-none">
      <div className="brutal-card p-5 space-y-5">
        <div className="hairline-b pb-3">
          <h2 className="text-sm font-bold uppercase tracking-tight">Configurações de IA & LaTeX</h2>
        </div>

        {loading ? (
          <div className="py-12 flex justify-center">
            <Loader2 className="w-6 h-6 animate-spin" />
          </div>
        ) : (
          <div className="space-y-4 text-xs">
            <div>
              <label className="text-[10px] font-bold uppercase tracking-wider block mb-1">Provedor de IA</label>
              <select
                value={aiProvider}
                onChange={(e) => {
                  setAiProvider(e.target.value);
                  if (e.target.value === 'gemini') setAiModel('gemini-2.0-flash');
                  if (e.target.value === 'openai') setAiModel('gpt-4o-mini');
                }}
                className="brutal-input cursor-pointer"
              >
                <option value="gemini">Google Gemini (Recomendado — Visão ultra-rápida)</option>
                <option value="openai">OpenAI (GPT-4o / GPT-4o-mini)</option>
                <option value="openrouter">OpenRouter (Gateway Multimodelo)</option>
                <option value="ollama">Ollama (Modelo Local Offline)</option>
                <option value="mock">Mock Offline (Modo de Demonstração sem chave)</option>
              </select>
            </div>

            {aiProvider !== 'mock' && (
              <div>
                <label className="text-[10px] font-bold uppercase tracking-wider block mb-1">
                  Chave de API{' '}
                  {settings?.has_key && (
                    <span className="text-neutral-500 normal-case tracking-normal">
                      (Configurada: {settings.ai_api_key_masked})
                    </span>
                  )}
                </label>
                <input
                  type="password"
                  value={aiApiKey}
                  onChange={(e) => setAiApiKey(e.target.value)}
                  placeholder={settings?.has_key ? 'Insira nova chave para substituir' : 'Insira a Chave de API'}
                  className="brutal-input"
                />
              </div>
            )}

            <div>
              <label className="text-[10px] font-bold uppercase tracking-wider block mb-1">Nome do Modelo</label>
              <input
                type="text"
                value={aiModel}
                onChange={(e) => setAiModel(e.target.value)}
                className="brutal-input"
              />
            </div>

            {/* Test connection */}
            <div className="pt-1">
              <button
                type="button"
                onClick={handleTest}
                disabled={testing}
                className="brutal-btn w-full py-2 flex items-center justify-center gap-1.5"
              >
                {testing && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span>{testing ? 'Testando conexão...' : 'Testar Conexão com a IA'}</span>
              </button>

              {testResult && (
                <div className={`mt-2 p-2.5 flex items-center gap-2 border-2 border-black ${testResult.ok ? 'bg-brutal-yellow' : 'bg-white'}`}>
                  <span className="brutal-tag brutal-tag-black shrink-0">{testResult.ok ? 'OK' : 'Falha'}</span>
                  <span>{testResult.message}</span>
                </div>
              )}
            </div>

            {/* Compiler Information */}
            <div className="border-2 border-black p-3 flex items-center justify-between">
              <div>
                <div className="font-bold uppercase">Motor LaTeX</div>
                <div className="text-[10px] text-neutral-600 font-mono">{settings?.detected_compiler || 'Tectonic (Portátil)'}</div>
              </div>
              <span className="brutal-tag brutal-tag-yellow">Pronto</span>
            </div>
          </div>
        )}

        <div className="flex items-center justify-end gap-2 pt-3 hairline-t">
          {saved && <span className="brutal-tag brutal-tag-yellow mr-auto">Salvo</span>}
          <button
            onClick={handleSave}
            disabled={saving}
            className="brutal-btn-yellow px-5 py-2 text-xs tracking-wider"
          >
            {saving ? 'Salvando...' : 'Salvar Configurações'}
          </button>
        </div>
      </div>
    </div>
  );
};
