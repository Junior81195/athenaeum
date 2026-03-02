"""PDF text extraction with section detection."""

import re


def extract_sections_from_pdf(pdf_path: str) -> list[dict]:
    """Extract text from PDF, split by major section headings.

    Returns: [{"title": "SECTION NAME", "text": "section body...", "page_start": 1, "page_end": 3}, ...]
    """
    import pdfplumber

    pages_text = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            pages_text.append((i + 1, text))

    if not pages_text:
        return []

    # Combine all text with page markers
    full_text_with_pages = []
    for page_num, text in pages_text:
        for line in text.split("\n"):
            full_text_with_pages.append((page_num, line))

    # Detect section headings:
    # - ALL CAPS lines (at least 3 chars, not just numbers)
    # - Lines that look like "Section N:" or "CHAPTER N"
    # - Lines starting with a number followed by a period and uppercase
    heading_pattern = re.compile(
        r'^(?:'
        r'[A-Z][A-Z\s&,/()-]{2,}$'  # ALL CAPS (3+ chars)
        r'|(?:SECTION|CHAPTER|ARTICLE|PART)\s+\w+'  # SECTION N, CHAPTER N
        r'|\d+\.?\s+[A-Z][A-Z\s]{2,}$'  # "1. SECTION NAME" or "1 SECTION NAME"
        r')'
    )

    sections = []
    current_title = "Introduction"
    current_lines = []
    current_page_start = 1

    for page_num, line in full_text_with_pages:
        stripped = line.strip()
        if not stripped:
            current_lines.append("")
            continue

        # Check if this line is a section heading
        is_heading = bool(heading_pattern.match(stripped))
        # Filter out lines that are too short or just numbers
        if is_heading and len(stripped) < 3:
            is_heading = False
        if is_heading and stripped.replace(" ", "").replace(".", "").isdigit():
            is_heading = False
        # Don't treat very long lines as headings (they're paragraphs)
        if is_heading and len(stripped) > 80:
            is_heading = False

        if is_heading and current_lines:
            # Save the previous section
            body = "\n".join(current_lines).strip()
            if body and len(body) > 50:  # Skip tiny sections
                sections.append({
                    "title": current_title,
                    "text": body,
                    "page_start": current_page_start,
                    "page_end": page_num - 1 if page_num > current_page_start else current_page_start,
                })
            current_title = stripped.strip()
            current_lines = []
            current_page_start = page_num
        else:
            current_lines.append(stripped)

    # Flush last section
    if current_lines:
        body = "\n".join(current_lines).strip()
        if body and len(body) > 50:
            last_page = pages_text[-1][0] if pages_text else current_page_start
            sections.append({
                "title": current_title,
                "text": body,
                "page_start": current_page_start,
                "page_end": last_page,
            })

    # If no sections were detected (no headings found), treat whole doc as one section
    if not sections:
        all_text = "\n".join(line for _, line in full_text_with_pages).strip()
        if all_text:
            sections.append({
                "title": pdf_path.rsplit("/", 1)[-1].rsplit(".", 1)[0],
                "text": all_text,
                "page_start": 1,
                "page_end": pages_text[-1][0] if pages_text else 1,
            })

    return sections


def extract_text_from_file(file_path: str) -> list[dict]:
    """Extract sections from a text file by splitting on blank-line-separated headings."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    if not content.strip():
        return []

    # For plain text, just return as a single document
    title = file_path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    return [{
        "title": title,
        "text": content.strip(),
        "page_start": None,
        "page_end": None,
    }]
