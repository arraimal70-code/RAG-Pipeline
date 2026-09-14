# Push Code to GitHub - Step-by-Step Guide

## Prerequisites
- Git installed on your system
- GitHub account
- Repository created on GitHub (e.g., https://github.com/arraimal70-code/RAG-Pipeline)

## Step 1: Initialize Git Repository

```bash
# Navigate to project directory
cd /path/to/rag-pipeline

# Initialize git
git init
```

## Step 2: Add Remote Repository

```bash
# Add your GitHub repository as remote
git remote add origin https://github.com/arraimal70-code/RAG-Pipeline.git

# Verify remote
git remote -v
```

## Step 3: Stage All Files

```bash
# Add all files to staging
git add .

# Check status
git status
```

## Step 4: Commit Changes

```bash
# Create initial commit
git commit -m "Initial commit: Evidence-Aware Adaptive RAG Pipeline

- Core pipeline with modular architecture
- Multiple chunking strategies (fixed, sentence, recursive, structure-aware)
- Hybrid retrieval (dense + BM25 + RRF fusion)
- Cross-encoder reranking
- Adaptive query analysis and retrieval
- Evidence sufficiency assessment
- Contradiction detection
- Citation validation
- Comprehensive evaluation framework
- 19 experiments + ablation studies
- 15-category failure taxonomy
- Full test suite
- Docker + CI/CD support
- Complete documentation"
```

## Step 5: Push to GitHub

```bash
# Push to main branch
git branch -M main
git push -u origin main
```

## Alternative: If Repository Already Exists

If you already have a git repository set up:

```bash
# Check current status
git status

# Add all changes
git add .

# Commit
git commit -m "Add complete RAG pipeline implementation"

# Push
git push origin main
```

## Verify Push

1. Go to https://github.com/arraimal70-code/RAG-Pipeline
2. Refresh the page
3. Verify all files are present:
   - src/ directory with all Python modules
   - tests/ directory
   - experiments/ directory
   - benchmarks/ directory
   - docs/ directory
   - README.md
   - requirements.txt
   - Dockerfile
   - .github/workflows/ci.yml

## Troubleshooting

### Authentication Issues
If you get authentication errors:
```bash
# Use GitHub CLI (recommended)
gh auth login

# Or use personal access token
git remote set-url origin https://YOUR_TOKEN@github.com/arraimal70-code/RAG-Pipeline.git
```

### Large Files
If you have large files (>100MB):
```bash
# Install Git LFS
git lfs install

# Track large files
git lfs track "*.pdf"
git lfs track "*.pkl"

# Add .gitattributes
git add .gitattributes
git commit -m "Add Git LFS tracking"
git push
```

### Branch Issues
```bash
# Check current branch
git branch

# Switch to main
git checkout main

# If main doesn't exist
git branch -M main
git push -u origin main
```

## Post-Push Verification

After pushing, verify:
- [ ] All Python files are present
- [ ] Tests can be discovered
- [ ] README renders correctly
- [ ] Documentation is accessible
- [ ] CI/CD workflow is recognized

## Next Steps

After successful push:
1. Monitor GitHub Actions for CI/CD status
2. Set up branch protection rules
3. Configure repository settings
4. Add collaborators if needed
5. Create release tags for versions

## Repository Structure

Your pushed repository should contain:

```
RAG-Pipeline/
├── src/                    # Python source code
│   ├── core/              # Configuration and models
│   ├── parsing/           # PDF parsing
│   ├── chunking/          # Chunking strategies
│   ├── embeddings/        # Embedding generation
│   ├── indexing/          # Vector and BM25 indexes
│   ├── retrieval/         # Hybrid retrieval
│   ├── generation/        # LLM generation
│   ├── evaluation/        # Evaluation framework
│   ├── adaptive/          # Query analysis
│   ├── evidence/          # Evidence sufficiency
│   ├── citations/         # Citation validation
│   └── api/               # FastAPI server
├── tests/                 # Unit and integration tests
├── experiments/           # Experiment runner
├── benchmarks/            # Evaluation datasets
├── docs/                  # Documentation
├── .github/workflows/     # CI/CD
├── README.md
├── requirements.txt
├── Dockerfile
└── .gitignore
```

## Support

If you encounter issues:
1. Check GitHub's documentation: https://docs.github.com/
2. Verify git configuration: `git config --list`
3. Check network connectivity
4. Review error messages carefully
