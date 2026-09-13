import { useState, useMemo } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { sourceFiles } from './data/sourceCode';
import { documentation } from './data/documentation';

type Section = 'overview' | 'architecture' | 'pipeline' | 'source' | 'experiments' | 'docs' | 'metrics';

const navItems: { id: Section; label: string; icon: string }[] = [
  { id: 'overview', label: 'Overview', icon: '🏠' },
  { id: 'architecture', label: 'Architecture', icon: '🏗️' },
  { id: 'pipeline', label: 'Pipeline', icon: '⚡' },
  { id: 'source', label: 'Source Code', icon: '💻' },
  { id: 'experiments', label: 'Experiments', icon: '🧪' },
  { id: 'docs', label: 'Documentation', icon: '📚' },
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
      case 'docs': return <DocsSection />;
      case 'metrics': return <MetricsSection />;
      default: return null;
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-gray-950/90 backdrop-blur-xl border-b border-gray-800/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-400 to-cyan-500 flex items-center justify-center text-sm font-bold text-gray-900">
                R
              </div>
              <div className="hidden sm:block">
                <h1 className="text-sm font-bold text-white leading-tight">RAG Pipeline</h1>
                <p className="text-[10px] text-gray-500 leading-tight">Research-Grade Document Intelligence</p>
              </div>
            </div>
            <nav className="hidden lg:flex items-center gap-0.5">
              {navItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setActiveSection(item.id)}
                  className={`px-2.5 py-1.5 rounded-md text-xs font-medium transition-all ${
                    activeSection === item.id
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
                  }`}
                >
                  <span className="mr-1">{item.icon}</span>{item.label}
                </button>
              ))}
            </nav>
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="lg:hidden p-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d={mobileMenuOpen ? "M6 18L18 6M6 6l12 12" : "M4 6h16M4 12h16M4 18h16"} />
              </svg>
            </button>
          </div>
        </div>
        {mobileMenuOpen && (
          <div className="lg:hidden border-t border-gray-800/50 bg-gray-950/95 backdrop-blur-xl">
            <div className="px-4 py-2 space-y-0.5">
              {navItems.map((item) => (
                <button key={item.id}
                  onClick={() => { setActiveSection(item.id); setMobileMenuOpen(false); }}
                  className={`w-full text-left px-3 py-2 rounded-md text-sm font-medium transition-all ${
                    activeSection === item.id ? 'bg-emerald-500/10 text-emerald-400' : 'text-gray-400 hover:text-white'
                  }`}>
                  <span className="mr-2">{item.icon}</span>{item.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </header>

      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 w-full">
        {renderContent()}
      </main>

      <footer className="border-t border-gray-800/50 py-4 text-center text-xs text-gray-600">
        Research-Grade RAG Pipeline • LangChain • ChromaDB • Hybrid Retrieval • Evaluation Framework
      </footer>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   OVERVIEW SECTION
   ═══════════════════════════════════════════════════════════ */
function OverviewSection({ onNavigate }: { onNavigate: (s: Section) => void }) {
  return (
    <div className="space-y-10">
      {/* Hero */}
      <div className="text-center py-8 space-y-5">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-medium">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse"></span>
          Research-Grade RAG System
        </div>
        <h2 className="text-3xl sm:text-4xl font-bold bg-gradient-to-r from-white via-gray-200 to-gray-400 bg-clip-text text-transparent leading-tight">
          Document-Grounded QA<br />with Experimental Validation
        </h2>
        <p className="max-w-2xl mx-auto text-sm text-gray-400 leading-relaxed">
          A modular RAG pipeline that investigates how retrieval strategy, chunking, reranking,
          and abstention affect factual reliability, citation accuracy, and cost.
          Every architectural decision is measured, not assumed.
        </p>
      </div>

      {/* Key principles */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { icon: '🎯', title: 'Faithfulness First', desc: 'Answers grounded in evidence, not hallucination' },
          { icon: '📏', title: 'Measured, Not Claimed', desc: 'Every component validated by experiments' },
          { icon: '🔬', title: 'Failure Analysis', desc: 'Formal taxonomy of how and why systems fail' },
          { icon: '🔄', title: 'Reproducible', desc: 'Config snapshots, locked deps, experiment tracking' },
        ].map(p => (
          <div key={p.title} className="p-4 rounded-xl bg-gray-900/50 border border-gray-800/50">
            <span className="text-xl">{p.icon}</span>
            <h4 className="font-semibold text-white text-sm mt-2">{p.title}</h4>
            <p className="text-xs text-gray-500 mt-1">{p.desc}</p>
          </div>
        ))}
      </div>

      {/* Priority stack */}
      <div className="p-5 rounded-xl bg-gray-900/50 border border-gray-800/50">
        <h3 className="font-bold text-white mb-3">Priority Stack</h3>
        <div className="flex flex-wrap items-center gap-2">
          {['FAITHFULNESS', 'RETRIEVAL QUALITY', 'TRACEABILITY', 'PERFORMANCE', 'UX'].map((p, i) => (
            <div key={p} className="flex items-center gap-2">
              <span className={`px-3 py-1 rounded-md text-xs font-mono font-bold ${
                i === 0 ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                i === 1 ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/20' :
                i === 2 ? 'bg-blue-500/15 text-blue-400 border border-blue-500/20' :
                i === 3 ? 'bg-purple-500/15 text-purple-400 border border-purple-500/20' :
                'bg-gray-700/50 text-gray-400 border border-gray-600/30'
              }`}>{p}</span>
              {i < 4 && <span className="text-gray-600 text-xs">{'>'}</span>}
            </div>
          ))}
        </div>
      </div>

      {/* What this project investigates */}
      <div className="grid md:grid-cols-2 gap-6">
        <div className="space-y-4">
          <h3 className="text-xl font-bold text-white">Research Questions</h3>
          <div className="space-y-2">
            {[
              'Does hybrid retrieval (dense + BM25) outperform dense-only?',
              'Does cross-encoder reranking improve citation accuracy?',
              'Which chunking strategy produces the best retrieval quality?',
              'Can abstention reduce hallucination without excessive false refusals?',
              'What is the latency/cost tradeoff of each pipeline component?',
            ].map((q, i) => (
              <div key={i} className="flex items-start gap-2 text-sm">
                <span className="text-emerald-400 font-mono text-xs mt-0.5 shrink-0">RQ{i+1}</span>
                <span className="text-gray-400">{q}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="space-y-4">
          <h3 className="text-xl font-bold text-white">System Components</h3>
          <div className="grid grid-cols-2 gap-2">
            {[
              { label: 'PDF Parser', phase: 'Phase 3' },
              { label: '4 Chunking Strategies', phase: 'Phase 4' },
              { label: 'Dense Retrieval', phase: 'Phase 5' },
              { label: 'BM25 Retrieval', phase: 'Phase 5' },
              { label: 'Hybrid Fusion (RRF)', phase: 'Phase 5' },
              { label: 'Cross-Encoder Rerank', phase: 'Phase 5' },
              { label: 'Citation Validation', phase: 'Phase 8' },
              { label: 'Abstention System', phase: 'Phase 9' },
              { label: 'Evaluation Framework', phase: 'Phase 6-7' },
              { label: 'Experiment Runner', phase: 'Phase 11' },
              { label: 'Failure Analysis', phase: 'Phase 13' },
              { label: 'FastAPI Server', phase: 'Phase 19' },
            ].map(c => (
              <div key={c.label} className="flex items-center gap-2 p-2 rounded-lg bg-gray-800/30 border border-gray-800/50">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-400/60"></div>
                <div>
                  <p className="text-xs text-gray-300">{c.label}</p>
                  <p className="text-[10px] text-gray-600">{c.phase}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Quick navigation */}
      <div className="grid sm:grid-cols-3 gap-3">
        <button onClick={() => onNavigate('source')}
          className="p-4 rounded-xl bg-gray-900/50 border border-gray-800/50 hover:border-emerald-500/30 transition-all text-left group">
          <span className="text-lg">💻</span>
          <h4 className="font-semibold text-white text-sm mt-2 group-hover:text-emerald-400 transition-colors">Source Code</h4>
          <p className="text-xs text-gray-500 mt-1">Complete Python implementation with comments</p>
        </button>
        <button onClick={() => onNavigate('experiments')}
          className="p-4 rounded-xl bg-gray-900/50 border border-gray-800/50 hover:border-cyan-500/30 transition-all text-left group">
          <span className="text-lg">🧪</span>
          <h4 className="font-semibold text-white text-sm mt-2 group-hover:text-cyan-400 transition-colors">Experiments</h4>
          <p className="text-xs text-gray-500 mt-1">Ablation studies and configuration comparison</p>
        </button>
        <button onClick={() => onNavigate('docs')}
          className="p-4 rounded-xl bg-gray-900/50 border border-gray-800/50 hover:border-purple-500/30 transition-all text-left group">
          <span className="text-lg">📚</span>
          <h4 className="font-semibold text-white text-sm mt-2 group-hover:text-purple-400 transition-colors">Documentation</h4>
          <p className="text-xs text-gray-500 mt-1">Architecture, decisions, security, reproducibility</p>
        </button>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   ARCHITECTURE SECTION
   ═══════════════════════════════════════════════════════════ */
function ArchitectureSection() {
  return (
    <div className="space-y-8">
      <div className="text-center space-y-3">
        <h2 className="text-2xl font-bold text-white">System Architecture</h2>
        <p className="text-sm text-gray-400">Modular pipeline with clean interfaces between stages</p>
      </div>

      {/* Ingestion Pipeline */}
      <div className="p-5 rounded-xl bg-gray-900/50 border border-gray-800/50 overflow-x-auto">
        <div className="flex items-center gap-2 mb-4">
          <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-medium">
            Ingestion Pipeline
          </span>
          <span className="text-gray-600 text-xs">— Run once per document set</span>
        </div>
        <div className="min-w-[600px] flex items-center gap-2 flex-wrap">
          {[
            { icon: '📄', label: 'PDFs', sub: 'documents/' },
            { icon: '🔍', label: 'Parser', sub: 'pypdf + metadata' },
            { icon: '🏗️', label: 'Structure', sub: 'heading detection' },
            { icon: '✂️', label: 'Chunker', sub: '4 strategies' },
            { icon: '🔢', label: 'Embed', sub: 'MiniLM / OpenAI' },
            { icon: '💾', label: 'Indexes', sub: 'Chroma + BM25' },
          ].map((step, i, arr) => (
            <div key={i} className="flex items-center gap-2">
              <div className="flex flex-col items-center px-3 py-2 rounded-lg border border-emerald-500/20 bg-emerald-500/5 min-w-[90px]">
                <span className="text-lg">{step.icon}</span>
                <span className="text-xs font-semibold text-white">{step.label}</span>
                <span className="text-[10px] text-gray-500">{step.sub}</span>
              </div>
              {i < arr.length - 1 && <span className="text-gray-600 text-xs">→</span>}
            </div>
          ))}
        </div>
      </div>

      {/* Query Pipeline */}
      <div className="p-5 rounded-xl bg-gray-900/50 border border-gray-800/50 overflow-x-auto">
        <div className="flex items-center gap-2 mb-4">
          <span className="px-2 py-0.5 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-xs font-medium">
            Query Pipeline
          </span>
          <span className="text-gray-600 text-xs">— Run for each question</span>
        </div>
        <div className="min-w-[600px] flex items-center gap-2 flex-wrap">
          {[
            { icon: '❓', label: 'Query', sub: 'embed query' },
            { icon: '🔍', label: 'Dense', sub: 'top-50 cosine' },
            { icon: '📝', label: 'BM25', sub: 'top-50 lexical' },
            { icon: '🔀', label: 'RRF Fusion', sub: 'combine signals' },
            { icon: '⚖️', label: 'Rerank', sub: 'cross-encoder' },
            { icon: '🤖', label: 'LLM', sub: 'gpt-4o-mini' },
            { icon: '✅', label: 'Validate', sub: 'citations' },
          ].map((step, i, arr) => (
            <div key={i} className="flex items-center gap-2">
              <div className="flex flex-col items-center px-3 py-2 rounded-lg border border-cyan-500/20 bg-cyan-500/5 min-w-[85px]">
                <span className="text-lg">{step.icon}</span>
                <span className="text-xs font-semibold text-white">{step.label}</span>
                <span className="text-[10px] text-gray-500">{step.sub}</span>
              </div>
              {i < arr.length - 1 && <span className="text-gray-600 text-xs">→</span>}
            </div>
          ))}
        </div>
      </div>

      {/* Component details */}
      <div className="grid md:grid-cols-3 gap-4">
        {[
          { title: 'Retrieval', items: ['Dense (cosine similarity)', 'BM25 (lexical matching)', 'RRF fusion', 'Cross-encoder rerank'], color: 'emerald' },
          { title: 'Generation', items: ['Strict grounding prompt', 'Citation extraction', 'Support-level classification', 'Abstention mechanism'], color: 'cyan' },
          { title: 'Evaluation', items: ['Recall@K, MRR, nDCG', 'Factual correctness', 'Citation accuracy', 'Failure categorization'], color: 'purple' },
        ].map(group => (
          <div key={group.title} className="p-4 rounded-xl bg-gray-900/50 border border-gray-800/50">
            <h4 className={`font-bold text-sm mb-3 ${
              group.color === 'emerald' ? 'text-emerald-400' :
              group.color === 'cyan' ? 'text-cyan-400' : 'text-purple-400'
            }`}>{group.title}</h4>
            <ul className="space-y-1.5">
              {group.items.map(item => (
                <li key={item} className="flex items-center gap-2 text-xs text-gray-400">
                  <span className="w-1 h-1 rounded-full bg-gray-600"></span>{item}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {/* File structure */}
      <div className="p-5 rounded-xl bg-gray-900/50 border border-gray-800/50">
        <h3 className="font-bold text-white mb-3 text-sm">Project Structure</h3>
        <div className="font-mono text-xs space-y-0.5 text-gray-400 overflow-x-auto">
          <p className="text-gray-300 font-semibold">RAG-Pipeline/</p>
          <p className="pl-3">├── <span className="text-emerald-400">src/</span></p>
          <p className="pl-6">├── <span className="text-gray-300">core/</span> <span className="text-gray-600">— config, models</span></p>
          <p className="pl-6">├── <span className="text-gray-300">parsing/</span> <span className="text-gray-600">— PDF parser</span></p>
          <p className="pl-6">├── <span className="text-gray-300">chunking/</span> <span className="text-gray-600">— 4 strategies</span></p>
          <p className="pl-6">├── <span className="text-gray-300">embeddings/</span> <span className="text-gray-600">— local + API</span></p>
          <p className="pl-6">├── <span className="text-gray-300">indexing/</span> <span className="text-gray-600">— ChromaDB + BM25</span></p>
          <p className="pl-6">├── <span className="text-gray-300">retrieval/</span> <span className="text-gray-600">— hybrid + rerank</span></p>
          <p className="pl-6">├── <span className="text-gray-300">generation/</span> <span className="text-gray-600">— LLM + citations</span></p>
          <p className="pl-6">├── <span className="text-gray-300">evaluation/</span> <span className="text-gray-600">— metrics + experiments</span></p>
          <p className="pl-6">└── <span className="text-gray-300">api/</span> <span className="text-gray-600">— FastAPI server</span></p>
          <p className="pl-3">├── <span className="text-cyan-400">tests/</span> <span className="text-gray-600">— unit + integration</span></p>
          <p className="pl-3">├── <span className="text-purple-400">experiments/</span> <span className="text-gray-600">— ablation studies</span></p>
          <p className="pl-3">├── <span className="text-amber-400">benchmarks/</span> <span className="text-gray-600">— evaluation dataset</span></p>
          <p className="pl-3">├── <span className="text-gray-300">docs/</span> <span className="text-gray-600">— architecture, decisions, security</span></p>
          <p className="pl-3">├── <span className="text-gray-300">Dockerfile</span></p>
          <p className="pl-3">└── <span className="text-gray-300">.github/workflows/ci.yml</span></p>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   PIPELINE SECTION
   ═══════════════════════════════════════════════════════════ */
function PipelineSection() {
  const [expanded, setExpanded] = useState<number | null>(0);

  const stages = [
    { num: 1, icon: '📄', title: 'Document Parsing', phase: 'Phase 3',
      desc: 'Robust PDF extraction with structure detection and metadata.',
      points: ['pypdf for reliable text extraction', 'Header/footer detection and removal', 'Metadata extraction (title, author, pages)', 'Content hashing for deduplication', 'Graceful handling of malformed PDFs', 'File validation (size, type, page count)'] },
    { num: 2, icon: '✂️', title: 'Chunking', phase: 'Phase 4',
      desc: 'Four configurable strategies for splitting documents.',
      points: ['Fixed-size: predictable, simple splitting', 'Sentence-based: never splits mid-sentence', 'Recursive: LangChain-style hierarchical splitting', 'Structure-aware: detects headings and sections', 'Configurable size, overlap, min/max constraints', 'Metadata preserved through all strategies'] },
    { num: 3, icon: '🔢', title: 'Embedding', phase: 'Phase 5',
      desc: 'Convert chunks to vectors with swappable providers.',
      points: ['Local: all-MiniLM-L6-v2 (free, 384-dim)', 'OpenAI: text-embedding-3-small (1536-dim)', 'Batch processing for efficiency', 'Model caching (load once)', 'Normalized embeddings for cosine similarity'] },
    { num: 4, icon: '💾', title: 'Indexing', phase: 'Phase 5',
      desc: 'Dual indexing for dense and lexical retrieval.',
      points: ['ChromaDB: persistent vector store with metadata', 'BM25: lexical index for keyword matching', 'Both persist to disk for fast reload', 'Support incremental updates', 'Cosine similarity for dense search'] },
    { num: 5, icon: '🔍', title: 'Retrieval', phase: 'Phase 5-6',
      desc: 'Hybrid retrieval with fusion and reranking.',
      points: ['Dense: top-50 by cosine similarity', 'BM25: top-50 by lexical score', 'RRF fusion: combines both signals', 'Cross-encoder reranking: precision boost', 'Configurable top-K at each stage', 'Full latency tracking per stage'] },
    { num: 6, icon: '🤖', title: 'Generation', phase: 'Phase 7-9',
      desc: 'LLM generation with grounding, citations, and abstention.',
      points: ['Strict grounding instructions in prompt', 'Citation extraction [CITE:chunk_N]', 'Citation validation against retrieved chunks', 'Support-level classification', 'Explicit abstention when evidence insufficient', 'Confidence scoring from multiple signals'] },
    { num: 7, icon: '📊', title: 'Evaluation', phase: 'Phase 6-7',
      desc: 'Comprehensive metrics for retrieval and generation.',
      points: ['Retrieval: Recall@K, MRR, nDCG', 'Generation: correctness, groundedness, citations', 'System: latency, token usage, cost', 'Abstention: correct refusal rate', 'Failure categorization (14 categories)', 'Experiment tracking with config snapshots'] },
  ];

  return (
    <div className="space-y-6">
      <div className="text-center space-y-3">
        <h2 className="text-2xl font-bold text-white">Pipeline Stages</h2>
        <p className="text-sm text-gray-400">Each stage is modular, configurable, and measurable</p>
      </div>

      <div className="space-y-3">
        {stages.map((stage, idx) => (
          <div key={idx} className={`rounded-xl border transition-all ${
            expanded === idx ? 'border-emerald-500/30 bg-gray-900/80' : 'border-gray-800/50 bg-gray-900/30 hover:border-gray-700/50'
          }`}>
            <button onClick={() => setExpanded(expanded === idx ? null : idx)}
              className="w-full flex items-center gap-3 p-4 text-left">
              <div className="w-10 h-10 rounded-lg bg-gray-800 flex items-center justify-center text-lg shrink-0">{stage.icon}</div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono text-gray-600">STAGE {stage.num}</span>
                  <span className="text-[10px] text-gray-700">•</span>
                  <span className="text-[10px] text-gray-600">{stage.phase}</span>
                </div>
                <h3 className="text-sm font-bold text-white">{stage.title}</h3>
                <p className="text-xs text-gray-500 mt-0.5 truncate">{stage.desc}</p>
              </div>
              <svg className={`w-4 h-4 text-gray-500 transition-transform shrink-0 ${expanded === idx ? 'rotate-180' : ''}`}
                fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            {expanded === idx && (
              <div className="px-4 pb-4">
                <div className="grid sm:grid-cols-2 gap-4">
                  <ul className="space-y-1.5">
                    {stage.points.map((p, i) => (
                      <li key={i} className="flex items-start gap-2 text-xs text-gray-400">
                        <span className="text-emerald-400 mt-0.5 shrink-0">•</span>{p}
                      </li>
                    ))}
                  </ul>
                  <div className="p-3 rounded-lg bg-gray-800/30 border border-gray-800/50">
                    <p className="text-xs text-gray-500 italic">{stage.desc}</p>
                    <p className="text-xs text-gray-600 mt-2">
                      Implementation: <code className="text-emerald-400/70">src/{stage.title.toLowerCase().split(' ')[0]}/</code>
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   SOURCE CODE SECTION
   ═══════════════════════════════════════════════════════════ */
function SourceSection() {
  const [activeFile, setActiveFile] = useState(0);
  const [filterPhase, setFilterPhase] = useState<string>('all');

  const phases = useMemo(() => {
    const unique = [...new Set(sourceFiles.map(f => f.phase))];
    return ['all', ...unique.sort()];
  }, []);

  const filteredFiles = useMemo(() => {
    if (filterPhase === 'all') return sourceFiles;
    return sourceFiles.filter(f => f.phase === filterPhase);
  }, [filterPhase]);

  const file = filteredFiles[activeFile] || filteredFiles[0];

  return (
    <div className="space-y-5">
      <div className="text-center space-y-3">
        <h2 className="text-2xl font-bold text-white">Source Code</h2>
        <p className="text-sm text-gray-400">Complete, commented implementation of every component</p>
      </div>

      {/* Phase filter */}
      <div className="flex flex-wrap gap-1.5">
        {phases.map(phase => (
          <button key={phase} onClick={() => { setFilterPhase(phase); setActiveFile(0); }}
            className={`px-2.5 py-1 rounded text-xs font-mono transition-all ${
              filterPhase === phase
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                : 'bg-gray-800/50 text-gray-500 border border-gray-700/50 hover:text-gray-300'
            }`}>
            {phase === 'all' ? 'All Files' : phase}
          </button>
        ))}
      </div>

      {/* File tabs */}
      <div className="flex flex-wrap gap-1.5">
        {filteredFiles.map((f, idx) => (
          <button key={f.path} onClick={() => setActiveFile(idx)}
            className={`px-2.5 py-1 rounded text-xs font-mono transition-all truncate max-w-[200px] ${
              activeFile === idx
                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
                : 'bg-gray-800/30 text-gray-500 border border-gray-800/50 hover:text-gray-300'
            }`}>
            {f.path.split('/').pop()}
          </button>
        ))}
      </div>

      {/* File info */}
      {file && (
        <>
          <div className="flex items-center gap-3 p-3 rounded-lg bg-gray-900/50 border border-gray-800/50">
            <span className="text-lg">{file.path.endsWith('.py') ? '🐍' : file.path.endsWith('.json') ? '📋' : file.path.endsWith('.yml') ? '⚙️' : '🐳'}</span>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-mono text-gray-300 truncate">{file.path}</p>
              <p className="text-xs text-gray-500">{file.description}</p>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded bg-gray-800 text-gray-500 shrink-0">{file.phase}</span>
          </div>

          {/* Code */}
          <CodeBlock code={file.code} language={file.language} filename={file.path} />
        </>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   EXPERIMENTS SECTION
   ═══════════════════════════════════════════════════════════ */
function ExperimentsSection() {
  const experiments = [
    { id: 'A', name: 'Dense Only', desc: 'Semantic retrieval only', config: 'dense_top_k=50, bm25=disabled, rerank=off' },
    { id: 'B', name: 'BM25 Only', desc: 'Lexical retrieval only', config: 'bm25_top_k=50, dense=disabled, rerank=off' },
    { id: 'C', name: 'Hybrid (RRF)', desc: 'Dense + BM25 with RRF fusion', config: 'dense=50, bm25=50, fusion=RRF, rerank=off' },
    { id: 'D', name: 'Hybrid + Rerank', desc: 'Full pipeline with cross-encoder', config: 'dense=50, bm25=50, fusion=RRF, rerank=on, top_k=5' },
    { id: 'E-H', name: 'Chunking Strategies', desc: 'Fixed vs Sentence vs Recursive vs Structure', config: 'chunk_size=512, overlap=64, strategy=varies' },
    { id: 'I-K', name: 'Top-K Sensitivity', desc: 'Final retrieval depth: 3 vs 5 vs 10', config: 'rerank_top_k=3/5/10' },
    { id: 'L', name: 'Ablation: No Rerank', desc: 'Remove reranking from full pipeline', config: 'Same as D but rerank_enabled=false' },
    { id: 'M', name: 'Ablation: No BM25', desc: 'Remove BM25 from hybrid', config: 'Same as C but bm25_top_k=0' },
    { id: 'N', name: 'Ablation: No Dense', desc: 'Remove dense retrieval from hybrid', config: 'Same as C but dense_top_k=0' },
  ];

  const metrics = [
    { name: 'Recall@5', desc: 'Fraction of relevant chunks in top-5', status: 'pending' },
    { name: 'MRR', desc: 'Mean Reciprocal Rank of first relevant result', status: 'pending' },
    { name: 'nDCG@5', desc: 'Normalized Discounted Cumulative Gain', status: 'pending' },
    { name: 'Factual Correctness', desc: 'Answer matches expected answer', status: 'pending' },
    { name: 'Groundedness', desc: 'Answer supported by retrieved evidence', status: 'pending' },
    { name: 'Citation Accuracy', desc: 'Citations map to actual evidence', status: 'pending' },
    { name: 'Hallucination Rate', desc: 'Answers with unsupported claims', status: 'pending' },
    { name: 'Abstention Accuracy', desc: 'Correct refusal on unanswerable questions', status: 'pending' },
    { name: 'Latency p50', desc: 'Median end-to-end query time', status: 'pending' },
    { name: 'Latency p95', desc: '95th percentile query time', status: 'pending' },
  ];

  return (
    <div className="space-y-8">
      <div className="text-center space-y-3">
        <h2 className="text-2xl font-bold text-white">Experiment Framework</h2>
        <p className="text-sm text-gray-400">Systematic comparison of retrieval strategies, chunking, and pipeline components</p>
      </div>

      {/* Experiment table */}
      <div className="rounded-xl border border-gray-800/50 overflow-hidden">
        <div className="p-3 bg-gray-900/50 border-b border-gray-800/50">
          <h3 className="text-sm font-bold text-white">Experiment Configurations</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gray-800/50">
                <th className="text-left px-3 py-2 text-gray-500 font-medium">ID</th>
                <th className="text-left px-3 py-2 text-gray-500 font-medium">Name</th>
                <th className="text-left px-3 py-2 text-gray-500 font-medium hidden sm:table-cell">Description</th>
                <th className="text-left px-3 py-2 text-gray-500 font-medium hidden md:table-cell">Configuration</th>
              </tr>
            </thead>
            <tbody>
              {experiments.map(exp => (
                <tr key={exp.id} className="border-b border-gray-800/30 hover:bg-gray-800/20">
                  <td className="px-3 py-2 font-mono text-emerald-400">{exp.id}</td>
                  <td className="px-3 py-2 text-gray-300 font-medium">{exp.name}</td>
                  <td className="px-3 py-2 text-gray-500 hidden sm:table-cell">{exp.desc}</td>
                  <td className="px-3 py-2 text-gray-600 font-mono hidden md:table-cell">{exp.config}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Metrics */}
      <div className="rounded-xl border border-gray-800/50 overflow-hidden">
        <div className="p-3 bg-gray-900/50 border-b border-gray-800/50">
          <h3 className="text-sm font-bold text-white">Metrics Tracked</h3>
        </div>
        <div className="grid sm:grid-cols-2 gap-px bg-gray-800/30">
          {metrics.map(m => (
            <div key={m.name} className="flex items-center justify-between p-3 bg-gray-900/50">
              <div>
                <p className="text-xs font-medium text-gray-300">{m.name}</p>
                <p className="text-[10px] text-gray-600">{m.desc}</p>
              </div>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                pending
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Status note */}
      <div className="p-4 rounded-xl bg-amber-500/5 border border-amber-500/20">
        <div className="flex items-start gap-3">
          <span className="text-lg">⚠️</span>
          <div>
            <h4 className="text-sm font-bold text-amber-400">Results Pending</h4>
            <p className="text-xs text-gray-400 mt-1">
              The experiment infrastructure is complete. Results will be populated when experiments are executed
              with actual documents and API access. Per the project's core rules, no results are fabricated.
              The framework records configuration, metrics, latency, and per-question results for full reproducibility.
            </p>
          </div>
        </div>
      </div>

      {/* Ablation purpose */}
      <div className="p-4 rounded-xl bg-gray-900/50 border border-gray-800/50">
        <h3 className="text-sm font-bold text-white mb-2">Ablation Study Purpose</h3>
        <p className="text-xs text-gray-400 leading-relaxed">
          Ablation studies answer: <em>"Which architectural components materially improve reliability?"</em>
          By systematically removing one component at a time from the full pipeline, we measure each component's
          individual contribution. This prevents adding technology merely for appearance and ensures every
          component earns its place through measured improvement.
        </p>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   DOCUMENTATION SECTION
   ═══════════════════════════════════════════════════════════ */
function DocsSection() {
  const [activeDoc, setActiveDoc] = useState(0);
  const doc = documentation[activeDoc];

  const categories = useMemo(() => [...new Set(documentation.map(d => d.category))], []);

  return (
    <div className="space-y-5">
      <div className="text-center space-y-3">
        <h2 className="text-2xl font-bold text-white">Documentation</h2>
        <p className="text-sm text-gray-400">Architecture, decisions, security, and reproducibility guides</p>
      </div>

      {/* Doc tabs */}
      <div className="flex flex-wrap gap-1.5">
        {documentation.map((d, idx) => (
          <button key={d.path} onClick={() => setActiveDoc(idx)}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeDoc === idx
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                : 'bg-gray-800/30 text-gray-500 border border-gray-800/50 hover:text-gray-300'
            }`}>
            <span className="mr-1">{d.icon}</span>{d.title}
          </button>
        ))}
      </div>

      {/* Doc content */}
      {doc && (
        <div className="space-y-3">
          <div className="flex items-center gap-3 p-3 rounded-lg bg-gray-900/50 border border-gray-800/50">
            <span className="text-xl">{doc.icon}</span>
            <div>
              <p className="text-sm font-bold text-white">{doc.title}</p>
              <p className="text-xs font-mono text-gray-500">{doc.path}</p>
            </div>
            <span className="ml-auto text-[10px] px-2 py-0.5 rounded bg-gray-800 text-gray-500">{doc.category}</span>
          </div>
          <div className="rounded-xl border border-gray-800/50 overflow-hidden">
            <div className="max-h-[600px] overflow-y-auto p-5 bg-gray-900/30">
              <MarkdownRenderer content={doc.content} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   METRICS SECTION
   ═══════════════════════════════════════════════════════════ */
function MetricsSection() {
  const failureCategories = [
    { name: 'Retrieval Failure', desc: 'Correct evidence exists but was not retrieved', icon: '🔍' },
    { name: 'Chunking Failure', desc: 'Information split in a way that makes it unretrievable', icon: '✂️' },
    { name: 'Ranking Failure', desc: 'Relevant chunks retrieved but ranked too low', icon: '📉' },
    { name: 'Generation Failure', desc: 'Evidence correct but LLM produced wrong answer', icon: '🤖' },
    { name: 'Citation Failure', desc: 'Citations do not point to actual evidence', icon: '📎' },
    { name: 'Hallucination', desc: 'Answer contains information not in evidence', icon: '💭' },
    { name: 'Abstention Failure', desc: 'Should have refused but answered anyway', icon: '⚠️' },
    { name: 'Parsing Failure', desc: 'PDF text extraction produced incorrect text', icon: '📄' },
    { name: 'Contradictory Source', desc: 'Different sources contain contradictory info', icon: '⚡' },
    { name: 'Latency Failure', desc: 'System exceeds acceptable response time', icon: '⏱️' },
    { name: 'Embedding Failure', desc: 'Query and relevant text have low similarity', icon: '🔢' },
    { name: 'Context Window', desc: 'Too much context overwhelms the LLM', icon: '📏' },
    { name: 'OCR Failure', desc: 'Scanned document text not recognized', icon: '👁️' },
    { name: 'Table Understanding', desc: 'Tabular data not correctly interpreted', icon: '📊' },
  ];

  const supportLevels = [
    { level: 'SUPPORTED', color: 'emerald', desc: 'Answer directly and clearly supported by context' },
    { level: 'PARTIALLY_SUPPORTED', color: 'cyan', desc: 'Answer partially supported but requires inference' },
    { level: 'UNSUPPORTED', color: 'red', desc: 'Answer goes beyond what context provides' },
    { level: 'INSUFFICIENT_EVIDENCE', color: 'gray', desc: 'Not enough context for reliable answer → ABSTAIN' },
  ];

  return (
    <div className="space-y-8">
      <div className="text-center space-y-3">
        <h2 className="text-2xl font-bold text-white">Evaluation & Failure Analysis</h2>
        <p className="text-sm text-gray-400">Metrics, failure taxonomy, and support-level classification</p>
      </div>

      {/* Support levels */}
      <div className="rounded-xl border border-gray-800/50 overflow-hidden">
        <div className="p-3 bg-gray-900/50 border-b border-gray-800/50">
          <h3 className="text-sm font-bold text-white">Answer Support Classification</h3>
        </div>
        <div className="grid sm:grid-cols-2 gap-px bg-gray-800/30">
          {supportLevels.map(s => (
            <div key={s.level} className="flex items-center gap-3 p-3 bg-gray-900/50">
              <div className={`w-2 h-8 rounded-full ${
                s.color === 'emerald' ? 'bg-emerald-400' :
                s.color === 'cyan' ? 'bg-cyan-400' :
                s.color === 'red' ? 'bg-red-400' : 'bg-gray-500'
              }`}></div>
              <div>
                <p className={`text-xs font-bold font-mono ${
                  s.color === 'emerald' ? 'text-emerald-400' :
                  s.color === 'cyan' ? 'text-cyan-400' :
                  s.color === 'red' ? 'text-red-400' : 'text-gray-400'
                }`}>{s.level}</p>
                <p className="text-[10px] text-gray-500">{s.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Failure taxonomy */}
      <div className="rounded-xl border border-gray-800/50 overflow-hidden">
        <div className="p-3 bg-gray-900/50 border-b border-gray-800/50">
          <h3 className="text-sm font-bold text-white">Failure Taxonomy (14 Categories)</h3>
          <p className="text-[10px] text-gray-500 mt-0.5">Every failure is categorized, preserved, and analyzed</p>
        </div>
        <div className="grid sm:grid-cols-2 gap-px bg-gray-800/30">
          {failureCategories.map(f => (
            <div key={f.name} className="flex items-start gap-2 p-3 bg-gray-900/50">
              <span className="text-sm shrink-0">{f.icon}</span>
              <div>
                <p className="text-xs font-medium text-gray-300">{f.name}</p>
                <p className="text-[10px] text-gray-500">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Failure analysis pipeline */}
      <div className="p-4 rounded-xl bg-gray-900/50 border border-gray-800/50">
        <h3 className="text-sm font-bold text-white mb-3">Failure Analysis Pipeline</h3>
        <div className="space-y-2">
          {[
            'Record the question and expected answer',
            'Record all retrieved evidence with scores',
            'Record the generated answer',
            'Categorize failure type from taxonomy',
            'Identify probable root cause',
            'Propose specific mitigation',
            'Store in structured JSON for analysis',
          ].map((step, i) => (
            <div key={i} className="flex items-center gap-2 text-xs">
              <span className="w-5 h-5 rounded-full bg-gray-800 flex items-center justify-center text-[10px] text-gray-400 shrink-0">{i + 1}</span>
              <span className="text-gray-400">{step}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Question types */}
      <div className="p-4 rounded-xl bg-gray-900/50 border border-gray-800/50">
        <h3 className="text-sm font-bold text-white mb-3">Benchmark Question Types</h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
          {[
            'Direct Lookup', 'Multi-hop', 'Numerical', 'Definition',
            'Comparison', 'Summarization', 'Cross-section', 'Cross-document',
            'Ambiguous', 'Unanswerable', 'Adversarial', 'Table-based',
          ].map(type => (
            <div key={type} className="px-2 py-1.5 rounded-md bg-gray-800/30 border border-gray-800/50 text-xs text-gray-400 text-center">
              {type}
            </div>
          ))}
        </div>
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
          <div className="flex gap-1">
            <div className="w-2.5 h-2.5 rounded-full bg-red-500/70"></div>
            <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/70"></div>
            <div className="w-2.5 h-2.5 rounded-full bg-green-500/70"></div>
          </div>
          <span className="text-[10px] text-gray-400 font-mono truncate max-w-[200px]">{filename}</span>
        </div>
        <button onClick={handleCopy}
          className="flex items-center gap-1 px-2 py-0.5 text-[10px] rounded bg-gray-700 hover:bg-gray-600 text-gray-300 transition-all">
          {copied ? '✓ Copied' : 'Copy'}
        </button>
      </div>
      <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
        <SyntaxHighlighter language={language === 'json' ? 'json' : language === 'yaml' ? 'yaml' : language === 'dockerfile' ? 'docker' : 'python'}
          style={oneDark}
          customStyle={{ margin: 0, padding: '1rem', fontSize: '0.7rem', lineHeight: '1.5', background: '#1a1a2e' }}
          wrapLines={true}>
          {code}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}

function MarkdownRenderer({ content }: { content: string }) {
  // Simple markdown renderer for documentation content
  const lines = content.split('\n');
  const elements: JSX.Element[] = [];
  let inCodeBlock = false;
  let codeContent = '';
  let codeLang = '';

  lines.forEach((line, i) => {
    if (line.startsWith('```')) {
      if (inCodeBlock) {
        elements.push(
          <pre key={`code-${i}`} className="my-2 p-3 rounded-lg bg-gray-800/50 text-xs font-mono text-gray-300 overflow-x-auto">
            <code>{codeContent.trim()}</code>
          </pre>
        );
        codeContent = '';
        inCodeBlock = false;
      } else {
        inCodeBlock = true;
        codeLang = line.slice(3).trim();
      }
      return;
    }

    if (inCodeBlock) {
      codeContent += line + '\n';
      return;
    }

    if (line.startsWith('# ')) {
      elements.push(<h1 key={i} className="text-xl font-bold text-white mt-4 mb-2">{line.slice(2)}</h1>);
    } else if (line.startsWith('## ')) {
      elements.push(<h2 key={i} className="text-lg font-bold text-white mt-4 mb-2">{line.slice(3)}</h2>);
    } else if (line.startsWith('### ')) {
      elements.push(<h3 key={i} className="text-sm font-bold text-gray-200 mt-3 mb-1.5">{line.slice(4)}</h3>);
    } else if (line.startsWith('#### ')) {
      elements.push(<h4 key={i} className="text-xs font-bold text-gray-300 mt-2 mb-1">{line.slice(5)}</h4>);
    } else if (line.startsWith('- [x] ') || line.startsWith('- [ ] ')) {
      const checked = line.startsWith('- [x]');
      elements.push(
        <div key={i} className="flex items-center gap-2 text-xs text-gray-400 py-0.5">
          <span className={checked ? 'text-emerald-400' : 'text-gray-600'}>{checked ? '✓' : '○'}</span>
          <span className={checked ? 'text-gray-300' : ''}>{line.slice(6)}</span>
        </div>
      );
    } else if (line.startsWith('- ')) {
      elements.push(
        <div key={i} className="flex items-start gap-2 text-xs text-gray-400 py-0.5">
          <span className="text-gray-600 mt-0.5">•</span>{line.slice(2)}
        </div>
      );
    } else if (line.startsWith('| ') && line.includes('|')) {
      // Table row
      const cells = line.split('|').filter(c => c.trim()).map(c => c.trim());
      if (cells.every(c => c.match(/^[-:]+$/))) return; // separator row
      elements.push(
        <div key={i} className="flex gap-3 text-xs py-0.5 border-b border-gray-800/30">
          {cells.map((cell, j) => (
            <span key={j} className={`${j === 0 ? 'text-gray-300 font-medium min-w-[100px]' : 'text-gray-500'}`}>{cell}</span>
          ))}
        </div>
      );
    } else if (line.startsWith('> ')) {
      elements.push(
        <div key={i} className="pl-3 border-l-2 border-emerald-500/30 text-xs text-gray-400 italic my-1">
          {line.slice(2)}
        </div>
      );
    } else if (line.trim() === '') {
      elements.push(<div key={i} className="h-2"></div>);
    } else if (line.startsWith('---')) {
      elements.push(<hr key={i} className="border-gray-800/50 my-3" />);
    } else {
      // Regular paragraph - handle inline formatting
      const formatted = line
        .replace(/\*\*(.+?)\*\*/g, '<strong class="text-gray-200">$1</strong>')
        .replace(/`(.+?)`/g, '<code class="px-1 py-0.5 rounded bg-gray-800 text-emerald-400/80 text-[11px]">$1</code>')
        .replace(/\*(.+?)\*/g, '<em class="text-gray-300">$1</em>');
      elements.push(<p key={i} className="text-xs text-gray-400 leading-relaxed" dangerouslySetInnerHTML={{ __html: formatted }} />);
    }
  });

  return <div className="space-y-0">{elements}</div>;
}
