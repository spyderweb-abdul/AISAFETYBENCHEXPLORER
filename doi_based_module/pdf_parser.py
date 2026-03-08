"""
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025-2026 AISafetyBenchExplorer Contributors

Enhanced PDF Parser with Adaptive Backend Selection
===================================================

IMPROVEMENTS:
1. Intelligent Marker vs Nougat selection based on content type
2. GROBID integration for structured metadata pre-extraction
3. Improved error handling and fallback chains
4. GPU memory management for Nougat
5. Math-heavy paper detection heuristic

Backends (in priority order):
- GROBID: Fast metadata extraction (title, authors, abstract)
- Nougat: Best for math-heavy papers (LaTeX output)
- Marker: Fast general-purpose parser (Markdown output)
- PyMuPDF: Fallback for basic text extraction
"""

import os
import sys
import logging
from pathlib import Path
from typing import Tuple, Optional, Dict
from functools import partial
import re

logger = logging.getLogger(__name__)

class EnhancedPDFParser:
    """
    Enhanced PDF parser with adaptive backend selection.

    Key Features:
    - Automatic backend selection based on paper characteristics
    - GROBID integration for metadata bootstrapping
    - Robust fallback chain
    - GPU memory management
    """

    def __init__(
        self,
        prefer_nougat: bool = False,
        nougat_timeout: int = 300,
        enable_grobid: bool = True,
        grobid_url: str = "http://localhost:8070"
    ):
        """
        Initialize parser with multiple backends.

        Args:
            prefer_nougat: Always try Nougat first (slower but better for math)
            nougat_timeout: Timeout in seconds for Nougat processing
            enable_grobid: Use GROBID for metadata pre-extraction
            grobid_url: GROBID service URL
        """
        self.prefer_nougat = prefer_nougat
        self.nougat_timeout = nougat_timeout
        self.enable_grobid = enable_grobid
        self.grobid_url = grobid_url
        self._check_backends()

    def _check_backends(self):
        """Check which PDF parsing backends are available"""
        self.backends = {
            'grobid': False,
            'nougat': False,
            'marker': False,
            'pymupdf': False
        }

        # Check GROBID
        if self.enable_grobid:
            try:
                from grobid_parser import GROBIDParser
                self.grobid_parser = GROBIDParser(grobid_url=self.grobid_url)
                self.backends['grobid'] = self.grobid_parser.available
                if self.backends['grobid']:
                    logger.info("GROBID backend available")
            except ImportError:
                logger.info("GROBID parser not found (optional)")

        # Check Nougat
        try:
            import nougat
            from nougat.model import NougatModel
            from nougat.utils.checkpoint import get_checkpoint
            from nougat.utils.dataset import LazyDataset
            from nougat.postprocessing import markdown_compatible
            self.backends['nougat'] = True
            logger.info("Nougat backend available")
        except ImportError:
            logger.info("Nougat not available (pip install nougat-ocr)")
        except Exception as e:
            logger.warning(f"Nougat check failed: {e}")

        # Check Marker
        try:
            import marker
            from marker.convert import convert_single_pdf
            from marker.models import load_all_models
            self.backends['marker'] = True
            logger.info(" Marker backend available")
        except ImportError:
            logger.info("Marker not available (pip install marker-pdf)")
        except Exception as e:
            logger.warning(f"Marker check failed: {e}")

        # Check PyMuPDF
        try:
            import fitz
            self.backends['pymupdf'] = True
            logger.info(" PyMuPDF backend available")
        except ImportError:
            logger.info("PyMuPDF not available (pip install pymupdf)")

        # Log summary
        available = [k for k, v in self.backends.items() if v]
        if not available:
            raise RuntimeError(
                "No PDF parsing backend available! Install at least one:\n"
                "pip install pymupdf  # Basic fallback\n"
                "pip install marker-pdf  # Recommended\n"
                "pip install nougat-ocr  # Best for math"
            )
        else:
            logger.info(f"Available backends: {', '.join(available)}")

    def parse_pdf(
        self,
        pdf_path: str,
        extract_grobid_metadata: bool = True
    ) -> Tuple[str, str, Optional[Dict]]:
        """
        Parse PDF using best available method with adaptive backend selection.

        Args:
            pdf_path: Path to PDF file
            extract_grobid_metadata: Extract structured metadata with GROBID first

        Returns:
            Tuple of (text, format_hint, grobid_metadata)
            - text: Parsed full text
            - format_hint: 'latex', 'markdown', or 'text'
            - grobid_metadata: Structured metadata from GROBID (if available)
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        logger.info(f"Parsing PDF: {pdf_path.name}")

        # Step 1: Try GROBID for structured metadata (fast)
        grobid_metadata = None
        if extract_grobid_metadata and self.backends.get('grobid'):
            try:
                grobid_metadata = self.grobid_parser.extract_metadata(str(pdf_path))
                if grobid_metadata and grobid_metadata.get('title'):
                    logger.info(f"GROBID metadata: {grobid_metadata['title']}")
            except Exception as e:
                logger.warning(f"GROBID extraction failed: {e}")

        # Step 2: Detect paper characteristics for backend selection
        is_math_heavy = self._detect_math_heavy_paper(pdf_path)

        # Step 3: Select and use appropriate backend
        text, format_hint = self._parse_with_adaptive_backend(pdf_path, is_math_heavy)

        logger.info(f" Parsed {len(text)} characters ({format_hint} format)")

        return text, format_hint, grobid_metadata

    def _parse_with_adaptive_backend(
        self,
        pdf_path: Path,
        is_math_heavy: bool
    ) -> Tuple[str, str]:
        """Select and use appropriate parsing backend"""
        #if self.enable_grobid:
            #text, fmt = self.grobid_parser.extract_full_text(str(pdf_path))

        # Strategy 1: User preference for Nougat
        if self.prefer_nougat and self.backends['nougat']:
            try:
                text, fmt = self._parse_with_nougat(pdf_path)
                logger.info(f"Nougat (user preference): {len(text)} chars")
                return text, fmt
            except Exception as e:
                logger.warning(f"Nougat failed: {e}")

        # Strategy 2: Math-heavy papers  Nougat
        if is_math_heavy and self.backends['nougat'] and not self.prefer_nougat:
            logger.info("Detected math-heavy paper  using Nougat for LaTeX accuracy")
            try:
                text, fmt = self._parse_with_nougat(pdf_path)
                logger.info(f"Nougat (math-heavy): {len(text)} chars")
                return text, fmt
            except Exception as e:
                logger.warning(f"Nougat failed: {e}, falling back...")

        # Strategy 3: General papers  Marker (faster)
        if self.backends['marker']:
            try:
                text, fmt = self._parse_with_marker(pdf_path)
                logger.info(f" Marker: {len(text)} chars")
                return text, fmt
            except Exception as e:
                logger.warning(f"Marker failed: {e}")

        # Strategy 4: Fallback to Nougat if available and not tried yet
        if self.backends['nougat'] and not is_math_heavy and not self.prefer_nougat:
            try:
                text, fmt = self._parse_with_nougat(pdf_path)
                logger.info(f" Nougat (fallback): {len(text)} chars")
                return text, fmt
            except Exception as e:
                logger.warning(f"Nougat fallback failed: {e}")

        # Strategy 5: Last resort - PyMuPDF
        if self.backends['pymupdf']:
            try:
                text, fmt = self._parse_with_pymupdf(pdf_path)
                logger.info(f" PyMuPDF (basic): {len(text)} chars")
                return text, fmt
            except Exception as e:
                logger.error(f"PyMuPDF failed: {e}")
                raise

        raise RuntimeError("All PDF parsing methods failed")

    def _detect_math_heavy_paper(self, pdf_path: Path) -> bool:
        """
        Heuristic to detect math-heavy papers.
        Samples first 3 pages and counts math indicators.
        """
        if not self.backends['pymupdf']:
            return False  # Can't detect without PyMuPDF

        try:
            import fitz
            doc = fitz.open(str(pdf_path))

            math_indicators = 0
            pages_to_check = min(3, len(doc))

            for page_num in range(pages_to_check):
                text = doc[page_num].get_text()

                # Count math indicators
                math_indicators += text.count('\\')  # LaTeX commands
                math_indicators += text.count('')  # Summation
                math_indicators += text.count('')  # Integral
                math_indicators += text.count('')  # Product
                math_indicators += text.count('')  # Less than or equal
                math_indicators += text.count('')  # Greater than or equal
                math_indicators += text.count('')  # Element of
                math_indicators += text.count('')  # Arrow

                # Count Greek letters
                greek_letters = len(re.findall(r'[--]', text))
                math_indicators += greek_letters

                # Count equation-like patterns
                equation_patterns = len(re.findall(r'=\s*[0-9a-zA-Z]', text))
                math_indicators += equation_patterns

            doc.close()

            # Threshold: >50 math indicators in first 3 pages = math-heavy
            is_heavy = math_indicators > 50
            logger.info(
                f"Math detection: {math_indicators} indicators  "
                f"{'MATH-HEAVY' if is_heavy else 'GENERAL'}"
            )
            return is_heavy

        except Exception as e:
            logger.warning(f"Math detection failed: {e}")
            return False

    def _parse_with_nougat(self, pdf_path: Path) -> Tuple[str, str]:
        """Parse PDF with Nougat (LaTeX-style output)"""
        try:
            from nougat import NougatModel
            from nougat.utils.checkpoint import get_checkpoint
            from nougat.utils.dataset import LazyDataset
            from nougat.postprocessing import markdown_compatible
            import torch

            logger.info("Loading Nougat model...")
            checkpoint = get_checkpoint()
            model = NougatModel.from_pretrained(checkpoint)

            # GPU setup with fallback
            device = "cuda" if torch.cuda.is_available() else "cpu"
            if device == "cuda":
                logger.info("Using GPU for Nougat")
                try:
                    model = model.to("cuda")
                except RuntimeError as e:
                    logger.warning(f"GPU OOM, falling back to CPU: {e}")
                    model = model.to("cpu")
                    device = "cpu"
            else:
                logger.info("Using CPU for Nougat (slower)")

            model.eval()

            # Create dataset with prepare function
            prepare_fn = partial(model.encoder.prepare_input, random_padding=False)

            try:
                dataset = LazyDataset(str(pdf_path), prepare_fn, None)
                logger.info(f"Dataset created: {dataset.size} pages")
            except TypeError:
                raise RuntimeError("LazyDataset initialization failed - check Nougat version")

            # Process pages
            predictions = []
            batch_size = 4 if device == "cuda" else 1

            for i, sample in enumerate(dataset):
                if sample is None:
                    logger.warning(f"Skipping page {i+1} (None sample)")
                    continue

                try:
                    # Handle tuple unpacking (LazyDataset returns (tensor, index))
                    if isinstance(sample, tuple):
                        image_tensor = sample[0]
                    else:
                        image_tensor = sample

                    # Ensure correct dimensions
                    if image_tensor.dim() == 3:
                        image_tensor = image_tensor.unsqueeze(0)

                    image_tensor = image_tensor.to(device)

                    # Inference
                    with torch.no_grad():
                        model_output = model.inference(image_tensors=image_tensor)

                    pred_text = model_output["predictions"][0]
                    pred_text = markdown_compatible(pred_text)
                    predictions.append(pred_text)

                    # Clear GPU cache periodically
                    if device == "cuda" and (i + 1) % batch_size == 0:
                        torch.cuda.empty_cache()

                except Exception as e:
                    logger.warning(f"Failed to process page {i+1}: {e}")
                    predictions.append("")

            # Combine pages
            full_text = "\n\n".join(predictions)
            full_text = re.sub(r'\n{3,}', '\n\n', full_text).strip()

            logger.info(f"Processed {len(predictions)} pages with Nougat")
            return full_text, "latex"

        except Exception as e:
            logger.error(f"Nougat parsing error: {e}")
            raise

    def _parse_with_marker(self, pdf_path: Path) -> Tuple[str, str]:
        """Parse PDF with Marker (Markdown output)"""
        try:
            from marker.convert import convert_single_pdf
            from marker.models import load_all_models

            logger.info("Loading Marker models...")
            model_lst = load_all_models()

            logger.info("Converting PDF with Marker...")
            full_text, images, out_meta = convert_single_pdf(
                str(pdf_path),
                model_lst,
                max_pages=None,
                langs=None
            )

            return full_text, "markdown"

        except Exception as e:
            logger.error(f"Marker parsing error: {e}")
            raise

    def _parse_with_pymupdf(self, pdf_path: Path) -> Tuple[str, str]:
        """Parse PDF with PyMuPDF (basic text extraction)"""
        try:
            import fitz

            logger.info("Parsing with PyMuPDF...")
            doc = fitz.open(str(pdf_path))

            full_text = []
            for page_num, page in enumerate(doc):
                text = page.get_text("text", sort=True)
                # Clean up excessive whitespace
                text = re.sub(r' {3,}', ' ', text)
                text = re.sub(r'\n{4,}', '\n\n\n', text)
                full_text.append(text)

            doc.close()

            markdown_text = '\n\n---PAGE BREAK---\n\n'.join(full_text)
            return markdown_text, "text"

        except Exception as e:
            logger.error(f"PyMuPDF parsing error: {e}")
            raise


def parse_pdf_to_markdown(
    pdf_path: str,
    prefer_nougat: bool = False,
    nougat_timeout: int = 300,
    enable_grobid: bool = True
) -> Tuple[str, str, Optional[Dict]]:
    """
    Convenience function to parse PDF with best available method.

    Args:
        pdf_path: Path to PDF file
        prefer_nougat: Always try Nougat first
        nougat_timeout: Nougat timeout in seconds
        enable_grobid: Use GROBID for metadata extraction

    Returns:
        (text, format_hint, grobid_metadata) tuple
    """
    parser = EnhancedPDFParser(
        prefer_nougat=prefer_nougat,
        nougat_timeout=nougat_timeout,
        enable_grobid=enable_grobid
    )
    return parser.parse_pdf(pdf_path, extract_grobid_metadata=enable_grobid)