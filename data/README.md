# data/

Working directory for corpus data files. The primary ingestion path is the upload
endpoint (`POST /api/libraries/{id}/upload`) which accepts PDF, TXT, and MD files
via the web UI or API.

## Upload (preferred)

Upload documents via the frontend at `/library/{slug}/upload` or the API:
```bash
curl -X POST http://localhost:8140/api/libraries/{id}/upload \
  -H "Remote-User: your-user" \
  -F "file=@document.pdf"
```

The upload pipeline handles: section extraction, chunking, embedding, and topic clustering.
SHA-256 content dedup ensures re-uploading the same file is safe.

## Supported formats

- **PDF** — extracted via pdfplumber with section detection
- **TXT** — plain text, split by headings or fixed size
- **MD** — markdown, split by heading structure
