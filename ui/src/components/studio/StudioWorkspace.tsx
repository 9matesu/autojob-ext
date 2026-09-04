import React, { useState, useEffect } from 'react';
import {
  Download,
  RefreshCw,
  FileCode,
  Sliders,
  Trash2,
  Loader2,
  Wand2,
} from 'lucide-react';
import {
  compileResume,
  polishBullet,
  fetchHistory,
  resumePdfUrl,
} from '../../services/api';
import type {
  AdaptedResult,
  CandidateProfile,
} from '../../services/api';

interface StudioWorkspaceProps {
  adaptedData: AdaptedResult;
  onBackToOverlay?: () => void;
}

export const StudioWorkspace: React.FC<StudioWorkspaceProps> = ({ adaptedData }) => {
  const [activeTab, setActiveTab] = useState<'visual' | 'latex'>('visual');
  const [profile, setProfile] = useState<CandidateProfile>(() => {
    const coerceBullets = (d: unknown): string[] =>
      Array.isArray(d)
        ? d.map((x) => String(x))
        : typeof d === 'string' && d.trim()
          ? d.split(/\r?\n/).map((s) => s.trim()).filter(Boolean)
          : [];
    const base = adaptedData.adaptation.tailored_profile;
    const fixEntries = (list: any[] | undefined) =>
      (list || []).map((e) => ({ ...e, description: coerceBullets(e?.description) }));
    return {
      ...base,
      leadership: fixEntries(base.leadership),
      experience: fixEntries(base.experience),
      education: base.education || [],
      projects: base.projects || [],
      certifications: base.certifications || [],
      languages: base.languages || [],
    };
  });
  const [rawTex, setRawTex] = useState(adaptedData.adaptation.tex_code);
  const [pdfUrl, setPdfUrl] = useState(adaptedData.adaptation.pdf_url);
  const [matchScore] = useState(adaptedData.adaptation.match_score ?? 0);

  const [compiling, setCompiling] = useState(false);
  const [polishingIndex, setPolishingIndex] = useState<{ expIdx: number; bIdx: number } | null>(null);
  const [newSkill, setNewSkill] = useState('');
  const [pdfStatus, setPdfStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [pdfKey, setPdfKey] = useState(0);
  const [expired, setExpired] = useState(false);

  // Revalida o snapshot do chrome.storage contra o histórico: o registro
  // pode ter sumido (limpeza) ou o backend pode ter reiniciado.
  useEffect(() => {
    let alive = true;
    fetchHistory()
      .then((items) => {
        if (!alive) return;
        const found = items.some((it) => it.id === adaptedData.adaptation.id);
        if (!found) {
          setExpired(true);
        } else {
          setPdfUrl(resumePdfUrl(adaptedData.adaptation.id));
        }
      })
      .catch(() => {
        // Sem histórico acessível, tenta a URL guardada mesmo assim.
      });
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Recompile PDF
  const handleRecompile = async () => {
    setCompiling(true);
    setPdfStatus('loading');
    try {
      if (activeTab === 'latex') {
        const res = await compileResume({ raw_tex: rawTex, job: adaptedData.job });
        setPdfUrl(`${res.pdf_url}?t=${Date.now()}`);
      } else {
        const res = await compileResume({ profile, job: adaptedData.job });
        setPdfUrl(`${res.pdf_url}?t=${Date.now()}`);
        setRawTex(res.tex);
      }
    } catch (err: any) {
      alert('Erro de compilação: ' + err.message);
    } finally {
      setCompiling(false);
    }
  };

  // AI Polish single bullet (experience or leadership)
  const handlePolishBullet = async (section: 'experience' | 'leadership', expIdx: number, bIdx: number) => {
    setPolishingIndex({ expIdx, bIdx });
    try {
      const list = section === 'experience' ? profile.experience : (profile.leadership || []);
      const currentBullet = list[expIdx].description[bIdx];
      const roleContext = `${adaptedData.job.title} at ${adaptedData.job.company}`;
      const polished = await polishBullet(currentBullet, roleContext);

      const updated = { ...profile };
      const target = (section === 'experience' ? updated.experience : (updated.leadership || [])) as typeof list;
      target[expIdx].description[bIdx] = polished;
      if (section === 'leadership') updated.leadership = target;
      setProfile(updated);
    } catch (err: any) {
      console.error('Polish error:', err);
    } finally {
      setPolishingIndex(null);
    }
  };

  const handleDownload = () => {
    const a = document.createElement('a');
    a.href = pdfUrl;
    a.download = `Curriculo_${adaptedData.job.company.replace(/\s+/g, '_')}_${adaptedData.job.title.replace(/\s+/g, '_')}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const handleAddSkill = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && newSkill.trim() && !profile.skills.includes(newSkill.trim())) {
      setProfile({ ...profile, skills: [...profile.skills, newSkill.trim()] });
      setNewSkill('');
    }
  };

  return (
    <div className="flex flex-col lg:flex-row h-screen w-screen bg-white text-black overflow-hidden select-none">
      {/* LEFT PANE: Editor (empilha no estreito) */}
      <div className="w-full h-1/2 lg:h-full lg:w-1/2 flex flex-col bg-white overflow-hidden border-b lg:border-b-0 border-[#1a1a1a]">
        {/* Top Job Context Bar */}
        <div className="p-4 hairline-b bg-white flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-bold text-black text-sm uppercase tracking-tight">{adaptedData.job.title}</h2>
              <span className="text-xs text-neutral-500 font-medium">na {adaptedData.job.company}</span>
            </div>
            {adaptedData.job.location && (
              <span className="text-[11px] text-neutral-400 mt-0.5 block font-mono">{adaptedData.job.location}</span>
            )}
          </div>

          <div className="flex items-center gap-3">
            {matchScore > 0 && (
              <span className="brutal-tag brutal-tag-yellow">
                {matchScore.toFixed(0)}% Compatibilidade
              </span>
            )}

            {/* Mode Toggle */}
            <div className="flex border-2 border-black text-xs font-bold uppercase">
              <button
                onClick={() => setActiveTab('visual')}
                className={`flex items-center gap-1 px-3 py-1.5 cursor-pointer transition-colors ${activeTab === 'visual' ? 'bg-black text-white' : 'bg-white text-black hover:bg-neutral-100'}`}
              >
                <Sliders className="w-3.5 h-3.5" />
                Visual
              </button>
              <button
                onClick={() => setActiveTab('latex')}
                className={`flex items-center gap-1 px-3 py-1.5 cursor-pointer transition-colors border-l-2 border-black ${activeTab === 'latex' ? 'bg-black text-white' : 'bg-white text-black hover:bg-neutral-100'}`}
              >
                <FileCode className="w-3.5 h-3.5" />
                LaTeX
              </button>
            </div>
          </div>
        </div>

        {/* Scrollable Content Area */}
        <div className="flex-1 overflow-y-auto p-5 space-y-6">
          {activeTab === 'visual' ? (
            <>
              {/* Summary Section */}
              <div className="space-y-2">
                <label className="text-[10px] font-bold uppercase tracking-wider block">
                  Resumo Profissional Adaptado
                </label>
                <textarea
                  rows={3}
                  value={profile.summary}
                  onChange={(e) => setProfile({ ...profile, summary: e.target.value })}
                  className="brutal-input leading-relaxed"
                />
              </div>

              {/* Experience Section */}
              <div className="space-y-4">
                <label className="text-[10px] font-bold uppercase tracking-wider block">
                  Experiências e Conquistas Adaptadas
                </label>

                {profile.experience.map((exp, expIdx) => (
                  <div key={expIdx} className="brutal-card p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="font-bold text-xs uppercase">{exp.title}</span>
                        <span className="text-xs text-neutral-500 ml-2 font-medium">na {exp.company}</span>
                      </div>
                      <span className="text-[11px] text-neutral-400 font-mono">{exp.period}</span>
                    </div>

                    {/* Bullets */}
                    <div className="space-y-2">
                      {exp.description.map((bullet, bIdx) => (
                        <div key={bIdx} className="flex items-start gap-2 group">
                          <span className="mt-2.5 text-xs font-bold">—</span>
                          <textarea
                            rows={2}
                            value={bullet}
                            onChange={(e) => {
                              const updated = { ...profile };
                              updated.experience[expIdx].description[bIdx] = e.target.value;
                              setProfile(updated);
                            }}
                            className="brutal-input flex-1 leading-relaxed"
                          />
                          <div className="flex flex-col gap-1">
                            <button
                              type="button"
                              onClick={() => handlePolishBullet('experience', expIdx, bIdx)}
                              disabled={polishingIndex?.expIdx === expIdx && polishingIndex?.bIdx === bIdx}
                              title="Aprimorar este item com IA"
                              className="brutal-btn p-2 cursor-pointer"
                            >
                              {polishingIndex?.expIdx === expIdx && polishingIndex?.bIdx === bIdx ? (
                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              ) : (
                                <Wand2 className="w-3.5 h-3.5" />
                              )}
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                const updated = { ...profile };
                                updated.experience[expIdx].description = updated.experience[expIdx].description.filter((_, i) => i !== bIdx);
                                setProfile(updated);
                              }}
                              className="brutal-btn p-2 cursor-pointer"
                              title="Remover item"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                      ))}
                      <button
                        type="button"
                        onClick={() => {
                          const updated = { ...profile };
                          updated.experience[expIdx].description.push('Nova conquista sob medida com métrica...');
                          setProfile(updated);
                        }}
                        className="text-[11px] font-bold underline underline-offset-4 inline-flex items-center gap-1 cursor-pointer hover:bg-black hover:text-white px-1 py-0.5 transition-colors"
                      >
                        + Adicionar item de realização
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              {/* Leadership Section (espelha o template) */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <label className="text-[10px] font-bold uppercase tracking-wider block">
                    Atividades de Liderança
                  </label>
                  <button
                    type="button"
                    onClick={() => {
                      setProfile({
                        ...profile,
                        leadership: [
                          ...(profile.leadership || []),
                          { title: '', company: '', location: '', period: '', description: [] },
                        ],
                      });
                    }}
                    className="text-[11px] font-bold underline underline-offset-4 inline-flex items-center gap-1 cursor-pointer hover:bg-black hover:text-white px-1 py-0.5 transition-colors"
                  >
                    + Adicionar atividade
                  </button>
                </div>

                {(profile.leadership || []).map((lead, leadIdx) => (
                  <div key={leadIdx} className="brutal-card p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="font-bold text-xs uppercase">{lead.title || 'Nova atividade'}</span>
                        {lead.company && (
                          <span className="text-xs text-neutral-500 ml-2 font-medium">na {lead.company}</span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] text-neutral-400 font-mono">{lead.period}</span>
                        <button
                          type="button"
                          onClick={() => {
                            setProfile({
                              ...profile,
                              leadership: (profile.leadership || []).filter((_, i) => i !== leadIdx),
                            });
                          }}
                          className="brutal-btn p-1.5 cursor-pointer"
                          title="Remover atividade"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      <input
                        type="text"
                        value={lead.title}
                        onChange={(e) => {
                          const updated = [...(profile.leadership || [])];
                          updated[leadIdx] = { ...updated[leadIdx], title: e.target.value };
                          setProfile({ ...profile, leadership: updated });
                        }}
                        placeholder="Cargo / Posição"
                        className="brutal-input text-xs"
                      />
                      <input
                        type="text"
                        value={lead.company}
                        onChange={(e) => {
                          const updated = [...(profile.leadership || [])];
                          updated[leadIdx] = { ...updated[leadIdx], company: e.target.value };
                          setProfile({ ...profile, leadership: updated });
                        }}
                        placeholder="Organização"
                        className="brutal-input text-xs"
                      />
                      <input
                        type="text"
                        value={lead.location || ''}
                        onChange={(e) => {
                          const updated = [...(profile.leadership || [])];
                          updated[leadIdx] = { ...updated[leadIdx], location: e.target.value };
                          setProfile({ ...profile, leadership: updated });
                        }}
                        placeholder="Local"
                        className="brutal-input text-xs"
                      />
                      <input
                        type="text"
                        value={lead.period || ''}
                        onChange={(e) => {
                          const updated = [...(profile.leadership || [])];
                          updated[leadIdx] = { ...updated[leadIdx], period: e.target.value };
                          setProfile({ ...profile, leadership: updated });
                        }}
                        placeholder="Período"
                        className="brutal-input text-xs"
                      />
                    </div>

                    {/* Bullets */}
                    <div className="space-y-2">
                      {(lead.description || []).map((bullet, bIdx) => (
                        <div key={bIdx} className="flex items-start gap-2 group">
                          <span className="mt-2.5 text-xs font-bold">—</span>
                          <textarea
                            rows={2}
                            value={bullet}
                            onChange={(e) => {
                              const updated = [...(profile.leadership || [])];
                              updated[leadIdx].description[bIdx] = e.target.value;
                              setProfile({ ...profile, leadership: updated });
                            }}
                            className="brutal-input flex-1 leading-relaxed"
                          />
                          <div className="flex flex-col gap-1">
                            <button
                              type="button"
                              onClick={() => handlePolishBullet('leadership', leadIdx, bIdx)}
                              disabled={polishingIndex?.expIdx === leadIdx && polishingIndex?.bIdx === bIdx}
                              title="Aprimorar este item com IA"
                              className="brutal-btn p-2 cursor-pointer"
                            >
                              {polishingIndex?.expIdx === leadIdx && polishingIndex?.bIdx === bIdx ? (
                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              ) : (
                                <Wand2 className="w-3.5 h-3.5" />
                              )}
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                const updated = [...(profile.leadership || [])];
                                updated[leadIdx].description = updated[leadIdx].description.filter((_, i) => i !== bIdx);
                                setProfile({ ...profile, leadership: updated });
                              }}
                              className="brutal-btn p-2 cursor-pointer"
                              title="Remover item"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                      ))}
                      <button
                        type="button"
                        onClick={() => {
                          const updated = [...(profile.leadership || [])];
                          updated[leadIdx].description.push('Novo item de impacto...');
                          setProfile({ ...profile, leadership: updated });
                        }}
                        className="text-[11px] font-bold underline underline-offset-4 inline-flex items-center gap-1 cursor-pointer hover:bg-black hover:text-white px-1 py-0.5 transition-colors"
                      >
                        + Adicionar item de impacto
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              {/* Highlighted Skills */}
              <div className="space-y-2">
                <label className="text-[10px] font-bold uppercase tracking-wider block">
                  Habilidades em Destaque
                </label>
                <div className="flex flex-wrap gap-1.5">
                  {profile.skills.map((skill) => (
                    <span key={skill} className="brutal-tag">
                      {skill}
                      <button
                        onClick={() => setProfile({ ...profile, skills: profile.skills.filter((s) => s !== skill) })}
                        className="font-bold ml-1 hover:bg-black hover:text-white px-0.5 cursor-pointer"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
                <input
                  type="text"
                  value={newSkill}
                  onChange={(e) => setNewSkill(e.target.value)}
                  onKeyDown={handleAddSkill}
                  placeholder="Digite uma habilidade e pressione Enter..."
                  className="brutal-input"
                />
              </div>

              {/* Education Section (espelha o template) */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <label className="text-[10px] font-bold uppercase tracking-wider block">
                    Formação Acadêmica
                  </label>
                  <button
                    type="button"
                    onClick={() => {
                      setProfile({
                        ...profile,
                        education: [
                          ...profile.education,
                          { institution: '', degree: '', year: '', location: '' },
                        ],
                      });
                    }}
                    className="text-[11px] font-bold underline underline-offset-4 inline-flex items-center gap-1 cursor-pointer hover:bg-black hover:text-white px-1 py-0.5 transition-colors"
                  >
                    + Adicionar formação
                  </button>
                </div>

                {profile.education.map((edu, eduIdx) => (
                  <div key={eduIdx} className="brutal-card p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-xs uppercase">{edu.institution || 'Nova formação'}</span>
                      <button
                        type="button"
                        onClick={() => {
                          setProfile({
                            ...profile,
                            education: profile.education.filter((_, i) => i !== eduIdx),
                          });
                        }}
                        className="brutal-btn p-1.5 cursor-pointer"
                        title="Remover formação"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      <input
                        type="text"
                        value={edu.institution}
                        onChange={(e) => {
                          const updated = [...profile.education];
                          updated[eduIdx] = { ...updated[eduIdx], institution: e.target.value };
                          setProfile({ ...profile, education: updated });
                        }}
                        placeholder="Instituição"
                        className="brutal-input text-xs"
                      />
                      <input
                        type="text"
                        value={edu.degree || ''}
                        onChange={(e) => {
                          const updated = [...profile.education];
                          updated[eduIdx] = { ...updated[eduIdx], degree: e.target.value };
                          setProfile({ ...profile, education: updated });
                        }}
                        placeholder="Curso / Grau"
                        className="brutal-input text-xs"
                      />
                      <input
                        type="text"
                        value={edu.location || ''}
                        onChange={(e) => {
                          const updated = [...profile.education];
                          updated[eduIdx] = { ...updated[eduIdx], location: e.target.value };
                          setProfile({ ...profile, education: updated });
                        }}
                        placeholder="Local"
                        className="brutal-input text-xs"
                      />
                      <input
                        type="text"
                        value={edu.year || ''}
                        onChange={(e) => {
                          const updated = [...profile.education];
                          updated[eduIdx] = { ...updated[eduIdx], year: e.target.value };
                          setProfile({ ...profile, education: updated });
                        }}
                        placeholder="Ano / Período"
                        className="brutal-input text-xs"
                      />
                    </div>
                  </div>
                ))}
              </div>

              {(profile.projects || []).length > 0 && (
                <div className="space-y-2">
                  <label className="text-[10px] font-bold uppercase tracking-wider block">
                    Projetos
                  </label>
                  {(profile.projects || []).map((p, pIdx) => (
                    <div key={pIdx} className="brutal-card p-3 flex items-center justify-between gap-2">
                      <span className="text-xs font-bold">{p.name}</span>
                      <button
                        type="button"
                        onClick={() => {
                          setProfile({
                            ...profile,
                            projects: (profile.projects || []).filter((_, i) => i !== pIdx),
                          });
                        }}
                        className="brutal-btn p-1.5 cursor-pointer"
                        title="Remover projeto"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {(profile.certifications || []).length > 0 && (
                <div className="space-y-2">
                  <label className="text-[10px] font-bold uppercase tracking-wider block">
                    Certificações
                  </label>
                  {(profile.certifications || []).map((c, cIdx) => (
                    <div key={cIdx} className="brutal-card p-3 flex items-center justify-between gap-2">
                      <span className="text-xs font-bold">{typeof c === 'string' ? c : c.name}</span>
                      <button
                        type="button"
                        onClick={() => {
                          setProfile({
                            ...profile,
                            certifications: (profile.certifications || []).filter((_, i) => i !== cIdx),
                          });
                        }}
                        className="brutal-btn p-1.5 cursor-pointer"
                        title="Remover certificação"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            /* Raw LaTeX Source Tab */
            <div className="h-full flex flex-col">
              <label className="text-[10px] font-bold uppercase tracking-wider mb-2 block">
                Código-Fonte LaTeX (Jinja2 / Tectonic)
              </label>
              <textarea
                value={rawTex}
                onChange={(e) => setRawTex(e.target.value)}
                className="flex-1 min-h-[500px] w-full p-4 bg-black font-mono text-xs text-white border-2 border-black focus:outline-none leading-relaxed selection:bg-[#ffff00] selection:text-black"
                spellCheck={false}
              />
            </div>
          )}
        </div>

        {/* Bottom Action Footer */}
        <div className="p-4 hairline-t bg-white flex items-center justify-between">
          <span className="text-xs text-neutral-600 font-mono">
            {compiling ? 'Compilando LaTeX com Tectonic...' : 'Alterações prontas para recompilação'}
          </span>
          <button
            onClick={handleRecompile}
            disabled={compiling}
            className="brutal-btn-yellow flex items-center gap-2 px-5 py-2.5 text-xs tracking-wider"
          >
            {compiling ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
            <span>{compiling ? 'Compilando PDF...' : 'Recompilar e Atualizar PDF'}</span>
          </button>
        </div>
      </div>

      {/* RIGHT PANE: Live PDF Viewer */}
      <div className="w-full h-1/2 lg:h-full lg:w-1/2 flex flex-col bg-neutral-100">
        {/* Viewer Toolbar */}
        <div className="p-3 hairline-b bg-white flex items-center justify-between">
          <span className="text-xs font-bold flex items-center gap-2">
            <span className="uppercase">Pré-visualização do PDF ATS</span>
          </span>

          <div className="flex items-center gap-2">
            <button
              onClick={handleDownload}
              className="brutal-btn-yellow flex items-center gap-1.5 px-4 py-1.5 text-[11px]"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Baixar PDF</span>
            </button>
          </div>
        </div>

        {/* Embedded PDF iframe */}
        <div className="flex-1 w-full h-full bg-neutral-200 p-4">
          <div className="w-full h-full overflow-hidden border-2 border-black bg-white shadow-[8px_8px_0px_0px_#000000] relative">
            {expired ? (
              <div className="w-full h-full flex flex-col items-center justify-center gap-3 p-6 text-center">
                <span className="brutal-tag brutal-tag-black">Resultado expirado</span>
                <p className="text-xs font-mono text-neutral-600 max-w-xs">
                  Este resultado não está mais no histórico. Capture a vaga novamente no painel.
                </p>
                <button onClick={() => window.close()} className="brutal-btn px-4 py-2 text-[11px]">
                  Fechar aba
                </button>
              </div>
            ) : (
              <>
                {pdfStatus === 'loading' && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-white">
                    <Loader2 className="w-8 h-8 animate-spin" />
                    <span className="text-[11px] font-mono uppercase">Carregando PDF...</span>
                  </div>
                )}
                {pdfStatus === 'error' && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 p-6 text-center bg-white">
                    <span className="brutal-tag brutal-tag-black">Falha ao carregar</span>
                    <p className="text-xs font-mono text-neutral-600 max-w-xs">
                      Não foi possível abrir a pré-visualização. Confira se o motor está rodando.
                    </p>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => {
                          setPdfStatus('loading');
                          setPdfKey((k) => k + 1);
                        }}
                        className="brutal-btn px-4 py-2 text-[11px]"
                      >
                        Tentar novamente
                      </button>
                      <button onClick={handleDownload} className="brutal-btn-yellow px-4 py-2 text-[11px]">
                        Baixar PDF
                      </button>
                    </div>
                  </div>
                )}
                <iframe
                  key={pdfKey}
                  src={pdfUrl}
                  title="Pré-visualização do Currículo"
                  className="w-full h-full border-none"
                  onLoad={() => setPdfStatus('ready')}
                  onError={() => setPdfStatus('error')}
                />
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
