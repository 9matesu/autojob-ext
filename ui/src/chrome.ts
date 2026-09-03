export const BACKEND = 'http://127.0.0.1:8322';

export const isExtension =
  typeof chrome !== 'undefined' && !!chrome.runtime?.id;

export async function requestCapture(): Promise<unknown> {
  if (!isExtension) throw new Error('Captura DOM disponivel apenas dentro da extensao.');
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) throw new Error('Nenhuma aba ativa encontrada.');
  const res = await chrome.tabs.sendMessage(tab.id, { type: 'autojob-capture' });
  if (!res?.ok) throw new Error(res?.error || 'Falha na captura do painel da vaga.');
  return res.result;
}

export async function captureVisibleTabPng(): Promise<string> {
  if (!isExtension) throw new Error('Captura de tela disponivel apenas dentro da extensao.');
  return chrome.tabs.captureVisibleTab(null as unknown as number, { format: 'png' });
}

export function onCaptureResult(
  onResult: (result: unknown) => void,
  onError: (message: string) => void
): () => void {
  if (!isExtension) return () => {};
  const listener = (msg: any) => {
    if (msg?.type !== 'autojob-capture-result') return;
    if (msg.payload?.ok) onResult(msg.payload.result);
    else onError(String(msg.payload?.error || 'Falha na captura'));
  };
  chrome.runtime.onMessage.addListener(listener);
  return () => chrome.runtime.onMessage.removeListener(listener);
}

const STUDIO_KEY = 'autojob_studio';

export async function saveStudioPayload(data: unknown): Promise<void> {
  if (isExtension) await chrome.storage.local.set({ [STUDIO_KEY]: data });
  else localStorage.setItem(STUDIO_KEY, JSON.stringify(data));
}

export async function loadStudioPayload<T>(): Promise<T | null> {
  if (isExtension) {
    const d = await chrome.storage.local.get(STUDIO_KEY);
    return (d[STUDIO_KEY] as T) ?? null;
  }
  const raw = localStorage.getItem(STUDIO_KEY);
  return raw ? (JSON.parse(raw) as T) : null;
}

export function openStudioTab(): void {
  if (isExtension) chrome.tabs.create({ url: chrome.runtime.getURL('studio.html') });
  else window.open('studio.html', '_blank');
}
