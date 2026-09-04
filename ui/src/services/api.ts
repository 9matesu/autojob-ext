/**
 * AutoJob API Client — talks to the local FastAPI sidecar.
 */
import { BACKEND } from '../chrome';

export interface PersonalInfo {
  name: string;
  email: string;
  phone: string;
  location: string;
  linkedin: string;
  github: string;
  portfolio: string;
}

export interface ExperienceItem {
  title: string;
  company: string;
  period?: string;
  location?: string;
  description: string[];
}

export interface EducationItem {
  institution: string;
  degree?: string;
  field?: string;
  year?: string;
  location?: string;
}

export interface CandidateProfile {
  personal: PersonalInfo;
  summary: string;
  experience: ExperienceItem[];
  leadership?: ExperienceItem[];
  education: EducationItem[];
  skills: string[];
  projects?: Array<{ name: string; role?: string; location?: string; period?: string; description?: string[] | string }>;
  certifications?: Array<{ name: string }>;
  languages?: Array<{ name: string; level?: string }>;
}

export interface JobData {
  id?: string;
  title: string;
  company: string;
  location?: string;
  workplace_type?: string;
  requirements?: string[];
  description?: string;
  keywords?: string[];
  url?: string;
  match_score?: number;
}

export interface AdaptedResult {
  job: JobData;
  captured_chars?: number | null;
  adaptation: {
    id: string;
    match_score: number | null;
    applied_keywords?: string[];
    tailored_profile: CandidateProfile;
    tex_code: string;
    pdf_url: string;
  };
}

export interface AppHealth {
  status: string;
  ai_provider: string;
  ai_model: string;
  has_api_key: boolean;
  compiler_type: string | null;
  compiler_path: string | null;
  has_active_candidate: boolean;
  candidate_name: string | null;
}

export interface AppSettings {
  ai_provider: string;
  ai_model: string;
  ai_api_key_masked: string;
  has_key: boolean;
  ai_base_url: string;
  default_template: string;
  default_lang: string;
  compiler_preference: string;
  detected_compiler: string | null;
  compiler_path: string | null;
}

const API_BASE = `${BACKEND}/api`;

export function absUrl(path: string): string {
  if (!path) return path;
  if (path.startsWith('http')) return path;
  return `${BACKEND}${path}`;
}

function withAbsolutePdf(result: AdaptedResult): AdaptedResult {
  return {
    ...result,
    adaptation: { ...result.adaptation, pdf_url: absUrl(result.adaptation.pdf_url) },
  };
}

export async function fetchHealth(): Promise<AppHealth> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Falha ao conectar no motor AutoJob');
  return res.json();
}

export async function fetchSettings(): Promise<AppSettings> {
  const res = await fetch(`${API_BASE}/settings`);
  if (!res.ok) throw new Error('Falha ao buscar configuracoes');
  return res.json();
}

