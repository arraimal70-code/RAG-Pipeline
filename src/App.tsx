import { useState } from 'react';
import CodeBlock from './components/CodeBlock';
import { codeFiles } from './data/codeFiles';

type Section = 'overview' | 'architecture' | 'pipeline' | 'code' | 'decisions' | 'readme';

const navItems: { id: Section; label: string; icon: string }[] = [
  { id: 'overview', label: 'Overview', icon: '🏠' },
  { id: 'architecture', label: 'Architecture', icon: '🏗️' },
  { id: 'pipeline', label: 'Pipeline', icon: '⚡' },
  { id: 'code', label: 'Source Code', icon: '💻' },
  { id: 'decisions', label: 'Decisions', icon: '🧠' },
  { id: 'readme', label: 'README', icon: '📖' },
];

export default function App() {
  const [activeSection, setActiveSection] = useState<Section>('overview');
  const [activeFile, setActiveFile] = useState(0);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const renderContent = () => {
    switch (activeSection) {
      case 'overview':
        return <OverviewSection />;
      case 'architecture':
        return <ArchitectureSection />;
      case 'pipeline':
        return <PipelineSection />;
      case 'code':
        return <CodeSection activeFile={activeFile} setActiveFile={setActiveFile} />;
      case 'decisions':
        return <DecisionsSection />;
      case 'readme':
        return <ReadmeSection />;
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col">
      {/* Top Navigation */}
      <header className="sticky top-0 z-50 bg-gray-950/80 backdrop-blur-xl border-b border-gray-800/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-emerald-400 to-cyan-500 flex items-center justify-center text-lg font-bold text-gray-900">
                R
              </div>
              <div>
                <h1 className="text-lg font-bold text-white leading-tight">RAG Pipeline</h1>
                <p className="text-xs text-gray-500 leading-tight">PDF Q&A with LangChain</p>
              </div>
            </div>

            {/* Desktop nav */}
            <nav className="hidden md:flex items-center gap-1">
              {navItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setActiveSection(item.id)}
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                    activeSection === item.id
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
                  }`}
                >
                  <span className="mr-1.5">{item.icon}</span>
                  {item.label}
                </button>
              ))}
            </nav>

            {/* Mobile menu button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800"
            >
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                {mobileMenuOpen ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                )}
              </svg>
            </button>
          </div>
        </div>

        {/* Mobile nav */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-gray-800/50 bg-gray-950/95 backdrop-blur-xl">
            <div className="px-4 py-3 space-y-1">
              {navItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => { setActiveSection(item.id); setMobileMenuOpen(false); }}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                    activeSection === item.id
                      ? 'bg-emerald-500/10 text-emerald-400'
                      : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
                  }`}
                >
                  <span className="mr-2">{item.icon}</span>
                  {item.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </header>

      {/* Main content */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
        {renderContent()}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800/50 py-6 text-center text-sm text-gray-600">
        <p>Built with LangChain • Chroma • OpenAI • An educational RAG implementation</p>
      </footer>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────
   Section Components
   ───────────────────────────────────────────────────────── */

function OverviewSection() {
  return (
    <div className="space-y-12">
      {/* Hero */}
      <div className="text-center py-12 space-y-6">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          Educational RAG Pipeline
        </div>
        <h2 className="text-4xl sm:text-5xl font-bold bg-gradient-to-r from-white via-gray-200 to-gray-400 bg-clip-text text-transparent">
          Ask Questions About<br />Your PDF Documents
        </h2>
        <p className="max-w-2xl mx-auto text-lg text-gray-400 leading-relaxed">
          A complete, self-contained Retrieval-Augmented Generation system. Drop PDFs into a folder,
          ask natural-language questions, get accurate answers with source citations — all running locally.
        </p>
        <div className="flex flex-wrap justify-center gap-4 pt-4">
          <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-800/50 border border-gray-700/50">
            <span className="text-lg">🆓</span>
            <span className="text-sm text-gray-300">Free local embeddings</span>
          </div>
          <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-800/50 border border-gray-700/50">
            <span className="text-lg">💾</span>
            <span className="text-sm text-gray-300">Persistent vector store</span>
          </div>
          <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-800/50 border border-gray-700/50">
            <span className="text-lg">📎</span>
            <span className="text-sm text-gray-300">Source citations</span>
          </div>
          <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-800/50 border border-gray-700/50">
            <span className="text-lg">⚙️</span>
            <span className="text-sm text-gray-300">Fully configurable</span>
          </div>
        </div>
      </div>

      {/* Quick start */}
      <div className="grid md:grid-cols-2 gap-8">
        <div className="space-y-4">
          <h3 className="text-2xl font-bold text-white">What is RAG?</h3>
          <p className="text-gray-400 leading-relaxed">
            <strong className="text-gray-200">Retrieval-Augmented Generation</strong> combines the power of
            large language models with your own documents. Instead of relying solely on training data,
            the LLM receives relevant context retrieved from your files — producing answers that are
            grounded in your actual documents.
          </p>
          <p className="text-gray-400 leading-relaxed">
            This project implements the two core stages: <strong className="text-emerald-400">ingestion</strong> (loading,
            chunking, embedding, storing) and <strong className="text-cyan-400">querying</strong> (retrieving, prompting,
            generating, citing). Each stage is explained with inline comments and architectural decisions.
          </p>
        </div>
        <div className="space-y-4">
          <h3 className="text-2xl font-bold text-white">Tech Stack</h3>
          <div className="space-y-3">
            {[
              { name: 'LangChain', desc: 'Orchestration framework for LLM apps', color: 'from-green-400 to-emerald-500' },
              { name: 'ChromaDB', desc: 'Persistent local vector database', color: 'from-blue-400 to-indigo-500' },
              { name: 'OpenAI GPT-4o-mini', desc: 'Fast, cheap answer generation', color: 'from-purple-400 to-pink-500' },
              { name: 'sentence-transformers', desc: 'Free local embedding model', color: 'from-orange-400 to-red-500' },
              { name: 'PyPDF', desc: 'PDF text extraction', color: 'from-cyan-400 to-blue-500' },
            ].map((tech) => (
              <div key={tech.name} className="flex items-start gap-3 p-3 rounded-lg bg-gray-900/50 border border-gray-800/50">
                <div className={`w-2 h-2 mt-2 rounded-full bg-gradient-to-r ${tech.color} shrink-0`}></div>
                <div>
                  <p className="text-sm font-semibold text-gray-200">{tech.name}</p>
                  <p className="text-xs text-gray-500">{tech.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Cost callout */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-emerald-500/5 to-cyan-500/5 border border-emerald-500/20">
        <div className="flex items-start gap-4">
          <span className="text-3xl">💰</span>
          <div>
            <h4 className="font-bold text-white text-lg">Cost: ~$0.10 for 100 queries</h4>
            <p className="text-gray-400 text-sm mt-1">
              Local embeddings are free. GPT-4o-mini costs ~$0.001 per query. The entire pipeline
              runs at near-zero cost during development.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function ArchitectureSection() {
  return (
    <div className="space-y-12">
      <div className="text-center space-y-4">
        <h2 className="text-3xl font-bold text-white">System Architecture</h2>
        <p className="text-gray-400 max-w-2xl mx-auto">
          Two-stage pipeline: ingest once, query many times. The vector store persists between runs.
        </p>
      </div>

      {/* Architecture Diagram */}
      <div className="p-8 rounded-2xl bg-gray-900/50 border border-gray-800/50 overflow-x-auto">
        <div className="min-w-[700px]">
          {/* Stage 1: Ingestion */}
          <div className="mb-8">
            <div className="flex items-center gap-2 mb-4">
              <span className="px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-sm font-medium">
                Stage 1: Ingestion
              </span>
              <span className="text-gray-600 text-sm">— Run once per document set</span>
            </div>
            <div className="flex items-center gap-3 flex-wrap">
              <ArchBox icon="📄" title="PDF Files" subtitle="documents/" color="emerald" />
              <ArchArrow />
              <ArchBox icon="✂️" title="Chunking" subtitle="RecursiveTextSplitter" color="emerald" />
              <ArchArrow />
              <ArchBox icon="🔢" title="Embedding" subtitle="all-MiniLM-L6-v2" color="emerald" />
              <ArchArrow />
              <ArchBox icon="💾" title="Chroma DB" subtitle="chroma_db/" color="emerald" />
            </div>
          </div>

          {/* Divider */}
          <div className="flex items-center gap-4 my-8">
            <div className="flex-1 h-px bg-gradient-to-r from-transparent via-gray-700 to-transparent"></div>
            <span className="text-gray-500 text-sm px-3">persistent storage</span>
            <div className="flex-1 h-px bg-gradient-to-r from-transparent via-gray-700 to-transparent"></div>
          </div>

          {/* Stage 2: Querying */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <span className="px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-sm font-medium">
                Stage 2: Querying
              </span>
              <span className="text-gray-600 text-sm">— Run for each question</span>
            </div>
            <div className="flex items-center gap-3 flex-wrap">
              <ArchBox icon="💾" title="Chroma DB" subtitle="(loaded)" color="cyan" />
              <ArchArrow />
              <ArchBox icon="🔍" title="Retrieve" subtitle="MMR, top-k=4" color="cyan" />
              <ArchArrow />
              <ArchBox icon="📝" title="Prompt" subtitle="context + question" color="cyan" />
              <ArchArrow />
              <ArchBox icon="🤖" title="LLM" subtitle="gpt-4o-mini" color="cyan" />
              <ArchArrow />
              <ArchBox icon="💬" title="Answer" subtitle="+ sources" color="cyan" />
            </div>
          </div>
        </div>
      </div>

      {/* Data flow explanation */}
      <div className="grid md:grid-cols-3 gap-6">
        <div className="p-6 rounded-xl bg-gray-900/50 border border-gray-800/50 space-y-3">
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center text-xl">📄</div>
          <h4 className="font-bold text-white">Documents → Vectors</h4>
          <p className="text-sm text-gray-400">
            Each PDF page is loaded, split into ~800-char chunks with 150-char overlap, then converted
            to 384-dimensional vectors via sentence-transformers.
          </p>
        </div>
        <div className="p-6 rounded-xl bg-gray-900/50 border border-gray-800/50 space-y-3">
          <div className="w-10 h-10 rounded-lg bg-cyan-500/10 flex items-center justify-center text-xl">🔍</div>
          <h4 className="font-bold text-white">Query → Context</h4>
          <p className="text-sm text-gray-400">
            Your question is embedded with the same model, then MMR retrieval finds the 4 most relevant
            and diverse chunks from the vector store.
          </p>
        </div>
        <div className="p-6 rounded-xl bg-gray-900/50 border border-gray-800/50 space-y-3">
          <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center text-xl">🤖</div>
          <h4 className="font-bold text-white">Context → Answer</h4>
          <p className="text-sm text-gray-400">
            The retrieved chunks are stitched into a prompt template with your question, sent to GPT-4o-mini,
            and the answer is returned with source citations.
          </p>
        </div>
      </div>

      {/* File structure */}
      <div className="p-6 rounded-2xl bg-gray-900/50 border border-gray-800/50">
        <h3 className="text-xl font-bold text-white mb-4">Project Structure</h3>
        <div className="font-mono text-sm space-y-1 text-gray-400">
          <p className="text-gray-300 font-semibold">rag-pipeline/</p>
          <p className="pl-4">├── <span className="text-emerald-400">documents/</span>          <span className="text-gray-600"># Your PDF files go here</span></p>
          <p className="pl-4">├── <span className="text-yellow-400">chroma_db/</span>          <span className="text-gray-600"># Persisted vector store (auto-created)</span></p>
          <p className="pl-4">├── <span className="text-cyan-400">ingest.py</span>           <span className="text-gray-600"># Stage 1: load, chunk, embed, store</span></p>
          <p className="pl-4">├── <span className="text-cyan-400">query.py</span>            <span className="text-gray-600"># Stage 2: retrieve, generate, cite</span></p>
          <p className="pl-4">├── <span className="text-purple-400">config.py</span>           <span className="text-gray-600"># All configurable constants</span></p>
          <p className="pl-4">├── <span className="text-gray-400">requirements.txt</span>    <span className="text-gray-600"># Python dependencies</span></p>
          <p className="pl-4">├── <span className="text-gray-400">.env.example</span>        <span className="text-gray-600"># Template for API keys</span></p>
          <p className="pl-4">├── <span className="text-gray-400">.env</span>                <span className="text-gray-600"># Your actual keys (gitignored!)</span></p>
          <p className="pl-4">├── <span className="text-gray-400">DECISIONS.md</span>        <span className="text-gray-600"># Architectural decisions explained</span></p>
          <p className="pl-4">└── <span className="text-gray-400">README.md</span>           <span className="text-gray-600"># Setup and usage guide</span></p>
        </div>
      </div>
    </div>
  );
}

function ArchBox({ icon, title, subtitle, color }: { icon: string; title: string; subtitle: string; color: string }) {
  const colorClasses: Record<string, string> = {
    emerald: 'border-emerald-500/30 bg-emerald-500/5',
    cyan: 'border-cyan-500/30 bg-cyan-500/5',
  };
  return (
    <div className={`flex flex-col items-center gap-1 px-4 py-3 rounded-xl border ${colorClasses[color]} min-w-[120px]`}>
      <span className="text-2xl">{icon}</span>
      <span className="text-sm font-semibold text-white">{title}</span>
      <span className="text-xs text-gray-500">{subtitle}</span>
    </div>
  );
}

function ArchArrow() {
  return (
    <svg className="w-8 h-4 text-gray-600 shrink-0" viewBox="0 0 32 16" fill="none">
      <path d="M0 8h28m0 0l-6-6m6 6l-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function PipelineSection() {
  const [expandedStage, setExpandedStage] = useState<number | null>(0);

  const stages = [
    {
      number: 1,
      title: 'Load PDFs',
      icon: '📄',
      color: 'emerald',
      description: 'PyPDFDirectoryLoader walks the documents/ folder and extracts text from every PDF page.',
      details: [
        'Each page becomes a separate Document object',
        'Metadata preserved: source file path + page number',
        'This metadata flows through the entire pipeline for citations',
        'Handles multi-page PDFs automatically',
      ],
      code: `from langchain_community.document_loaders import PyPDFDirectoryLoader

loader = PyPDFDirectoryLoader("documents/")
documents = loader.load()
# → [Document(page_content="...", metadata={"source": "file.pdf", "page": 0}), ...]`
    },
    {
      number: 2,
      title: 'Chunk Documents',
      icon: '✂️',
      color: 'green',
      description: 'RecursiveCharacterTextSplitter breaks pages into overlapping ~800-char chunks.',
      details: [
        'Splits at natural boundaries: paragraphs → sentences → words',
        'Overlap (150 chars) prevents losing info at chunk boundaries',
        'Chunk size 800 balances context vs. retrieval precision',
        'Metadata from parent page is inherited by each chunk',
      ],
      code: `from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=150,
    separators=["\\n\\n", "\\n", ". ", " ", ""],
)
chunks = splitter.split_documents(documents)`
    },
    {
      number: 3,
      title: 'Embed & Store',
      icon: '🔢',
      color: 'cyan',
      description: 'Each chunk is converted to a vector and stored in persistent Chroma database.',
      details: [
        'all-MiniLM-L6-v2 produces 384-dimensional vectors',
        'Chroma persists to disk — no re-embedding on restart',
        'Vectors + metadata + text all stored together',
        'Swappable to OpenAI embeddings via config change',
      ],
      code: `from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
db = Chroma.from_documents(chunks, embeddings, persist_directory="chroma_db/")
db.persist()`
    },
    {
      number: 4,
      title: 'Retrieve',
      icon: '🔍',
      color: 'blue',
      description: 'MMR retrieval finds the top-4 most relevant AND diverse chunks for the query.',
      details: [
        'Query is embedded with the SAME model used for documents',
        'MMR balances relevance with diversity (no near-duplicates)',
        'fetch_k=20 considers more candidates before selecting top-4',
        'Returns chunks + their metadata (source, page)',
      ],
      code: `retriever = db.as_retriever(
    search_type="mmr",
    search_kwargs={"k": 4, "fetch_k": 20},
)
docs = retriever.invoke("What is the main topic of chapter 3?")`
    },
    {
      number: 5,
      title: 'Generate Answer',
      icon: '🤖',
      color: 'purple',
      description: 'Retrieved chunks are stitched into a prompt and sent to the LLM for a grounded answer.',
      details: [
        'Prompt template instructs LLM to use ONLY the provided context',
        'Temperature=0 for deterministic, factual answers',
        'Source metadata formatted for citation display',
        'LLM says "I don\'t know" if context is insufficient',
      ],
      code: `from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_template("""
Answer using only this context:
{context}

Question: {question}
""")
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
chain = {"context": retriever, "question": RunnablePassthrough()} | prompt | llm`
    },
  ];

  return (
    <div className="space-y-8">
      <div className="text-center space-y-4">
        <h2 className="text-3xl font-bold text-white">Pipeline Stages</h2>
        <p className="text-gray-400 max-w-2xl mx-auto">
          Click each stage to explore what happens and see example code.
        </p>
      </div>

      <div className="space-y-4">
        {stages.map((stage, idx) => (
          <div
            key={idx}
            className={`rounded-xl border transition-all ${
              expandedStage === idx
                ? 'border-emerald-500/30 bg-gray-900/80'
                : 'border-gray-800/50 bg-gray-900/30 hover:border-gray-700/50'
            }`}
          >
            <button
              onClick={() => setExpandedStage(expandedStage === idx ? null : idx)}
              className="w-full flex items-center gap-4 p-5 text-left"
            >
              <div className="w-12 h-12 rounded-xl bg-gray-800 flex items-center justify-center text-2xl shrink-0">
                {stage.icon}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-gray-600">STAGE {stage.number}</span>
                </div>
                <h3 className="text-lg font-bold text-white">{stage.title}</h3>
                <p className="text-sm text-gray-400 mt-0.5">{stage.description}</p>
              </div>
              <svg
                className={`w-5 h-5 text-gray-500 transition-transform ${expandedStage === idx ? 'rotate-180' : ''}`}
                fill="none" viewBox="0 0 24 24" stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {expandedStage === idx && (
              <div className="px-5 pb-5 space-y-4">
                <div className="grid sm:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <h4 className="text-sm font-semibold text-gray-300">Key Points:</h4>
                    <ul className="space-y-1.5">
                      {stage.details.map((detail, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-gray-400">
                          <span className="text-emerald-400 mt-0.5">•</span>
                          {detail}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-gray-300 mb-2">Example Code:</h4>
                    <div className="rounded-lg overflow-hidden border border-gray-700/50">
                      <pre className="p-3 bg-gray-800/50 text-xs text-gray-300 font-mono overflow-x-auto whitespace-pre">
                        {stage.code}
                      </pre>
                    </div>
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

function CodeSection({ activeFile, setActiveFile }: { activeFile: number; setActiveFile: (n: number) => void }) {
  const file = codeFiles[activeFile];

  return (
    <div className="space-y-6">
      <div className="text-center space-y-4">
        <h2 className="text-3xl font-bold text-white">Source Code</h2>
        <p className="text-gray-400 max-w-2xl mx-auto">
          Complete, commented source code for every file in the project. Click to copy.
        </p>
      </div>

      {/* File tabs */}
      <div className="flex flex-wrap gap-2">
        {codeFiles.map((f, idx) => (
          <button
            key={idx}
            onClick={() => setActiveFile(idx)}
            className={`px-4 py-2 rounded-lg text-sm font-mono transition-all ${
              activeFile === idx
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                : 'bg-gray-800/50 text-gray-400 border border-gray-700/50 hover:text-white hover:border-gray-600'
            }`}
          >
            {f.name}
          </button>
        ))}
      </div>

      {/* File description */}
      <div className="flex items-center gap-3 p-4 rounded-xl bg-gray-900/50 border border-gray-800/50">
        <span className="text-2xl">
          {file.name.endsWith('.py') ? '🐍' : file.name.endsWith('.md') ? '📝' : file.name.endsWith('.txt') ? '📋' : '🔧'}
        </span>
        <p className="text-gray-300">{file.description}</p>
      </div>

      {/* Code display */}
      <CodeBlock code={file.code} language={file.language} filename={file.name} />
    </div>
  );
}

function DecisionsSection() {
  const decisionsFile = codeFiles.find(f => f.name === 'DECISIONS.md');

  return (
    <div className="space-y-6">
      <div className="text-center space-y-4">
        <h2 className="text-3xl font-bold text-white">Architectural Decisions</h2>
        <p className="text-gray-400 max-w-2xl mx-auto">
          Why we made each choice — the learning companion to the code.
        </p>
      </div>

      {/* Decision cards */}
      <div className="grid md:grid-cols-2 gap-6">
        <DecisionCard
          title="RecursiveCharacterTextSplitter"
          emoji="✂️"
          decision="Splits at natural boundaries (paragraphs → sentences → words)"
          alternatives="CharacterTextSplitter (too simple), TokenTextSplitter (slower, needs tiktoken)"
        />
        <DecisionCard
          title="Chunk Size: 800 chars"
          emoji="📏"
          decision="Sweet spot: ~2-3 paragraphs, enough context without too much noise"
          alternatives="< 300: loses context | > 1500: too noisy for retrieval"
        />
        <DecisionCard
          title="ChromaDB over FAISS"
          emoji="💾"
          decision="Built-in persistence, metadata filtering, simpler API"
          alternatives="FAISS: faster but no persistence, no metadata filtering"
        />
        <DecisionCard
          title="Local Embeddings First"
          emoji="🆓"
          decision="Zero cost during development, no API key needed"
          alternatives="OpenAI text-embedding-3-small: better quality, ~$0.02/1M tokens"
        />
        <DecisionCard
          title="MMR Retrieval"
          emoji="🔍"
          decision="Balances relevance with diversity — no near-duplicate results"
          alternatives="Plain similarity: may return 4 nearly-identical chunks"
        />
        <DecisionCard
          title="Temperature = 0.0"
          emoji="🌡️"
          decision="Deterministic answers for factual Q&A — no creative interpretation"
          alternatives="0.7: creative/varied (good for brainstorming, bad for facts)"
        />
        <DecisionCard
          title="GPT-4o-mini"
          emoji="💰"
          decision="1/16th the cost of GPT-4o, fast, good enough for RAG tasks"
          alternatives="GPT-4o: better reasoning, 16x more expensive"
        />
        <DecisionCard
          title="Separate ingest.py / query.py"
          emoji="📦"
          decision="Ingestion is expensive (done once); querying is cheap (done many times)"
          alternatives="Single file: simpler but can't re-query without re-embedding"
        />
      </div>

      {/* Full DECISIONS.md */}
      <div className="pt-4">
        <h3 className="text-xl font-bold text-white mb-4">Full DECISIONS.md</h3>
        {decisionsFile && (
          <CodeBlock code={decisionsFile.code} language="markdown" filename="DECISIONS.md" />
        )}
      </div>
    </div>
  );
}

function DecisionCard({ title, emoji, decision, alternatives }: {
  title: string; emoji: string; decision: string; alternatives: string;
}) {
  return (
    <div className="p-5 rounded-xl bg-gray-900/50 border border-gray-800/50 space-y-3">
      <div className="flex items-center gap-3">
        <span className="text-2xl">{emoji}</span>
        <h4 className="font-bold text-white">{title}</h4>
      </div>
      <div className="space-y-2">
        <div className="flex items-start gap-2">
          <span className="text-emerald-400 text-xs mt-1 font-bold">✓</span>
          <p className="text-sm text-gray-300">{decision}</p>
        </div>
        <div className="flex items-start gap-2">
          <span className="text-gray-600 text-xs mt-1 font-bold">⚡</span>
          <p className="text-sm text-gray-500">{alternatives}</p>
        </div>
      </div>
    </div>
  );
}

function ReadmeSection() {
  const readmeFile = codeFiles.find(f => f.name === 'README.md');

  return (
    <div className="space-y-6">
      <div className="text-center space-y-4">
        <h2 className="text-3xl font-bold text-white">README</h2>
        <p className="text-gray-400 max-w-2xl mx-auto">
          Everything you need to get started — install, configure, run.
        </p>
      </div>

      {/* Quick start steps */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <StepCard step={1} title="Install" command="pip install -r requirements.txt" />
        <StepCard step={2} title="Configure" command="cp .env.example .env" />
        <StepCard step={3} title="Add PDFs" command="cp *.pdf documents/" />
        <StepCard step={4} title="Ingest" command="python ingest.py" />
        <StepCard step={5} title="Query" command="python query.py" />
        <StepCard step={6} title="Ask!" command='❓ What is...' highlight />
      </div>

      {/* Full README */}
      <div className="pt-4">
        <h3 className="text-xl font-bold text-white mb-4">Full README.md</h3>
        {readmeFile && (
          <CodeBlock code={readmeFile.code} language="markdown" filename="README.md" />
        )}
      </div>
    </div>
  );
}

function StepCard({ step, title, command, highlight }: {
  step: number; title: string; command: string; highlight?: boolean;
}) {
  return (
    <div className={`p-4 rounded-xl border transition-all ${
      highlight
        ? 'bg-emerald-500/5 border-emerald-500/30'
        : 'bg-gray-900/50 border-gray-800/50 hover:border-gray-700/50'
    }`}>
      <div className="flex items-center gap-3 mb-2">
        <span className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
          highlight ? 'bg-emerald-500 text-gray-900' : 'bg-gray-800 text-gray-400'
        }`}>
          {step}
        </span>
        <span className="font-semibold text-white text-sm">{title}</span>
      </div>
      <code className={`text-xs px-2 py-1 rounded font-mono ${
        highlight ? 'bg-emerald-500/10 text-emerald-300' : 'bg-gray-800 text-gray-400'
      }`}>
        $ {command}
      </code>
    </div>
  );
}
