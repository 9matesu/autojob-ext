import { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import type { AdaptedResult } from './services/api';
import { loadStudioPayload } from './chrome';
import { StudioWorkspace } from './components/studio/StudioWorkspace';

export function StudioApp() {
  const [data, setData] = useState<AdaptedResult | null>(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    loadStudioPayload<AdaptedResult>().then((d) => {
      if (d) setData(d);
      else setMissing(true);
    });
  }, []);

  if (missing) {
    return (
      <div className="h-screen flex flex-col items-center justify-center gap-3 bg-white text-black font-mono text-center p-6">
        <h1 className="font-editorial text-3xl">Nenhum resultado carregado</h1>
        <p className="text-xs text-neutral-600">
          Abra o painel lateral do AutoJob, capture uma vaga e clique em "Abrir Estúdio".
        </p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="h-screen flex items-center justify-center gap-3 bg-white text-black font-mono text-xs uppercase">
        <Loader2 className="w-5 h-5 animate-spin" />
        Carregando estúdio...
      </div>
    );
  }

  return <StudioWorkspace adaptedData={data} />;
}

export default StudioApp;