export async function saveSettings(settings: Partial<AppSettings & { ai_api_key?: string }>): Promise<void> {
  const res = await fetch(`${API_BASE}/settings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
  if (!res.ok) throw new Error('Falha ao salvar configuracoes');
}

export async function testAiConnection(payload: { ai_provider: string; ai_api_key: string; ai_model?: string; ai_base_url?: string }): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/settings/test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Teste de conexao falhou');
  }
  return res.json();
}

export interface ProviderInfo {
  id: string;
  label: string;
  needs_key: boolean;
  default_base_url: string;
  custom_base: boolean;
  key_hint: string;
}

const FALLBACK_PROVIDERS: ProviderInfo[] = [
  { id: 'gemini', label: 'Google Gemini', needs_key: true, default_base_url: '', custom_base: false, key_hint: 'AIzaSy...' },
  { id: 'openai', label: 'OpenAI', needs_key: true, default_base_url: '', custom_base: false, key_hint: 'sk-...' },
  { id: 'ollama', label: 'Ollama (local)', needs_key: false, default_base_url: '', custom_base: true, key_hint: '' },
  { id: 'openai-compatible', label: 'Customizado (OpenAI-compatible)', needs_key: false, default_base_url: '', custom_base: true, key_hint: '' },
];

export async function fetchProviders(): Promise<ProviderInfo[]> {
  try {
    const res = await fetch(`${API_BASE}/providers`);
    if (!res.ok) throw new Error('fallback');
    const data = await res.json();
    if (!Array.isArray(data.providers) || data.providers.length === 0) throw new Error('fallback');
    return data.providers as ProviderInfo[];
  } catch {
    return FALLBACK_PROVIDERS;
  }
}

export async function detectModels(payload: { ai_provider: string; ai_api_key?: string; ai_base_url?: string }): Promise<{ models: string[]; working: string }> {
  const res = await fetch(`${API_BASE}/models`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...payload, probe: true }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Falha ao listar modelos');
  }
  const data = await res.json();
  return {
    models: Array.isArray(data.models) ? (data.models as string[]) : [],
    working: typeof data.working === 'string' ? data.working : '',
  };
}

export interface MasterCandidate {
  id: string;
  name: string;
  email: string;
  source_file: string | null;
}

export async function fetchMasterProfile(): Promise<{ has_profile: boolean; profile: CandidateProfile; candidate?: MasterCandidate }> {
  const res = await fetch(`${API_BASE}/profile`);
  if (!res.ok) throw new Error('Falha ao buscar perfil');
  return res.json();
}

export async function deleteMasterProfile(): Promise<{ status: string; had_active: boolean }> {
  const res = await fetch(`${API_BASE}/profile`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Falha ao remover perfil mestre');
  return res.json();
}

export async function saveMasterProfile(profile: CandidateProfile): Promise<void> {
  const res = await fetch(`${API_BASE}/profile`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: profile.personal.name,
      email: profile.personal.email,
      phone: profile.personal.phone,
      profile,
    }),
  });
  if (!res.ok) throw new Error('Falha ao salvar perfil mestre');
}

export async function parseResumeFile(file: File): Promise<{ profile: CandidateProfile; raw_preview: string }> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/parse-resume`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Falha ao extrair texto do curriculo');
  }
  return res.json();
}

export async function adaptText(jobText: string, pageTitle = '', pageUrl = ''): Promise<AdaptedResult> {
  const res = await fetch(`${API_BASE}/adapt-text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ job_text: jobText, page_title: pageTitle, page_url: pageUrl }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Falha ao adaptar vaga a partir do texto');
  }
  return withAbsolutePdf(await res.json());
}

export async function compileResume(payload: {
  profile?: CandidateProfile;
  raw_tex?: string;
  job?: JobData;
  template?: string;
  lang?: string;
}): Promise<{ status: string; pdf_url: string; tex: string }> {
  const res = await fetch(`${API_BASE}/compile`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Recompilacao LaTeX falhou');
  }
  const data = await res.json();
  return { ...data, pdf_url: absUrl(data.pdf_url) };
}

export async function polishBullet(bullet: string, roleContext?: string): Promise<string> {
  const res = await fetch(`${API_BASE}/polish-bullet`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ bullet, role_context: roleContext }),
  });
  if (!res.ok) throw new Error('Falha ao aprimorar item');
  const data = await res.json();
  return data.polished;
}

export async function fetchHistory(): Promise<Array<{
  id: string;
  title: string;
  company: string;
  location?: string;
  url?: string;
  match_score: number;
  pdf_path: string;
  recruiter_pitch: string;
  created_at: string;
}>> {
  const res = await fetch(`${API_BASE}/history`);
  if (!res.ok) throw new Error('Falha ao buscar historico');
  const data = await res.json();
  return data.history;
}

export function resumePdfUrl(id: string): string {
  return absUrl(`/api/resumes/${id}/pdf`);
}
