import React, { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { fetchSettings, saveSettings, testAiConnection, fetchProviders, fetchMasterProfile, deleteMasterProfile, type ProviderInfo } from '../../services/api';
import type { AppSettings, MasterCandidate } from '../../services/api';
import { AiProviderFields } from './AiProviderFields';

export const SettingsPanel: React.FC = () => {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [catalog, setCatalog] = useState<ProviderInfo[]>([]);
  const [aiProvider, setAiProvider] = useState('gemini');
  const [aiModel, setAiModel] = useState('');
  const [aiApiKey, setAiApiKey] = useState('');
  const [aiBaseUrl, setAiBaseUrl] = useState('');
  const [baseProfile, setBaseProfile] = useState<MasterCandidate | null>(null);
  const [swapping, setSwapping] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [saved, setSaved] = useState(false);

  const load = async () => {
    try {
      setLoading(true);
      const [data, provs, prof] = await Promise.all([fetchSettings(), fetchProviders(), fetchMasterProfile()]);
      setSettings(data);
      setCatalog(provs);
      setAiProvider(data.ai_provider);
      setAiModel(data.ai_model);
      setAiBaseUrl(data.ai_base_url || '');
      setBaseProfile(prof.has_profile && prof.candidate ? prof.candidate : null);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const effectiveBaseUrl = () => {
    const ent = catalog.find((p) => p.id === aiProvider);
    return aiBaseUrl || ent?.default_base_url || '';
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      await testAiConnection({
        ai_provider: aiProvider,
        ai_api_key: aiApiKey,
        ai_model: aiModel,
        ai_base_url: effectiveBaseUrl(),
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
        ai_base_url: effectiveBaseUrl(),
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
            <AiProviderFields
              catalog={catalog}
              provider={aiProvider}
              model={aiModel}
              apiKey={aiApiKey}
              baseUrl={aiBaseUrl}
              onProviderChange={setAiProvider}
              onModelChange={setAiModel}
              onApiKeyChange={setAiApiKey}
              onBaseUrlChange={setAiBaseUrl}
              keyHint={
                settings?.has_key ? (
                  <span className="text-neutral-500 normal-case tracking-normal">
                    (Configurada: {settings.ai_api_key_masked})
                  </span>
                ) : undefined
              }
            />

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

            {/* Currículo base */}
            <div className="border-2 border-black p-3">
              <div className="font-bold uppercase mb-1">Currículo base</div>
              {baseProfile ? (
                <div className="text-[11px] font-mono space-y-0.5 mb-3">
                  <div className="font-bold text-xs">{baseProfile.name}</div>
                  <div className="text-neutral-600">{baseProfile.email}</div>
                  {baseProfile.source_file && (
                    <div className="text-neutral-500">arquivo: {baseProfile.source_file}</div>
                  )}
                </div>
              ) : (
                <div className="text-[11px] font-mono text-neutral-500 mb-3">nenhum perfil ativo</div>
              )}
              {baseProfile && (
                <button
                  type="button"
                  onClick={async () => {
                    setSwapping(true);
                    try {
                      await deleteMasterProfile();
                      window.location.reload();
                    } catch (err: any) {
                      alert('Falha ao remover perfil: ' + err.message);
                      setSwapping(false);
                    }
                  }}
                  disabled={swapping}
                  className="brutal-btn w-full py-2 text-[11px]"
                >
                  {swapping ? 'Removendo...' : 'Trocar currículo base'}
                </button>
              )}
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
