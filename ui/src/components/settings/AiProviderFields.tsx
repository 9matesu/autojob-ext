import React, { useState } from 'react';
import { Loader2 } from 'lucide-react';
import { detectModels, type ProviderInfo } from '../../services/api';

interface AiProviderFieldsProps {
  catalog: ProviderInfo[];
  provider: string;
  model: string;
  apiKey: string;
  baseUrl: string;
  onProviderChange: (id: string) => void;
  onModelChange: (v: string) => void;
  onApiKeyChange: (v: string) => void;
  onBaseUrlChange: (v: string) => void;
  keyHint?: React.ReactNode;
}

export const AiProviderFields: React.FC<AiProviderFieldsProps> = ({
  catalog,
  provider,
  model,
  apiKey,
  baseUrl,
  onProviderChange,
  onModelChange,
  onApiKeyChange,
  onBaseUrlChange,
  keyHint,
}) => {
  const [models, setModels] = useState<string[]>([]);
  const [detecting, setDetecting] = useState(false);
  const [detectMsg, setDetectMsg] = useState('');

  const entry = catalog.find((p) => p.id === provider);
  const listId = React.useId();

  const handleProvider = (id: string) => {
    const next = catalog.find((p) => p.id === id);
    onProviderChange(id);
    if (next?.default_model) onModelChange(next.default_model);
    setModels([]);
    setDetectMsg('');
  };

  const handleDetect = async () => {
    if (entry?.needs_key && !apiKey) {
      setDetectMsg('Informe a chave de API para listar os modelos.');
      return;
    }
    setDetecting(true);
    setDetectMsg('');
    try {
      const list = await detectModels({
        ai_provider: provider,
        ...(apiKey ? { ai_api_key: apiKey } : {}),
        ...(baseUrl ? { ai_base_url: baseUrl } : {}),
      });
      setModels(list);
      setDetectMsg(
        list.length > 0
          ? `${list.length} modelo(s) detectado(s) — escolha na lista ou digite.`
          : 'O provedor não listou modelos — digite o nome manualmente.'
      );
    } catch (err: any) {
      setModels([]);
      setDetectMsg(err.message || 'Falha ao listar modelos');
    } finally {
      setDetecting(false);
    }
  };

  return (
    <>
      <div>
        <label className="text-[10px] font-bold uppercase tracking-wider block mb-1">Provedor de IA</label>
        <select value={provider} onChange={(e) => handleProvider(e.target.value)} className="brutal-input cursor-pointer">
          {catalog.map((p) => (
            <option key={p.id} value={p.id}>
              {p.label}
            </option>
          ))}
        </select>
      </div>

      {entry?.needs_key && (
        <div>
          <label className="text-[10px] font-bold uppercase tracking-wider block mb-1">
            Chave de API {keyHint}
          </label>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => onApiKeyChange(e.target.value)}
            placeholder={entry.key_hint || 'Insira a Chave de API'}
            className="brutal-input"
          />
        </div>
      )}

      {entry?.custom_base && (
        <div>
          <label className="text-[10px] font-bold uppercase tracking-wider block mb-1">URL base (opcional)</label>
          <input
            type="text"
            value={baseUrl}
            onChange={(e) => onBaseUrlChange(e.target.value)}
            placeholder={entry.default_base_url || 'http://localhost:11434/v1'}
            className="brutal-input font-mono"
          />
        </div>
      )}

      <div>
        <label className="text-[10px] font-bold uppercase tracking-wider block mb-1">Nome do Modelo</label>
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={model}
            onChange={(e) => onModelChange(e.target.value)}
            placeholder="Ex: gemini-2.0-flash"
            list={listId}
            className="brutal-input flex-1"
          />
          <datalist id={listId}>
            {models.map((m) => (
              <option key={m} value={m} />
            ))}
          </datalist>
          <button
            type="button"
            onClick={handleDetect}
            disabled={detecting}
            className="brutal-btn px-3 py-2 text-[11px] shrink-0 flex items-center gap-1.5"
            title="Detectar modelos disponíveis no provedor"
          >
            {detecting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            <span>{detecting ? 'Lendo...' : 'Detectar'}</span>
          </button>
        </div>
        {detectMsg && <p className="text-[11px] text-neutral-500 mt-1 font-mono">{detectMsg}</p>}
      </div>
    </>
  );
};
