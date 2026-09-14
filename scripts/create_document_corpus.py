#!/usr/bin/env python3
"""
Create realistic financial document corpus for benchmarking.

This script creates sample financial documents that mimic real SEC 10-K filings.
These documents contain realistic financial data that can be used for benchmarking.
"""

import json
from pathlib import Path
from datetime import datetime
import hashlib

def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(block)
    return sha256_hash.hexdigest()

def create_apple_10k_2023():
    """Create Apple 10-K 2023 document."""
    content = """# APPLE INC.
# FORM 10-K
# For the Fiscal Year Ended September 30, 2023

## ITEM 1. BUSINESS

Apple Inc. (the "Company") designs, manufactures and markets smartphones, 
personal computers, tablets, wearables and accessories, and sells a variety 
of related services.

## ITEM 6. OPERATING AND FINANCIAL REVIEW AND PROSPECTS OF THE COMPANY

### Fiscal 2023 Highlights

Net sales increased 2% to $383.3 billion during 2023 compared to $394.3 billion in 2022.

Products net sales decreased 4% to $298.1 billion in 2023 compared to $310.5 billion in 2022.

Services net sales increased 16% to $85.2 billion in 2023 compared to $73.0 billion in 2022.

### Gross Margin

Gross margin was 44.1% in 2023 compared to 43.3% in 2022.

Products gross margin was 36.6% in 2023 compared to 35.3% in 2022.

Services gross margin was 70.8% in 2023 compared to 68.4% in 2022.

### Operating Expenses

Research and Development expense increased 8% to $29.9 billion in 2023.

Selling, General and Administrative expense increased 3% to $24.9 billion in 2023.

### Net Income

Net income was $97.0 billion in 2023 compared to $99.8 billion in 2022.

Diluted earnings per share was $6.16 in 2023 compared to $6.11 in 2022.

## ITEM 1A. RISK FACTORS

The Company's business, reputation, brands, financial condition and operating 
results could be materially adversely affected by a variety of factors, including:

1. Global and regional economic conditions could materially adversely affect the Company.
2. The Company's operations and performance could be significantly affected by global economic conditions.
3. Political events, trade relationships and other international conditions could adversely affect the Company.

## ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS

### Products and Services Performance

iPhone net sales decreased 2% to $200.6 billion in 2023.

Mac net sales decreased 7% to $29.4 billion in 2023.

iPad net sales decreased 5% to $28.3 billion in 2023.

Wearables, Home and Accessories net sales decreased 3% to $39.8 billion in 2023.

Services net sales increased 16% to $85.2 billion in 2023.

### Liquidity and Capital Resources

The Company's total cash and marketable securities was $162.2 billion as of September 30, 2023.

The Company returned $77.6 billion to shareholders during 2023 through dividends and share repurchases.
"""
    
    doc_path = Path("data/documents/apple_10k_2023.txt")
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(content)
    
    return {
        "filename": "apple_10k_2023.txt",
        "company": "Apple Inc.",
        "ticker": "AAPL",
        "filing_type": "10-K",
        "filing_year": 2023,
        "filing_date": "2023-11-03",
        "sha256": compute_sha256(doc_path),
        "size_bytes": doc_path.stat().st_size,
        "download_timestamp": datetime.utcnow().isoformat(),
        "source": "SEC EDGAR (sample document)",
        "url": "https://www.sec.gov/Archives/edgar/data/320193/000032019323000106/aapl-20230930.htm",
        "status": "sample_document",
    }

def create_microsoft_10k_2023():
    """Create Microsoft 10-K 2023 document."""
    content = """# MICROSOFT CORPORATION
# FORM 10-K
# For the Fiscal Year Ended June 30, 2023

## ITEM 1. BUSINESS

Microsoft Corporation (the "Company") develops and supports software, services, 
devices, and solutions worldwide.

## ITEM 6. OPERATING AND FINANCIAL REVIEW

### Fiscal 2023 Highlights

Revenue increased 7% to $211.9 billion in fiscal year 2023 from $198.3 billion in 2022.

Productivity and Business Processes revenue increased 10% to $69.3 billion.

Intelligent Cloud revenue increased 19% to $87.9 billion.

More Personal Computing revenue decreased 6% to $54.7 billion.

### Gross Margin

Gross margin was 69% in fiscal year 2023 compared to 68% in fiscal year 2022.

### Operating Expenses

Research and development expense increased 11% to $27.2 billion.

Selling and marketing expense increased 1% to $22.8 billion.

### Operating Income

Operating income increased 12% to $88.5 billion in fiscal year 2023 from $79.1 billion in 2022.

Operating margin was 42% in fiscal year 2023 compared to 41% in fiscal year 2022.

### Net Income

Net income increased 8% to $72.4 billion in fiscal year 2023 from $66.9 billion in 2022.

Diluted earnings per share increased 9% to $9.68 from $8.91.

## ITEM 1A. RISK FACTORS

Our business is subject to various risks, including:

1. Competition in the technology industry is intense and rapidly changing.
2. Our success is highly dependent on our ability to innovate and bring new products to market.
3. We face risks related to cybersecurity and data privacy.

## ITEM 7. MANAGEMENT'S DISCUSSION

### Segment Performance

Productivity and Business Processes:
- Office Commercial products and cloud services revenue increased 10%
- Office Consumer products and cloud services revenue increased 2%
- LinkedIn revenue increased 10%

Intelligent Cloud:
- Server products and cloud services revenue increased 19%
- Azure and other cloud services revenue increased 29%

More Personal Computing:
- Windows revenue decreased 7%
- Gaming revenue decreased 11%
- Search and news advertising revenue increased 15%

### Employees

As of June 30, 2023, we employed 221,000 people worldwide.
"""
    
    doc_path = Path("data/documents/microsoft_10k_2023.txt")
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(content)
    
    return {
        "filename": "microsoft_10k_2023.txt",
        "company": "Microsoft Corporation",
        "ticker": "MSFT",
        "filing_type": "10-K",
        "filing_year": 2023,
        "filing_date": "2023-08-02",
        "sha256": compute_sha256(doc_path),
        "size_bytes": doc_path.stat().st_size,
        "download_timestamp": datetime.utcnow().isoformat(),
        "source": "SEC EDGAR (sample document)",
        "url": "https://www.sec.gov/Archives/edgar/data/789019/000078901923000032/msft-20230630.htm",
        "status": "sample_document",
    }

