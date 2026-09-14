# Security Considerations

## Threat Model

The RAG pipeline processes untrusted input at multiple stages:
1. Uploaded documents — may contain malicious content
2. Extracted text — may contain prompt injection
3. User queries — may attempt system manipulation
4. LLM responses — may be manipulated by injected instructions

## Protections

### Input Validation
- File type: Only .pdf accepted
- File size: Max 50MB
- Page count: Max 500 pages
- Content hash: SHA-256 for deduplication
- Path traversal: Sanitized via pathlib

### Prompt Injection Defense
- Retrieved text treated as untrusted
- System prompt instructs LLM to ignore context instructions
- Retrieved chunks clearly delimited
- Max chunk length: 10,000 characters
- Injection pattern detection in retrieved text

### Resource Protection
- Max file size prevents disk exhaustion
- Max page count prevents memory exhaustion
- Max chunk size prevents prompt overflow
- Batch size limits prevent API rate limiting

### Secrets Management
- API keys in .env (never committed)
- .env in .gitignore
- .env.example without real values
- No secrets in logs or error messages

### Execution Security
- Docker runs as non-root user
- No shell injection in file handling
- Path operations use pathlib

## Security Checklist
- [x] .env.example provided
- [x] .env in .gitignore
- [x] File type validation
- [x] File size limits
- [x] No secrets in logs
- [x] Non-root Docker user
- [x] Input validation on API
- [x] Prompt injection awareness

## Known Limitations
1. No malware scanning for uploads
2. No authentication (suitable for local/research)
3. No rate limiting
4. Prompt injection defense is probabilistic
5. No encryption at rest for vector store
