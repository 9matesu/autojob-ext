import React from 'react';

interface ErrorBoundaryState {
  error: Error | null;
}

export class ErrorBoundary extends React.Component<{ children: React.ReactNode }, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error): void {
    console.error('AutoJob UI crash:', error);
  }

  render(): React.ReactNode {
    if (!this.state.error) return this.props.children;
    return (
      <div className="h-full flex items-center justify-center p-6 bg-white text-black select-none">
        <div className="brutal-card p-6 max-w-md w-full space-y-4">
          <div className="brutal-tag brutal-tag-black">Erro na interface</div>
          <p className="text-xs font-mono leading-relaxed break-words">
            {String(this.state.error.message || this.state.error)}
          </p>
          <p className="text-[11px] font-mono text-neutral-600">
            Se o motor foi atualizado recentemente, reinicie-o (feche o processo na porta 8322 e reabra o painel).
          </p>
          <button onClick={() => location.reload()} className="brutal-btn-yellow px-4 py-2 text-xs tracking-wider">
            Recarregar
          </button>
        </div>
      </div>
    );
  }
}