def create_amazon_10k_2023():
    """Create Amazon 10-K 2023 document."""
    content = """# AMAZON.COM, INC.
# FORM 10-K
# For the Fiscal Year Ended December 31, 2023

## ITEM 1. BUSINESS

Amazon.com, Inc. (the "Company") seeks to be Earth's most customer-centric company.

## ITEM 6. OPERATING RESULTS

### Fiscal 2023 Highlights

Net sales increased 12% to $574.8 billion in 2023 from $513.8 billion in 2022.

North America segment net sales increased 12% to $352.8 billion.

International segment net sales increased 11% to $131.2 billion.

AWS segment net sales increased 13% to $90.8 billion.

### Operating Income

Operating income increased to $36.9 billion in 2023 compared to $12.2 billion in 2022.

North America operating income was $14.3 billion in 2023.

International operating income was $2.8 billion in 2023.

AWS operating income was $24.6 billion in 2023.

### Gross Margin

Gross margin was 48% in 2023 compared to 43% in 2022.

### Operating Expenses

Technology and infrastructure expense increased 14% to $85.6 billion.

Sales and marketing expense increased 8% to $34.4 billion.

### Net Income

Net income increased to $30.4 billion in 2023 compared to $2.7 billion in 2022.

Diluted earnings per share increased to $2.90 in 2023 compared to $0.27 in 2022.

## ITEM 1A. RISK FACTORS

Our business is subject to risks including:

1. We face intense competition in all areas of our business.
2. Our AWS business faces competition from established technology companies.
3. Our expansion into new businesses and geographies involves significant risks.

## ITEM 7. MANAGEMENT'S DISCUSSION

### Segment Analysis

North America:
- Online stores revenue increased 10%
- Physical stores revenue increased 6%
- Third-party seller services revenue increased 14%
- Advertising services revenue increased 25%

International:
- Online stores revenue increased 11%
- Third-party seller services revenue increased 12%

AWS:
- Compute revenue increased 15%
- Storage revenue increased 18%
- Database revenue increased 22%
- Machine Learning and AI services revenue increased 35%

### Employees

As of December 31, 2023, we employed approximately 1,525,000 full-time and part-time employees.
"""
    
    doc_path = Path("data/documents/amazon_10k_2023.txt")
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(content)
    
    return {
        "filename": "amazon_10k_2023.txt",
        "company": "Amazon.com, Inc.",
        "ticker": "AMZN",
        "filing_type": "10-K",
        "filing_year": 2023,
        "filing_date": "2024-02-02",
        "sha256": compute_sha256(doc_path),
        "size_bytes": doc_path.stat().st_size,
        "download_timestamp": datetime.utcnow().isoformat(),
        "source": "SEC EDGAR (sample document)",
        "url": "https://www.sec.gov/Archives/edgar/data/1018724/000101872424000004/amzn-20231231.htm",
        "status": "sample_document",
    }

def main():
    """Main entry point."""
    print("Creating financial document corpus...")
    
    documents = []
    
    # Create documents
    documents.append(create_apple_10k_2023())
    documents.append(create_microsoft_10k_2023())
    documents.append(create_amazon_10k_2023())
    
    # Create manifest
    manifest = {
        "version": "2.0.0",
        "created_at": datetime.utcnow().isoformat(),
        "total_documents": len(documents),
        "source": "SEC EDGAR (sample documents for benchmarking)",
        "note": "These are sample documents mimicking real SEC filings for benchmarking purposes.",
        "documents": documents,
    }
    
    manifest_path = Path("data/manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\n✓ Created {len(documents)} documents")
    print(f"✓ Manifest saved to {manifest_path}")
    print("\nDocuments created:")
    for doc in documents:
        print(f"  - {doc['filename']} ({doc['company']})")
    
    print("\n" + "=" * 80)
    print("NOTE: These are sample documents for benchmarking.")
    print("For production use, download actual SEC filings from:")
    print("https://www.sec.gov/edgar/searchedgar/companysearch.html")
    print("=" * 80)

if __name__ == "__main__":
    main()
