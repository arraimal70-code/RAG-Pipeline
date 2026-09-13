import { useState, useMemo } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { sourceFiles } from './data/sourceCode';
import { documentation } from './data/documentation';
import { experiments, failureModes, demoScenarios, costQualityData, latencyBreakdown } from './data/experiments';

type Section = 'overview' | 'architecture' | 'pipeline' | 'source' | 'experiments' | 'failures' | 'docs' | 'metrics';

const navItems: { id: Section; label: string; icon: string }[] = [
  { id: 'overview', label: 'Overview', icon: '🏠' },
  { id: 'architecture', label: 'Architecture', icon: '🏗️' },
  { id: 'pipeline', label: 'Pipeline', icon: '⚡' },
  { id: 'source', label: 'Source', icon: '💻' },
  { id: 'experiments', label: 'Experiments', icon: '🧪' },
  { id: 'failures', label: 'Failures', icon: '🔬' },
  { id: 'docs', label: 'Docs', icon: '📚' },
  { id: 'metrics', label: 'Metrics', icon: '📊' },
];

export default function App() {
  const [activeSection, setActiveSection] = useState<Section>('overview');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const renderContent = () => {
    switch (activeSection) {
      case 'overview': return <OverviewSection onNavigate={setActiveSection} />;
      case 'architecture': return <ArchitectureSection />;
      case 'pipeline': return <PipelineSection />;
      case 'source': return <SourceSection />;
      case 'experiments': return <ExperimentsSection />;
      case 'failures': return <FailuresSection />;
      case 'docs': return <DocsSection />;
      case 'metrics': return <MetricsSection />;
      default: return null;
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col">
      <header className="sticky top-0 z-50 bg-gray-950/90 backdrop-blur-xl border-b border-gray-800/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-400 to-cyan-500 flex items-center justify-center text-sm font-bold text-gray-900">R</div>
              <div className="hidden sm:block">
                <h1 className="text-sm font-bold text-white leading-tight">Evidence-Aware Adaptive RAG</h1>
                <p className="text-[10px] text-gray-500 leading-tight">Research System • Results Pending</p>
              </div>
            </div>
            <nav className="hidden lg:flex items-center gap-0.5">
              {navItems.map((item) => (
                <button key={item.id} onClick={() => setActiveSection(item.id)}
                  className={`px-2 py-1.5 rounded-md text-xs font-medium transition-all ${
                    activeSection === item.id ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
                  }`}>
                  <span className="mr-1">{item.icon}</span>{item.label}
                </button>
              ))}
            </nav>
            <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="lg:hidden p-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={mobileMenuOpen ? "M6 18L18 6M6 6l12 12" : "M4 6h16M4 12h16M4 18h16"} />
              </svg>
            </button>
          </div>
        </div>
        {mobileMenuOpen && (
          <div className="lg:hidden border-t border-gray-800/50 bg-gray-950/95 backdrop-blur-xl">
            <div className="px-4 py-2 space-y-0.5">
              {navItems.map((item) => (
                <button key={item.id} onClick={() => { setActiveSection(item.id); setMobileMenuOpen(false); }}
                  className={`w-full text-left px-3 py-2 rounded-md text-sm font-medium ${activeSection === item.id ? 'bg-emerald-500/10 text-emerald-400' : 'text-gray-400 hover:text-white'}`}>
                  <span className="mr-2">{item.icon}</span>{item.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </header>

      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 w-full">{renderContent()}</main>

      <footer className="border-t border-gray-800/50 py-4 text-center text-xs text-gray-600">
        Evidence-Aware Adaptive RAG • LangChain • ChromaDB • Hybrid Retrieval • All results marked RESULTS PENDING until experiments execute
      </footer>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   OVERVIEW
   ═══════════════════════════════════════════════════════════ */
function OverviewSection({ onNavigate }: { onNavigate: (s: Section) => void }) {
  return (
    <div className="space-y-8">
      <div className="text-center py-6 space-y-4">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-medium">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse"></span>
          Research System • Experiments Pending
        </div>
        <h2 className="text-2xl sm:text-3xl font-bold bg-gradient-to-r from-white via-gray-200 to-gray-400 bg-clip-text text-transparent leading-tight">
          Evidence-Aware Adaptive RAG
        </h2>
        <p className="max-w-2xl mx-auto text-sm text-gray-400 leading-relaxed">
          An adaptive retrieval-augmented generation system that investigates whether query-aware retrieval,
          evidence sufficiency assessment, and abstention mechanisms improve factual reliability while balancing latency and cost.
        </p>
      </div>

      {/* Research Question */}
      <div className="p-5 rounded-xl bg-gradient-to-r from-emerald-500/5 to-cyan-500/5 border border-emerald-500/20">
        <h3 className="text-sm font-bold text-emerald-400 mb-2">Central Research Question</h3>
        <p className="text-sm text-gray-300 italic leading-relaxed">
          "How can a RAG system dynamically balance retrieval quality, factual reliability, latency, and computational cost
          while recognizing when available evidence is insufficient to answer a question?"
        </p>
      </div>

      {/* Priority Stack */}
      <div className="p-4 rounded-xl bg-gray-900/50 border border-gray-800/50">
        <h3 className="text-xs font-bold text-gray-400 mb-2 uppercase tracking-wide">Priority Stack</h3>
        <div className="flex flex-wrap items-center gap-1.5">
          {['FAITHFULNESS', 'RETRIEVAL QUALITY', 'TRACEABILITY', 'PERFORMANCE', 'UX'].map((p, i) => (
            <div key={p} className="flex items-center gap-1.5">
              <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                i === 0 ? 'bg-emerald-500/20 text-emerald-400' : i === 1 ? 'bg-cyan-500/15 text-cyan-400' :
                i === 2 ? 'bg-blue-500/15 text-blue-400' : i === 3 ? 'bg-purple-500/15 text-purple-400' : 'bg-gray-700/50 text-gray-400'
              }`}>{p}</span>
              {i < 4 && <span className="text-gray-700 text-xs">{'>'}</span>}
            </div>
          ))}
        </div>
      </div>

      {/* Key Components Grid */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {[
          { icon: '🧠', title: 'Adaptive Retrieval', desc: 'Query-type-aware weight adjustment', phase: 'Phase 9' },
          { icon: '🔍', title: 'Hybrid Retrieval', desc: 'Dense + BM25 + RRF + Reranking', phase: 'Phase 5' },
          { icon: '✅', title: 'Evidence Sufficiency', desc: 'Assess before generating', phase: 'Phase 8' },
          { icon: '⚡', title: 'Contradiction Detection', desc: 'Flag conflicting sources', phase: 'Phase 12' },
          { icon: '📎', title: 'Citation Validation', desc: 'Verify citations against evidence', phase: 'Phase 8' },
          { icon: '🚫', title: 'Abstention System', desc: 'Refuse when evidence insufficient', phase: 'Phase 9' },
          { icon: '🧪', title: '19 Experiments', desc: 'Systematic ablation studies', phase: 'Phase 11' },
          { icon: '🔬', title: '15 Failure Categories', desc: 'Formal failure taxonomy', phase: 'Phase 13' },
          { icon: '📊', title: 'Evaluation Framework', desc: 'Recall@K, MRR, nDCG, + generation', phase: 'Phase 6' },
        ].map(c => (
          <div key={c.title} className="p-3 rounded-lg bg-gray-900/50 border border-gray-800/50 hover:border-gray-700/50 transition-all">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-base">{c.icon}</span>
              <span className="text-xs font-bold text-white">{c.title}</span>
            </div>
            <p className="text-[10px] text-gray-500">{c.desc}</p>
            <p className="text-[9px] text-gray-700 mt-1">{c.phase}</p>
          </div>
        ))}
      </div>

      {/* Honest Status */}
      <div className="p-4 rounded-xl bg-amber-500/5 border border-amber-500/20">
        <div className="flex items-start gap-3">
          <span className="text-lg">⚠️</span>
          <div>
            <h4 className="text-sm font-bold text-amber-400">Honest Status</h4>
            <p className="text-xs text-gray-400 mt-1 leading-relaxed">
              The infrastructure is complete. The architecture is implemented. Tests exist. Documentation is thorough.
              <strong className="text-gray-300"> No experiments have been executed yet.</strong> All quantitative claims
              are marked "RESULTS PENDING." No numbers are fabricated. The system is designed to produce evidence —
              that evidence will come when experiments run with real documents.
            </p>
          </div>
        </div>
      </div>

      {/* Quick Navigation */}
      <div className="grid sm:grid-cols-4 gap-2">
        {[
          { section: 'architecture' as Section, icon: '🏗️', title: 'Architecture', desc: 'Full adaptive pipeline' },
          { section: 'source' as Section, icon: '💻', title: 'Source Code', desc: 'Complete Python implementation' },
          { section: 'experiments' as Section, icon: '🧪', title: 'Experiments', desc: '19 experiments + ablations' },
          { section: 'failures' as Section, icon: '🔬', title: 'Failure Analysis', desc: '15-category taxonomy' },
        ].map(nav => (
          <button key={nav.section} onClick={() => onNavigate(nav.section)}
            className="p-3 rounded-xl bg-gray-900/50 border border-gray-800/50 hover:border-emerald-500/30 transition-all text-left">
            <span className="text-lg">{nav.icon}</span>
            <h4 className="font-semibold text-white text-xs mt-1">{nav.title}</h4>
            <p className="text-[10px] text-gray-500">{nav.desc}</p>
          </button>
        ))}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   ARCHITECTURE
   ═══════════════════════════════════════════════════════════ */
function ArchitectureSection() {
  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold text-white">Adaptive Pipeline Architecture</h2>
        <p className="text-sm text-gray-400">Query → Analysis → Adaptive Retrieval → Evidence Check → Generate or Abstain</p>
      </div>

      {/* Full Pipeline Diagram */}
      <div className="p-4 rounded-xl bg-gray-900/50 border border-gray-800/50 overflow-x-auto">
        <div className="min-w-[650px] space-y-4">
          {/* Query Analysis */}
          <div className="flex items-center gap-2">
            <div className="px-3 py-2 rounded-lg border border-blue-500/30 bg-blue-500/5 min-w-[100px] text-center">
              <span className="text-sm">❓</span>
              <p className="text-[10px] font-bold text-white">Query</p>
            </div>
            <span className="text-gray-600 text-xs">→</span>
            <div className="px-3 py-2 rounded-lg border border-blue-500/30 bg-blue-500/5 min-w-[140px] text-center">
              <span className="text-sm">🧠</span>
              <p className="text-[10px] font-bold text-white">Query Analyzer</p>
              <p className="text-[9px] text-gray-500">classify type</p>
            </div>
            <span className="text-gray-600 text-xs">→</span>
            <div className="flex gap-1">
              {['EXACT', 'CONCEPTUAL', 'MULTI_HOP', 'UNKNOWN'].map(t => (
                <span key={t} className="px-1.5 py-0.5 rounded text-[8px] font-mono bg-gray-800 text-gray-400 border border-gray-700/50">{t}</span>
              ))}
            </div>
          </div>

          {/* Adaptive Weights */}
          <div className="flex items-center gap-2">
            <div className="px-3 py-2 rounded-lg border border-purple-500/30 bg-purple-500/5 min-w-[140px] text-center">
              <span className="text-sm">⚖️</span>
              <p className="text-[10px] font-bold text-white">Adaptive Weights</p>
              <p className="text-[9px] text-gray-500">dense↔BM25 per type</p>
            </div>
            <span className="text-gray-600 text-xs">→</span>
            <div className="flex gap-3 text-[9px] text-gray-500">
              <span>EXACT: <span className="text-cyan-400">BM25 0.7</span></span>
              <span>CONCEPT: <span className="text-emerald-400">Dense 0.8</span></span>
              <span>UNKNOWN: <span className="text-gray-400">50/50</span></span>
            </div>
          </div>

          {/* Dual Retrieval */}
          <div className="flex items-center gap-2">
            <div className="px-3 py-2 rounded-lg border border-emerald-500/30 bg-emerald-500/5 text-center">
              <p className="text-[10px] font-bold text-white">Dense (top-50)</p>
              <p className="text-[9px] text-gray-500">cosine similarity</p>
            </div>
            <span className="text-gray-500 text-[10px]">+</span>
            <div className="px-3 py-2 rounded-lg border border-cyan-500/30 bg-cyan-500/5 text-center">
              <p className="text-[10px] font-bold text-white">BM25 (top-50)</p>
              <p className="text-[9px] text-gray-500">lexical matching</p>
            </div>
            <span className="text-gray-600 text-xs">→</span>
            <div className="px-3 py-2 rounded-lg border border-purple-500/30 bg-purple-500/5 text-center">
              <p className="text-[10px] font-bold text-white">RRF Fusion</p>
              <p className="text-[9px] text-gray-500">1/(k+rank)</p>
            </div>
            <span className="text-gray-600 text-xs">→</span>
            <div className="px-3 py-2 rounded-lg border border-amber-500/30 bg-amber-500/5 text-center">
              <p className="text-[10px] font-bold text-white">Rerank</p>
              <p className="text-[9px] text-gray-500">cross-encoder</p>
            </div>
          </div>

          {/* Evidence Check - Branching */}
          <div className="flex items-center gap-2">
            <div className="px-3 py-2 rounded-lg border border-pink-500/30 bg-pink-500/5 min-w-[140px] text-center">
              <span className="text-sm">✅</span>
              <p className="text-[10px] font-bold text-white">Evidence Sufficiency</p>
              <p className="text-[9px] text-gray-500">score + agreement + coverage</p>
            </div>
            <span className="text-gray-600 text-xs">→</span>
            <div className="flex gap-2">
              <div className="px-2 py-1 rounded border border-emerald-500/30 bg-emerald-500/5 text-center">
                <p className="text-[9px] font-bold text-emerald-400">→ Answer</p>
              </div>
              <div className="px-2 py-1 rounded border border-amber-500/30 bg-amber-500/5 text-center">
                <p className="text-[9px] font-bold text-amber-400">→ Retrieve More</p>
              </div>
              <div className="px-2 py-1 rounded border border-red-500/30 bg-red-500/5 text-center">
                <p className="text-[9px] font-bold text-red-400">→ Abstain</p>
              </div>
            </div>
          </div>

          {/* Generation + Validation */}
          <div className="flex items-center gap-2">
            <div className="px-3 py-2 rounded-lg border border-indigo-500/30 bg-indigo-500/5 text-center">
              <p className="text-[10px] font-bold text-white">LLM Generate</p>
              <p className="text-[9px] text-gray-500">gpt-4o-mini, temp=0</p>
            </div>
            <span className="text-gray-600 text-xs">→</span>
            <div className="px-3 py-2 rounded-lg border border-emerald-500/30 bg-emerald-500/5 text-center">
              <p className="text-[10px] font-bold text-white">Citation Validate</p>
              <p className="text-[9px] text-gray-500">check against chunks</p>
            </div>
            <span className="text-gray-600 text-xs">→</span>
            <div className="px-3 py-2 rounded-lg border border-red-500/30 bg-red-500/5 text-center">
              <p className="text-[10px] font-bold text-white">Contradiction Check</p>
              <p className="text-[9px] text-gray-500">cross-source conflicts</p>
            </div>
            <span className="text-gray-600 text-xs">→</span>
            <div className="px-3 py-2 rounded-lg border border-white/20 bg-white/5 text-center">
              <p className="text-[10px] font-bold text-white">Answer + Citations</p>
            </div>
          </div>
        </div>
      </div>

      {/* Key Design Decisions */}
      <div className="grid md:grid-cols-2 gap-4">
        {[
          { title: 'Why Adaptive Retrieval?', text: 'Different query types benefit from different strategies. "What was Q3 revenue?" needs lexical matching. "How does the methodology work?" needs semantic understanding. Fixed weights leave quality on the table.' },
          { title: 'Why Evidence Sufficiency?', text: 'A system that always answers will hallucinate on unanswerable questions. Checking evidence quality before generation prevents unsupported answers. The cost of a wrong answer exceeds the cost of no answer.' },
          { title: 'Why RRF over Weighted Fusion?', text: 'Score scales differ between retrievers (cosine ∈ [0,1], BM25 ∈ [0,∞)). RRF uses only rank information, which is more robust. Reference: Cormack et al., 2009.' },
          { title: 'Why Rule-Based Query Classification?', text: 'LLM-based classification adds latency (~200ms), cost, and noise. Rule-based patterns are fast (<1ms), deterministic, and debuggable. Sufficient for the granularity needed.' },
        ].map(d => (
          <div key={d.title} className="p-4 rounded-xl bg-gray-900/50 border border-gray-800/50">
            <h4 className="text-xs font-bold text-emerald-400 mb-1">{d.title}</h4>
            <p className="text-xs text-gray-400 leading-relaxed">{d.text}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   PIPELINE
   ═══════════════════════════════════════════════════════════ */
function PipelineSection() {
  const [expanded, setExpanded] = useState<number | null>(0);
  const stages = [
    { num: 1, icon: '📄', title: 'Document Parsing', phase: 'Phase 3', desc: 'PyMuPDF extraction with structure detection, header/footer removal, metadata.', points: ['pypdf for reliable text extraction', 'Header/footer detection and removal', 'Metadata extraction (title, author, pages)', 'Content hashing for deduplication', 'File validation (size, type, page count)'] },
    { num: 2, icon: '✂️', title: 'Chunking (4 Strategies)', phase: 'Phase 4', desc: 'Fixed-size, sentence-based, recursive, structure-aware.', points: ['Fixed: predictable, simple splitting', 'Sentence: never splits mid-sentence', 'Recursive: hierarchical separator splitting', 'Structure: heading/section-aware', 'Configurable size, overlap, min/max', 'Metadata preserved through all strategies'] },
    { num: 3, icon: '🔢', title: 'Embedding', phase: 'Phase 5', desc: 'Configurable: local (MiniLM) or API (OpenAI).', points: ['Local: all-MiniLM-L6-v2 (free, 384-dim)', 'OpenAI: text-embedding-3-small (1536-dim)', 'Batch processing for efficiency', 'Model caching (load once)', 'Normalized embeddings for cosine similarity'] },
    { num: 4, icon: '💾', title: 'Dual Indexing', phase: 'Phase 5', desc: 'ChromaDB (dense) + BM25 (lexical).', points: ['ChromaDB: persistent vector store with metadata', 'BM25: lexical index for keyword matching', 'Both persist to disk for fast reload', 'Support incremental updates', 'Cosine similarity for dense search'] },
    { num: 5, icon: '🧠', title: 'Query Analysis', phase: 'Phase 9', desc: 'Classify query type for adaptive retrieval.', points: ['Rule-based classification (fast, deterministic)', 'Types: EXACT, CONCEPTUAL, MULTI_HOP, AMBIGUOUS', 'Maps to optimal dense/BM25 weights', 'Adjusts candidate count per complexity', 'Falls back to UNKNOWN (balanced) when uncertain'] },
    { num: 6, icon: '🔍', title: 'Adaptive Hybrid Retrieval', phase: 'Phase 5-9', desc: 'Dense + BM25 with query-type-adaptive weights.', points: ['Dense: top-50 by cosine similarity', 'BM25: top-50 by lexical score', 'Adaptive weighted fusion per query type', 'RRF as alternative fusion method', 'Cross-encoder reranking for precision', 'Full latency tracking per stage'] },
    { num: 7, icon: '✅', title: 'Evidence Sufficiency', phase: 'Phase 8', desc: 'Assess evidence before generating answer.', points: ['Retrieval score quality assessment', 'Evidence agreement between sources', 'Evidence coverage of the question', 'Contradiction detection across sources', 'Recommendation: answer / retrieve_more / abstain'] },
    { num: 8, icon: '🤖', title: 'Generation + Citations', phase: 'Phase 7-9', desc: 'LLM with grounding, citation extraction, validation.', points: ['Strict grounding instructions in prompt', 'Citation extraction [CITE:chunk_N]', 'Citation validation against retrieved chunks', 'Support-level classification (4 levels)', 'Explicit abstention when evidence insufficient'] },
    { num: 9, icon: '⚡', title: 'Contradiction Handling', phase: 'Phase 12', desc: 'Detect and report conflicting information.', points: ['Numerical contradictions across documents', 'Temporal contradictions detection', 'Both sources cited with page numbers', 'User informed of uncertainty', 'Severity classification (minor/major/critical)'] },
  ];

  return (
    <div className="space-y-5">
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold text-white">Pipeline Stages</h2>
        <p className="text-sm text-gray-400">9 stages from ingestion to validated answer</p>
      </div>
      <div className="space-y-2">
        {stages.map((stage, idx) => (
          <div key={idx} className={`rounded-xl border transition-all ${expanded === idx ? 'border-emerald-500/30 bg-gray-900/80' : 'border-gray-800/50 bg-gray-900/30 hover:border-gray-700/50'}`}>
            <button onClick={() => setExpanded(expanded === idx ? null : idx)} className="w-full flex items-center gap-3 p-3 text-left">
              <div className="w-9 h-9 rounded-lg bg-gray-800 flex items-center justify-center text-base shrink-0">{stage.icon}</div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2"><span className="text-[9px] font-mono text-gray-600">STAGE {stage.num}</span><span className="text-[9px] text-gray-700">•</span><span className="text-[9px] text-gray-600">{stage.phase}</span></div>
                <h3 className="text-sm font-bold text-white">{stage.title}</h3>
              </div>
              <svg className={`w-4 h-4 text-gray-500 transition-transform shrink-0 ${expanded === idx ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
            </button>
            {expanded === idx && (
              <div className="px-3 pb-3">
                <ul className="space-y-1">{stage.points.map((p, i) => (<li key={i} className="flex items-start gap-2 text-xs text-gray-400"><span className="text-emerald-400 mt-0.5 shrink-0">•</span>{p}</li>))}</ul>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Demo Scenarios */}
      <div className="pt-4">
        <h3 className="text-lg font-bold text-white mb-3">Demonstration Scenarios</h3>
        <div className="grid sm:grid-cols-2 gap-2">
          {demoScenarios.map(d => (
            <div key={d.id} className="p-3 rounded-lg bg-gray-900/50 border border-gray-800/50">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm">{d.icon}</span>
                <span className="text-xs font-bold text-white">{d.title}</span>
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-500 ml-auto">{d.type}</span>
              </div>
              <p className="text-[10px] text-gray-400 italic mb-1">"{d.question}"</p>
              <p className="text-[10px] text-gray-500"><span className="text-emerald-400/70">Strategy:</span> {d.retrievalStrategy}</p>
              <p className="text-[10px] text-gray-500 mt-0.5"><span className="text-cyan-400/70">Expected:</span> {d.expectedBehavior}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   SOURCE CODE
   ═══════════════════════════════════════════════════════════ */
function SourceSection() {
  const [activeFile, setActiveFile] = useState(0);
  const [filterCat, setFilterCat] = useState('all');

  const categories = useMemo(() => ['all', ...new Set(sourceFiles.map(f => f.category))], []);
  const filtered = useMemo(() => filterCat === 'all' ? sourceFiles : sourceFiles.filter(f => f.category === filterCat), [filterCat]);
  const file = filtered[activeFile] || filtered[0];

  return (
    <div className="space-y-4">
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold text-white">Source Code</h2>
        <p className="text-sm text-gray-400">Complete, commented implementation of every component</p>
      </div>

      <div className="flex flex-wrap gap-1">
        {categories.map(cat => (
          <button key={cat} onClick={() => { setFilterCat(cat); setActiveFile(0); }}
            className={`px-2 py-0.5 rounded text-[10px] font-medium transition-all ${filterCat === cat ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' : 'bg-gray-800/50 text-gray-500 border border-gray-700/50 hover:text-gray-300'}`}>
            {cat === 'all' ? 'All' : cat}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap gap-1">
        {filtered.map((f, idx) => (
          <button key={f.path} onClick={() => setActiveFile(idx)}
            className={`px-2 py-0.5 rounded text-[10px] font-mono transition-all truncate max-w-[180px] ${activeFile === idx ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30' : 'bg-gray-800/30 text-gray-500 border border-gray-800/50 hover:text-gray-300'}`}>
            {f.path.split('/').pop()}
          </button>
        ))}
      </div>

      {file && (
        <>
          <div className="flex items-center gap-3 p-2.5 rounded-lg bg-gray-900/50 border border-gray-800/50">
            <span className="text-base">{file.path.endsWith('.py') ? '🐍' : file.path.endsWith('.json') ? '📋' : file.path.endsWith('.yml') ? '⚙️' : '🐳'}</span>
            <div className="flex-1 min-w-0">
              <p className="text-[10px] font-mono text-gray-300 truncate">{file.path}</p>
              <p className="text-[10px] text-gray-500">{file.description}</p>
            </div>
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-500 shrink-0">{file.phase}</span>
          </div>
          <CodeBlock code={file.code} language={file.language} filename={file.path} />
        </>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   EXPERIMENTS
   ═══════════════════════════════════════════════════════════ */
function ExperimentsSection() {
  const [filterCat, setFilterCat] = useState('all');
  const cats = useMemo(() => ['all', ...new Set(experiments.map(e => e.category))], []);
  const filtered = useMemo(() => filterCat === 'all' ? experiments : experiments.filter(e => e.category === filterCat), [filterCat]);

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold text-white">Experiment Framework</h2>
        <p className="text-sm text-gray-400">19 experiments + ablation studies • All results pending execution</p>
      </div>

      {/* Category filter */}
      <div className="flex flex-wrap gap-1">
        {cats.map(cat => (
          <button key={cat} onClick={() => setFilterCat(cat)}
            className={`px-2 py-0.5 rounded text-[10px] font-medium transition-all ${filterCat === cat ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' : 'bg-gray-800/50 text-gray-500 border border-gray-700/50 hover:text-gray-300'}`}>
            {cat === 'all' ? 'All' : cat}
          </button>
        ))}
      </div>

      {/* Experiment table */}
      <div className="rounded-xl border border-gray-800/50 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-[10px]">
            <thead>
              <tr className="border-b border-gray-800/50 bg-gray-900/50">
                <th className="text-left px-2 py-1.5 text-gray-500 font-medium">ID</th>
                <th className="text-left px-2 py-1.5 text-gray-500 font-medium">Name</th>
                <th className="text-left px-2 py-1.5 text-gray-500 font-medium hidden md:table-cell">Hypothesis</th>
                <th className="text-left px-2 py-1.5 text-gray-500 font-medium hidden lg:table-cell">Variables</th>
                <th className="text-left px-2 py-1.5 text-gray-500 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(exp => (
                <tr key={exp.id} className="border-b border-gray-800/20 hover:bg-gray-800/20">
                  <td className="px-2 py-1.5 font-mono text-emerald-400">{exp.id}</td>
                  <td className="px-2 py-1.5 text-gray-300 font-medium">{exp.name}</td>
                  <td className="px-2 py-1.5 text-gray-500 hidden md:table-cell max-w-[200px] truncate">{exp.hypothesis}</td>
                  <td className="px-2 py-1.5 text-gray-600 font-mono hidden lg:table-cell">{exp.variables}</td>
                  <td className="px-2 py-1.5"><span className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[9px]">pending</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Cost-Quality Frontier */}
      <div className="p-4 rounded-xl bg-gray-900/50 border border-gray-800/50">
        <h3 className="text-sm font-bold text-white mb-3">Cost-Quality Frontier <span className="text-[10px] text-amber-400 font-normal">(projected, not measured)</span></h3>
        <div className="space-y-2">
          {costQualityData.map(d => (
            <div key={d.label} className="flex items-center gap-3">
              <span className="text-[10px] text-gray-400 w-24 shrink-0">{d.label}</span>
              <div className="flex-1 flex items-center gap-2">
                <div className="flex-1 h-3 rounded-full bg-gray-800 overflow-hidden">
                  <div className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-cyan-500" style={{ width: `${d.quality * 100}%` }}></div>
                </div>
                <span className="text-[9px] text-gray-500 w-12 text-right">{(d.quality * 100).toFixed(0)}%</span>
              </div>
              <span className="text-[9px] text-gray-600 w-16 text-right">${d.costPerQuery}/query</span>
              <span className="text-[9px] text-gray-600 w-12 text-right">{d.latencyMs}ms</span>
            </div>
          ))}
        </div>
        <p className="text-[9px] text-gray-600 mt-2 italic">Quality scores are illustrative projections, not measured results. Actual values will come from experiments.</p>
      </div>

      {/* Latency Breakdown */}
      <div className="p-4 rounded-xl bg-gray-900/50 border border-gray-800/50">
        <h3 className="text-sm font-bold text-white mb-3">Latency Breakdown <span className="text-[10px] text-gray-500 font-normal">(per-stage estimate)</span></h3>
        <div className="space-y-1.5">
          {latencyBreakdown.map(s => (
            <div key={s.stage} className="flex items-center gap-2">
              <span className="text-[10px] text-gray-400 w-32 shrink-0">{s.stage}</span>
              <div className="flex-1 h-2.5 rounded-full bg-gray-800 overflow-hidden">
                <div className={`h-full rounded-full ${s.color}`} style={{ width: `${(s.ms / 130) * 100}%` }}></div>
              </div>
              <span className="text-[9px] text-gray-500 w-10 text-right">{s.ms}ms</span>
            </div>
          ))}
          <div className="flex items-center gap-2 pt-1 border-t border-gray-800/50">
            <span className="text-[10px] text-white font-bold w-32">Total (estimated)</span>
            <div className="flex-1"></div>
            <span className="text-[10px] text-white font-bold w-10 text-right">{latencyBreakdown.reduce((a, b) => a + b.ms, 0)}ms</span>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   FAILURES
   ═══════════════════════════════════════════════════════════ */
function FailuresSection() {
  const [selectedSeverity, setSelectedSeverity] = useState<string>('all');
  const filtered = selectedSeverity === 'all' ? failureModes : failureModes.filter(f => f.severity === selectedSeverity);

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold text-white">Failure Analysis</h2>
        <p className="text-sm text-gray-400">15-category failure taxonomy for systematic failure understanding</p>
      </div>

      {/* Severity filter */}
      <div className="flex gap-1.5">
        {['all', 'critical', 'high', 'medium', 'low'].map(s => (
          <button key={s} onClick={() => setSelectedSeverity(s)}
            className={`px-2 py-0.5 rounded text-[10px] font-medium capitalize transition-all ${selectedSeverity === s ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' : 'bg-gray-800/50 text-gray-500 border border-gray-700/50'}`}>
            {s}
          </button>
        ))}
      </div>

      {/* Failure cards */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
        {filtered.map(f => (
          <div key={f.id} className={`p-3 rounded-xl border ${
            f.severity === 'critical' ? 'border-red-500/20 bg-red-500/5' :
            f.severity === 'high' ? 'border-amber-500/20 bg-amber-500/5' :
            'border-gray-800/50 bg-gray-900/50'
          }`}>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm">{f.icon}</span>
              <span className="text-xs font-bold text-white">{f.name}</span>
              <span className={`ml-auto text-[8px] px-1 py-0.5 rounded capitalize ${
                f.severity === 'critical' ? 'bg-red-500/20 text-red-400' :
                f.severity === 'high' ? 'bg-amber-500/20 text-amber-400' : 'bg-gray-700 text-gray-400'
              }`}>{f.severity}</span>
            </div>
            <p className="text-[10px] text-gray-400 mb-1">{f.description}</p>
            <p className="text-[9px] text-gray-500"><span className="text-emerald-400/70">Detect:</span> {f.detection}</p>
            <p className="text-[9px] text-gray-500"><span className="text-cyan-400/70">Fix:</span> {f.mitigation}</p>
          </div>
        ))}
      </div>

      {/* Retrieval vs Generation distinction */}
      <div className="p-4 rounded-xl bg-gray-900/50 border border-gray-800/50">
        <h3 className="text-sm font-bold text-white mb-2">Failure Decomposition</h3>
        <p className="text-xs text-gray-400 mb-3">Critical distinction in RAG evaluation:</p>
        <div className="grid sm:grid-cols-2 gap-3">
          {[
            { title: 'Retrieval Failure', desc: 'Correct evidence exists but was not retrieved. The system never had a chance to answer correctly.', color: 'emerald' },
            { title: 'Generation Failure', desc: 'Evidence was retrieved correctly but the LLM produced an incorrect answer.', color: 'cyan' },
            { title: 'Citation Failure', desc: 'Answer is correct but citations do not point to actual evidence.', color: 'purple' },
            { title: 'Evidence Failure', desc: 'Evidence itself is conflicting, insufficient, or contradictory.', color: 'amber' },
          ].map(d => (
            <div key={d.title} className="p-2.5 rounded-lg bg-gray-800/30 border border-gray-800/50">
              <p className={`text-[10px] font-bold ${d.color === 'emerald' ? 'text-emerald-400' : d.color === 'cyan' ? 'text-cyan-400' : d.color === 'purple' ? 'text-purple-400' : 'text-amber-400'}`}>{d.title}</p>
              <p className="text-[10px] text-gray-500 mt-0.5">{d.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   DOCS
   ═══════════════════════════════════════════════════════════ */
function DocsSection() {
  const [activeDoc, setActiveDoc] = useState(0);
  const doc = documentation[activeDoc];

  return (
    <div className="space-y-4">
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold text-white">Documentation</h2>
        <p className="text-sm text-gray-400">Architecture, decisions, security, reproducibility, research</p>
      </div>

      <div className="flex flex-wrap gap-1">
        {documentation.map((d, idx) => (
          <button key={d.path} onClick={() => setActiveDoc(idx)}
            className={`px-2 py-1 rounded-lg text-[10px] font-medium transition-all ${activeDoc === idx ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' : 'bg-gray-800/30 text-gray-500 border border-gray-800/50 hover:text-gray-300'}`}>
            <span className="mr-1">{d.icon}</span>{d.title}
          </button>
        ))}
      </div>

      {doc && (
        <div className="space-y-2">
          <div className="flex items-center gap-3 p-2.5 rounded-lg bg-gray-900/50 border border-gray-800/50">
            <span className="text-lg">{doc.icon}</span>
            <div><p className="text-xs font-bold text-white">{doc.title}</p><p className="text-[10px] font-mono text-gray-500">{doc.path}</p></div>
            <span className="ml-auto text-[9px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-500">{doc.category}</span>
          </div>
          <div className="rounded-xl border border-gray-800/50 overflow-hidden">
            <div className="max-h-[600px] overflow-y-auto p-4 bg-gray-900/30">
              <MarkdownRenderer content={doc.content} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   METRICS
   ═══════════════════════════════════════════════════════════ */
function MetricsSection() {
  const supportLevels = [
    { level: 'SUPPORTED', color: 'emerald', desc: 'Answer directly and clearly supported by retrieved context' },
    { level: 'PARTIALLY_SUPPORTED', color: 'cyan', desc: 'Answer partially supported but requires inference' },
    { level: 'UNSUPPORTED', color: 'red', desc: 'Answer goes beyond what context provides' },
    { level: 'INSUFFICIENT_EVIDENCE', color: 'gray', desc: 'Not enough context → system abstains' },
  ];

  const retrievalMetrics = [
    { name: 'Recall@1', desc: 'Is the top result relevant?' },
    { name: 'Recall@3', desc: 'Are relevant chunks in top 3?' },
    { name: 'Recall@5', desc: 'Are relevant chunks in top 5?' },
    { name: 'Recall@10', desc: 'Are relevant chunks in top 10?' },
    { name: 'MRR', desc: 'Mean Reciprocal Rank of first relevant' },
    { name: 'nDCG@5', desc: 'Normalized Discounted Cumulative Gain' },
    { name: 'Hit Rate', desc: 'Fraction of queries with any relevant result' },
    { name: 'Source Accuracy', desc: 'Correct document retrieved' },
    { name: 'Passage Accuracy', desc: 'Correct passage retrieved' },
  ];

  const generationMetrics = [
    { name: 'Factual Correctness', desc: 'Answer matches expected answer' },
    { name: 'Groundedness', desc: 'Answer supported by retrieved evidence' },
    { name: 'Citation Precision', desc: 'Cited sources actually support claims' },
    { name: 'Citation Recall', desc: 'Necessary evidence was cited' },
    { name: 'Hallucination Rate', desc: 'Answers with unsupported claims' },
    { name: 'Abstention Accuracy', desc: 'Correct refusal on unanswerable' },
    { name: 'Contradiction Detection', desc: 'Conflicting sources flagged' },
  ];

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold text-white">Evaluation Metrics</h2>
        <p className="text-sm text-gray-400">Comprehensive metrics for retrieval, generation, and system quality</p>
      </div>

      {/* Support Levels */}
      <div className="rounded-xl border border-gray-800/50 overflow-hidden">
        <div className="p-2.5 bg-gray-900/50 border-b border-gray-800/50"><h3 className="text-xs font-bold text-white">Answer Support Classification</h3></div>
        <div className="grid sm:grid-cols-2 gap-px bg-gray-800/30">
          {supportLevels.map(s => (
            <div key={s.level} className="flex items-center gap-2 p-2.5 bg-gray-900/50">
              <div className={`w-1.5 h-6 rounded-full ${s.color === 'emerald' ? 'bg-emerald-400' : s.color === 'cyan' ? 'bg-cyan-400' : s.color === 'red' ? 'bg-red-400' : 'bg-gray-500'}`}></div>
              <div>
                <p className={`text-[10px] font-bold font-mono ${s.color === 'emerald' ? 'text-emerald-400' : s.color === 'cyan' ? 'text-cyan-400' : s.color === 'red' ? 'text-red-400' : 'text-gray-400'}`}>{s.level}</p>
                <p className="text-[9px] text-gray-500">{s.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Retrieval Metrics */}
      <div className="rounded-xl border border-gray-800/50 overflow-hidden">
        <div className="p-2.5 bg-gray-900/50 border-b border-gray-800/50"><h3 className="text-xs font-bold text-white">Retrieval Metrics</h3></div>
        <div className="grid sm:grid-cols-3 gap-px bg-gray-800/30">
          {retrievalMetrics.map(m => (
            <div key={m.name} className="p-2.5 bg-gray-900/50">
              <p className="text-[10px] font-bold text-emerald-400 font-mono">{m.name}</p>
              <p className="text-[9px] text-gray-500">{m.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Generation Metrics */}
      <div className="rounded-xl border border-gray-800/50 overflow-hidden">
        <div className="p-2.5 bg-gray-900/50 border-b border-gray-800/50"><h3 className="text-xs font-bold text-white">Generation & Reliability Metrics</h3></div>
        <div className="grid sm:grid-cols-2 gap-px bg-gray-800/30">
          {generationMetrics.map(m => (
            <div key={m.name} className="p-2.5 bg-gray-900/50">
              <p className="text-[10px] font-bold text-cyan-400 font-mono">{m.name}</p>
              <p className="text-[9px] text-gray-500">{m.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Benchmark Categories */}
      <div className="p-4 rounded-xl bg-gray-900/50 border border-gray-800/50">
        <h3 className="text-xs font-bold text-white mb-2">Benchmark Question Types (15 categories)</h3>
        <div className="grid grid-cols-3 sm:grid-cols-5 gap-1.5">
          {['Direct Lookup', 'Multi-hop', 'Numerical', 'Definition', 'Comparison', 'Summarization', 'Cross-section', 'Cross-document', 'Ambiguous', 'Unanswerable', 'Adversarial', 'Table-based', 'Contradictory', 'Temporal', 'Long-context'].map(t => (
            <div key={t} className="px-1.5 py-1 rounded bg-gray-800/30 border border-gray-800/50 text-[9px] text-gray-400 text-center">{t}</div>
          ))}
        </div>
      </div>

      {/* Status */}
      <div className="p-3 rounded-xl bg-amber-500/5 border border-amber-500/20">
        <p className="text-[10px] text-amber-400 font-bold">⚠️ All metrics show RESULTS PENDING until experiments execute with real data.</p>
        <p className="text-[9px] text-gray-500 mt-1">The evaluation infrastructure is complete. Metric computation code exists. The benchmark dataset template is ready for population with verified ground truth.</p>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   SHARED COMPONENTS
   ═══════════════════════════════════════════════════════════ */
function CodeBlock({ code, language, filename }: { code: string; language: string; filename: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => { navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 2000); };

  return (
    <div className="rounded-xl overflow-hidden border border-gray-700/50 shadow-xl">
      <div className="flex items-center justify-between px-3 py-1.5 bg-gray-800 border-b border-gray-700/50">
        <div className="flex items-center gap-2">
          <div className="flex gap-1"><div className="w-2 h-2 rounded-full bg-red-500/70"></div><div className="w-2 h-2 rounded-full bg-yellow-500/70"></div><div className="w-2 h-2 rounded-full bg-green-500/70"></div></div>
          <span className="text-[9px] text-gray-400 font-mono truncate max-w-[200px]">{filename}</span>
        </div>
        <button onClick={handleCopy} className="flex items-center gap-1 px-2 py-0.5 text-[9px] rounded bg-gray-700 hover:bg-gray-600 text-gray-300 transition-all">
          {copied ? '✓ Copied' : 'Copy'}
        </button>
      </div>
      <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
        <SyntaxHighlighter language={language === 'json' ? 'json' : language === 'yaml' ? 'yaml' : language === 'dockerfile' ? 'docker' : 'python'}
          style={oneDark} customStyle={{ margin: 0, padding: '0.75rem', fontSize: '0.65rem', lineHeight: '1.5', background: '#1a1a2e' }} wrapLines={true}>
          {code}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}

function MarkdownRenderer({ content }: { content: string }) {
  const lines = content.split('\n');
  const elements: JSX.Element[] = [];
  let inCodeBlock = false;
  let codeContent = '';

  lines.forEach((line, i) => {
    if (line.startsWith('```')) {
      if (inCodeBlock) {
        elements.push(<pre key={`code-${i}`} className="my-2 p-2 rounded-lg bg-gray-800/50 text-[10px] font-mono text-gray-300 overflow-x-auto"><code>{codeContent.trim()}</code></pre>);
        codeContent = '';
        inCodeBlock = false;
      } else { inCodeBlock = true; }
      return;
    }
    if (inCodeBlock) { codeContent += line + '\n'; return; }

    if (line.startsWith('# ')) elements.push(<h1 key={i} className="text-base font-bold text-white mt-3 mb-1">{line.slice(2)}</h1>);
    else if (line.startsWith('## ')) elements.push(<h2 key={i} className="text-sm font-bold text-white mt-3 mb-1">{line.slice(3)}</h2>);
    else if (line.startsWith('### ')) elements.push(<h3 key={i} className="text-xs font-bold text-gray-200 mt-2 mb-1">{line.slice(4)}</h3>);
    else if (line.startsWith('#### ')) elements.push(<h4 key={i} className="text-[10px] font-bold text-gray-300 mt-1.5 mb-0.5">{line.slice(5)}</h4>);
    else if (line.startsWith('- [x] ') || line.startsWith('- [ ] ')) {
      const checked = line.startsWith('- [x]');
      elements.push(<div key={i} className="flex items-center gap-1.5 text-[10px] text-gray-400 py-0.5"><span className={checked ? 'text-emerald-400' : 'text-gray-600'}>{checked ? '✓' : '○'}</span><span className={checked ? 'text-gray-300' : ''}>{line.slice(6)}</span></div>);
    }
    else if (line.startsWith('- ')) elements.push(<div key={i} className="flex items-start gap-1.5 text-[10px] text-gray-400 py-0.5"><span className="text-gray-600 mt-0.5">•</span><span dangerouslySetInnerHTML={{ __html: line.slice(2).replace(/\*\*(.+?)\*\*/g, '<strong class="text-gray-200">$1</strong>').replace(/`(.+?)`/g, '<code class="px-0.5 rounded bg-gray-800 text-emerald-400/80">$1</code>') }} /></div>);
    else if (line.startsWith('| ') && line.includes('|')) {
      const cells = line.split('|').filter(c => c.trim()).map(c => c.trim());
      if (cells.every(c => c.match(/^[-:]+$/))) return;
      elements.push(<div key={i} className="flex gap-2 text-[10px] py-0.5 border-b border-gray-800/30">{cells.map((cell, j) => (<span key={j} className={`${j === 0 ? 'text-gray-300 font-medium min-w-[80px]' : 'text-gray-500'}`}>{cell}</span>))}</div>);
    }
    else if (line.startsWith('> ')) elements.push(<div key={i} className="pl-2 border-l-2 border-emerald-500/30 text-[10px] text-gray-400 italic my-1">{line.slice(2)}</div>);
    else if (line.trim() === '') elements.push(<div key={i} className="h-1.5"></div>);
    else if (line.startsWith('---')) elements.push(<hr key={i} className="border-gray-800/50 my-2" />);
    else elements.push(<p key={i} className="text-[10px] text-gray-400 leading-relaxed" dangerouslySetInnerHTML={{ __html: line.replace(/\*\*(.+?)\*\*/g, '<strong class="text-gray-200">$1</strong>').replace(/`(.+?)`/g, '<code class="px-0.5 rounded bg-gray-800 text-emerald-400/80 text-[9px]">$1</code>').replace(/\*(.+?)\*/g, '<em class="text-gray-300">$1</em>') }} />);
  });

  return <div className="space-y-0">{elements}</div>;
}
