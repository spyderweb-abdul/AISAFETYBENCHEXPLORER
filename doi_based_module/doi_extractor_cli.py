"""
CLI Tool for DOI-Based Benchmark Metadata Extraction
====================================================

Command-line interface for the DOI-based extraction pipeline.

Usage examples:

    # Single DOI
    python doi_extractor_cli.py --doi "10.18653/v1/2021.acl-long.330"

    # Single arXiv paper
    python doi_extractor_cli.py --doi "2103.14296"

    # Batch from CSV (with DOI column)
    python doi_extractor_cli.py --batch dois.csv --doi-column "DOI"

    # With full-text extraction
    python doi_extractor_cli.py --doi "10.xxx/yyy" --full-text --save-pdfs

    # Using OpenAI
    python doi_extractor_cli.py --doi "10.xxx/yyy" --backend openai --model gpt-4o
"""

import argparse
import logging
import sys
from pathlib import Path
import json
import csv
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
import os

from doi_pipeline import OptimizedDOIPipeline
from models import (AggregatedPaperMetadata, BenchmarkMetadata, QualityAssessment, URLExtraction, EvaluationMetric)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('doi_extraction.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)
load_dotenv()

class DOIExtractorCLI:
    """CLI wrapper for DOI-based extraction pipeline."""

    def __init__(self, args):
        self.args = args

        # Validate email
        if not args.email:
            logger.error("Email is required for API access (--email)")
            sys.exit(1)

        # Initialize pipeline
        self.pipeline = OptimizedDOIPipeline(email=args.email, s2_api_key=args.s2_key, extractor_model=args.model, validation_model=args.validation_model, backend=args.backend, openai_api_key=args.openai_key)

        # Output directory
        self.output_dir = Path(args.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("CLI initialized")
        logger.info(f"Output dir: {self.output_dir}")

    def run(self):
        """Main execution logic."""
        if self.args.pdf:
            # Process pdf directly
            self.process_pdf_file(self.args.pdf)
        
        elif self.args.doi:
            # Single DOI mode
            self.process_single_doi(self.args.doi)

        elif self.args.batch:
            # Batch mode
            self.process_batch(self.args.batch)

        else:
            logger.error("Must specify either --doi or --batch")
            sys.exit(1)
    
    def process_pdf_file(self, pdf_path: str):
        """Process local PDF file"""
        logger.info("="*70)
        logger.info("PDF DIRECT MODE")
        logger.info("="*70)

        try:
            extracted, quality, api_metadata = self.pipeline.process_from_pdf(
                pdf_path=pdf_path,
                doi=self.args.doi  # Optional DOI for enrichment
            )

            if extracted:
                # Generate filename from benchmark name or PDF filename
                benchmark_name = extracted.get("Benchmark Name", "unknown")
                if benchmark_name == "unknown" or not benchmark_name:
                    # Use PDF filename as fallback
                    from pathlib import Path
                    benchmark_name = Path(pdf_path).stem

                # Save results (just like process_single_doi does)
                self._save_single_result(benchmark_name, extracted, quality, api_metadata)

                # Print summary to console
                self._print_summary(extracted, quality)
            else:
                logger.error("Extraction failed for PDF")
        except Exception as e:
            logger.error(f"Processing failed: {e}", exc_info=True)

    
    def process_single_doi(self, doi: str):
        """Process a single DOI."""

        logger.info("="*70)
        logger.info("SINGLE DOI MODE")
        logger.info("="*70)

        try:
            extracted, quality, api_metadata = self.pipeline.process_from_doi(identifier=doi, extract_full_text=self.args.full_text, save_pdf=self.args.save_pdfs, output_dir=self.output_dir if self.args.save_pdfs else None)

            if extracted:
                # Save results
                self._save_single_result(doi, extracted, quality, api_metadata)

                # Print summary
                self._print_summary(extracted, quality)
            else:
                logger.error(f"Extraction failed for {doi}")

        except Exception as e:
            logger.error(f"Processing failed: {e}", exc_info=True)

    def process_batch(self, csv_path: str):
        """Process multiple DOIs from CSV file."""

        logger.info("="*70)
        logger.info("BATCH MODE")
        logger.info("="*70)

        csv_file = Path(csv_path)
        if not csv_file.exists():
            logger.error(f"CSV file not found: {csv_path}")
            sys.exit(1)

        # Read DOIs from CSV
        dois = self._read_dois_from_csv(csv_file)

        logger.info(f"Found {len(dois)} DOIs to process")
        logger.info("="*70)

        # Process each DOI
        results = []

        for i, doi_info in enumerate(dois, 1):
            doi = doi_info['doi']
            logger.info(f"[{i}/{len(dois)}] Processing: {doi}")

            try:
                extracted, quality, api_metadata = self.pipeline.process_from_doi(
                    identifier=doi,
                    extract_full_text=self.args.full_text,
                    save_pdf=self.args.save_pdfs,
                    output_dir=self.output_dir if self.args.save_pdfs else None
                )

                if extracted:
                    # Save individual result
                    self._save_single_result(doi, extracted, quality, api_metadata)

                    # Track for batch summary
                    results.append({
                        'doi': doi,
                        'benchmark': extracted.get('Benchmark Name', 'Unknown'),
                        'success': True,
                        'quality': quality.overall_score,
                        'requires_review': quality.requires_human_review
                    })
                else:
                    results.append({
                        'doi': doi,
                        'success': False,
                        'error': 'Extraction failed'
                    })

            except Exception as e:
                logger.error(f"Failed to process {doi}: {e}")
                results.append({
                    'doi': doi,
                    'success': False,
                    'error': str(e)
                })

        # Save batch summary
        self._save_batch_summary(results)

        # Print batch stats
        self._print_batch_stats(results)

    def _read_dois_from_csv(self, csv_file: Path) -> List[Dict[str, str]]:
        """Read DOIs from CSV file."""

        dois = []

        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            # Find DOI column
            doi_col = self.args.doi_column

            if doi_col not in reader.fieldnames:
                logger.error(f"Column '{doi_col}' not found in CSV")
                logger.error(f"Available columns: {', '.join(reader.fieldnames)}")
                sys.exit(1)

            for row in reader:
                doi = row[doi_col].strip()
                if doi:
                    dois.append({'doi': doi, 'row': row})

        return dois

    def _save_single_result(self, doi: str, extracted: Dict[str, Any], quality: Any, api_metadata: AggregatedPaperMetadata):
        """Save results for a single DOI."""

        # Sanitize DOI for filename
        safe_doi = doi.replace('/', '_').replace('.', '_')

        # Save extracted metadata
        metadata_file = self.output_dir / f"{safe_doi}_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(extracted, f, indent=2, ensure_ascii=False)

        # Save quality assessment
        quality_file = self.output_dir / f"{safe_doi}_quality.json"
        with open(quality_file, 'w', encoding='utf-8') as f:
            json.dump(quality.model_dump(), f, indent=2)

        # Save API metadata
        api_file = self.output_dir / f"{safe_doi}_api.json"
        with open(api_file, 'w', encoding='utf-8') as f:
            json.dump(api_metadata.model_dump(), f, indent=2, default=str)

        logger.info(f"  Saved results to: {self.output_dir}")

    def _save_batch_summary(self, results: List[Dict]):
        """Save batch processing summary."""

        summary_file = self.output_dir / f"batch_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        summary = {
            'total': len(results),
            'successful': sum(1 for r in results if r.get('success')),
            'failed': sum(1 for r in results if not r.get('success')),
            'requires_review': sum(1 for r in results if r.get('requires_review')),
            'timestamp': datetime.now().isoformat(),
            'results': results
        }

        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)

        logger.info(f"Batch summary saved to: {summary_file}")

    def _print_summary(self, extracted: Dict[str, Any], quality: Any):
        """Print extraction summary."""

        print("\n" + "="*70)
        print("EXTRACTION SUMMARY")
        print("="*70)
        print(f"Benchmark: {extracted.get('Benchmark Name', 'Unknown')}")
        print(f"Title: {extracted.get('Paper Title', 'Unknown')}")
        print(f"Authors: {extracted.get('Authors', 'Unknown')[:60]}...")
        print(f"Year: {extracted.get('Year', 'Unknown')}")
        print(f"Venue: {extracted.get('Venue', 'Unknown')}")
        print(f"Citations: {extracted.get('Citation Count', 0)}")
        print(f"Metrics extracted: {len(extracted.get('Evaluation Metrics', []))}")
        print(f"\nQuality Score: {quality.overall_score:.2f}")
        print(f"Requires Review: {quality.requires_human_review}")
        print("="*70 + "\n")

    def _print_batch_stats(self, results: List[Dict]):
        """Print batch processing statistics."""

        successful = sum(1 for r in results if r.get('success'))
        failed = sum(1 for r in results if not r.get('success'))
        needs_review = sum(1 for r in results if r.get('requires_review'))

        print("\n" + "="*70)
        print("BATCH PROCESSING COMPLETE")
        print("="*70)
        print(f"Total processed: {len(results)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Needs review: {needs_review}")
        print(f"\nResults saved to: {self.output_dir}")
        print("="*70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Extract AI safety benchmark metadata from DOI/arXiv ID",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--doi', help='Single DOI or arXiv ID to process')
    input_group.add_argument('--batch', help='CSV file with DOIs to process')

    # Batch options
    parser.add_argument('--doi-column', default='DOI', help='Column name containing DOIs in CSV (default: DOI)')

    # API credentials
    parser.add_argument('--email', default=os.getenv('EMAIL_ADDRESS'), help='Email for Unpaywall API (or set UNPAYWALL_EMAIL env var)')
    parser.add_argument('--s2-key', default=os.getenv('S2_API_KEY'), help='Semantic Scholar API key (optional, for higher rate limits)')
    parser.add_argument('--openai-key', default=os.getenv('OPENAI_API_KEY'), help='OpenAI API key (if using --backend openai)')

    # LLM backend
    parser.add_argument('--backend', choices=['ollama', 'openai'], default='ollama', help='LLM backend to use')
    parser.add_argument('--model', default='gemma3:27b', help='Model for extraction (default: qwen2.5:32b)')
    parser.add_argument('--validation-model', default='qwen2.5:14b', help='Model for validation (default: qwen2.5:14b)')

    # Full-text options
    parser.add_argument('--full-text', action='store_true', help='Download and parse full text (if OA available)')
    parser.add_argument('--save-pdfs', action='store_true', help='Save downloaded PDFs to output directory')
    parser.add_argument('--pdf', help='Direct PDF file path (bypasses DOI resolution)')

    # Output
    parser.add_argument('--output-dir', default='doi_extracted_metadata', help='Output directory (default: doi_extracted_metadata)')

    args = parser.parse_args()

    # Run CLI
    cli = DOIExtractorCLI(args)
    cli.run()


if __name__ == '__main__':
    main()
