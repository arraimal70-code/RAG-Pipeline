r"""
src/parsing/table_parser.py — Markdown Table & Matrix Linearization Engine.

Addresses the critical "Table Blind Spot" in RAG:
Standard character/token chunkers shred multi-column tables across boundaries,
decoupling cell values from column headers and rendering financial statements,
balance sheets, and benchmark matrices unanswerable.

This module detects, parses, and linearizes tables into:
1. Canonical clean Markdown.
2. Row-Column Semantic Triples (Entity-Attribute-Value):
   e.g.: "[Row 1] Period: FY2023 | Revenue: $383.29B | Net Income: $96.99B | Margin: 25.3%"
3. Natural Language Table Schema Summaries:
   Allows dense bi-encoders and BM25 to locate cells with exact header context.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ParsedTable:
    """Structured representation of a parsed table."""
    headers: List[str]
    rows: List[List[str]]
    num_rows: int
    num_cols: int
    caption: Optional[str] = None
    column_types: Dict[str, str] = field(default_factory=dict)
    raw_markdown: str = ""

    def to_linearized_triples(self) -> List[str]:
        """
        Convert table rows into explicit Attribute-Value linearized semantic statements.
        Each statement anchors cell values with their explicit column header.
        """
        triples: List[str] = []
        for idx, row in enumerate(self.rows, start=1):
            cell_pairs = []
            for col_idx, header in enumerate(self.headers):
                val = row[col_idx] if col_idx < len(row) else ""
                val_clean = val.strip()
                if val_clean:
                    header_clean = header.strip()
                    cell_pairs.append(f"{header_clean}: {val_clean}")
            if cell_pairs:
                triple_str = f"[Row {idx}] " + " | ".join(cell_pairs)
                triples.append(triple_str)
        return triples

    def to_summary(self) -> str:
        """Generate a compact semantic synopsis of the table schema and entries."""
        header_str = ", ".join(self.headers)
        summary = f"Table contains {self.num_rows} rows and {self.num_cols} columns: [{header_str}]."
        if self.caption:
            summary = f"Caption: '{self.caption}'. " + summary
        return summary


class TableParser:
    """
    Detects and parses Markdown and delimited tables from documents.
    """

    TABLE_SEPARATOR_PATTERN = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$")

    @staticmethod
    def _clean_cell(cell: str) -> str:
        return cell.strip().replace("\n", " ")

    @staticmethod
    def _infer_type(values: List[str]) -> str:
        """Infer column type (numeric, currency, percentage, date, text)."""
        valid_vals = [v for v in values if v.strip() and v.strip() not in {"-", "N/A", "null"}]
        if not valid_vals:
            return "text"

        numeric_count = 0
        currency_count = 0
        percent_count = 0

        for val in valid_vals:
            v = val.strip()
            if re.match(r"^[\$€£¥]\s*[\d,.]+", v) or re.match(r"^[\d,.]+\s*[\$€£¥]", v):
                currency_count += 1
            elif "%" in v and re.search(r"\d", v):
                percent_count += 1
            elif re.match(r"^-?[\d,.]+$", v):
                numeric_count += 1

        total = len(valid_vals)
        if currency_count / total >= 0.5:
            return "currency"
        if percent_count / total >= 0.5:
            return "percentage"
        if (numeric_count + currency_count) / total >= 0.5:
            return "numeric"
        return "text"

    def parse_markdown_tables(self, text: str) -> List[ParsedTable]:
        """
        Scan text for Markdown tables and parse them into structured ParsedTable objects.
        """
        lines = text.splitlines()
        tables: List[ParsedTable] = []
        i = 0
        n = len(lines)

        while i < n:
            line = lines[i].strip()
            # Check if this line looks like a table row and next line is a separator
            if "|" in line and i + 1 < n and self.TABLE_SEPARATOR_PATTERN.match(lines[i + 1].strip()):
                # We found a table!
                header_line = line
                separator_line = lines[i + 1]
                table_lines = [header_line, separator_line]

                # Extract headers
                headers = [
                    self._clean_cell(c)
                    for c in header_line.split("|")
                    if c.strip() != ""
                ]

                # If leading/trailing pipes caused splitting issues
                if not headers:
                    headers = [self._clean_cell(c) for c in header_line.split("|")]

                # Read subsequent rows
                rows: List[List[str]] = []
                j = i + 2
                while j < n and "|" in lines[j] and lines[j].strip():
                    row_line = lines[j]
                    table_lines.append(row_line)
                    raw_cells = row_line.split("|")
                    # Handle optional surrounding pipes
                    if raw_cells and raw_cells[0].strip() == "":
                        raw_cells = raw_cells[1:]
                    if raw_cells and raw_cells[-1].strip() == "":
                        raw_cells = raw_cells[:-1]

                    cells = [self._clean_cell(c) for c in raw_cells]
                    # Pad or trim to match header length
                    if len(cells) < len(headers):
                        cells.extend([""] * (len(headers) - len(cells)))
                    elif len(cells) > len(headers):
                        cells = cells[: len(headers)]

                    rows.append(cells)
                    j += 1

                # Check for possible preceding caption
                caption = None
                if i > 0 and lines[i - 1].strip().startswith(("#", "Table", "**Table")):
                    caption = lines[i - 1].strip()

                # Infer column types
                col_types: Dict[str, str] = {}
                for col_idx, header in enumerate(headers):
                    col_vals = [r[col_idx] for r in rows if col_idx < len(r)]
                    col_types[header] = self._infer_type(col_vals)

                parsed_table = ParsedTable(
                    headers=headers,
                    rows=rows,
                    num_rows=len(rows),
                    num_cols=len(headers),
                    caption=caption,
                    column_types=col_types,
                    raw_markdown="\n".join(table_lines),
                )
                tables.append(parsed_table)
                i = j
            else:
                i += 1

        return tables

    def linearize_document_tables(self, text: str) -> str:
        """
        Enhance a document by appending linearized row-column statements
        and schema summaries for every table found in the text.
        Preserves original table while ensuring downstream chunkers and embedders
        capture explicit cell-header associations.
        """
        tables = self.parse_markdown_tables(text)
        if not tables:
            return text

        linearized_blocks = []
        for t_idx, table in enumerate(tables, start=1):
            block_lines = [
                f"\n--- [Linearized Table Representation #{t_idx}] ---",
                table.to_summary(),
                "Semantic Row Records:",
            ]
            block_lines.extend(table.to_linearized_triples())
            block_lines.append("--- [End Table] ---\n")
            linearized_blocks.append("\n".join(block_lines))

        return text + "\n\n" + "\n\n".join(linearized_blocks)
