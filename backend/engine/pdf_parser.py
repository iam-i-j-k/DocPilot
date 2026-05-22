import os
import re
import subprocess
import shutil
import datetime
from typing import List, Dict, Any
from PIL import Image
import pdfplumber
import pytesseract

def log_to_file(message: str):
    """
    Writes persistent tracking logs to the shared output directory.
    """
    try:
        log_path = os.path.join(os.getenv("OUTPUT_DIR", "/app/output"), "docpilot_pipeline.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        timestamp = datetime.datetime.now().isoformat()
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass

class PDFParser:
    """
    Parser engine class responsible for PDF text extraction, OCR,
    scanned vs native detection, table extraction, and page rasterization.
    """

    @staticmethod
    def is_scanned(pdf_path: str) -> bool:
        """
        Determines if a PDF is scanned by running pdftotext on Page 1.
        Returns True if the extracted meaningful characters count is under 80, 
        indicating an image-based scanned page.
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        try:
            log_to_file(f"PDFParser.is_scanned: Running pdftotext on page 1 of {pdf_path}")
            # Run pdftotext on page 1 only to standard out
            result = subprocess.run(
                ["pdftotext", "-f", "1", "-l", "1", pdf_path, "-"],
                capture_output=True,
                text=True,
                check=False
            )
            text = result.stdout or ""
            # Strip whitespace to get meaningful character count
            meaningful_chars = re.sub(r"\s+", "", text)
            is_scanned_res = len(meaningful_chars) < 80
            log_to_file(f"PDFParser.is_scanned: Result is {is_scanned_res} (meaningful chars found: {len(meaningful_chars)})")
            return is_scanned_res
        except Exception as e:
            log_to_file(f"PDFParser.is_scanned: pdftotext failed ({str(e)}). Falling back to pdfplumber...")
            # Fallback check if pdftotext is not available or errors
            # Let's open with pdfplumber and inspect the first page
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    if not pdf.pages:
                        log_to_file("PDFParser.is_scanned: PDF has 0 pages. Flagging as scanned (True)")
                        return True
                    text = pdf.pages[0].extract_text() or ""
                    meaningful_chars = re.sub(r"\s+", "", text)
                    is_scanned_res = len(meaningful_chars) < 80
                    log_to_file(f"PDFParser.is_scanned pdfplumber fallback result: {is_scanned_res}")
                    return is_scanned_res
            except Exception as fb_err:
                log_to_file(f"PDFParser.is_scanned fallback also failed ({str(fb_err)}). Defaulting to scanned (True)")
                return True

    @staticmethod
    def extract_text_pages(pdf_path: str) -> List[str]:
        """
        Extracts layout-preserved text from each page using pdftotext.
        Cleans headers, footers, and common/specific watermark lines.
        """
        log_to_file(f"PDFParser.extract_text_pages: Initializing text extraction for {pdf_path}")
        pages_text: List[str] = []
        try:
            # Use pdfplumber to safely get page count
            with pdfplumber.open(pdf_path) as pdf:
                page_count = len(pdf.pages)
            log_to_file(f"PDFParser.extract_text_pages: Determined page count is {page_count} via pdfplumber")
        except Exception as p_err:
            log_to_file(f"PDFParser.extract_text_pages: pdfplumber page count failed ({str(p_err)}). Falling back to pdfinfo...")
            # Fallback page count extraction via pdfinfo
            page_count = 1
            try:
                info_res = subprocess.run(["pdfinfo", pdf_path], capture_output=True, text=True, check=False)
                match = re.search(r"Pages:\s+(\d+)", info_res.stdout)
                if match:
                    page_count = int(match.group(1))
                log_to_file(f"PDFParser.extract_text_pages: Determined page count is {page_count} via pdfinfo")
            except Exception as info_err:
                log_to_file(f"PDFParser.extract_text_pages fallback info failed ({str(info_err)}). Using 1 as boundary.")
                pass

        for page_num in range(1, page_count + 1):
            try:
                log_to_file(f"PDFParser.extract_text_pages: Extracting Page {page_num} of {page_count} using pdftotext...")
                # Run pdftotext with -layout option on each specific page
                res = subprocess.run(
                    ["pdftotext", "-layout", "-f", str(page_num), "-l", str(page_num), pdf_path, "-"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                raw_text = res.stdout or ""
                cleaned_text = PDFParser._clean_page_text(raw_text)
                pages_text.append(cleaned_text)
                log_to_file(f"PDFParser.extract_text_pages: Successfully extracted and cleaned page {page_num}")
            except Exception as page_exc:
                log_to_file(f"PDFParser.extract_text_pages: Error extracting page {page_num} ({str(page_exc)}). Appending empty string.")
                pages_text.append("")
        
        return pages_text

    @staticmethod
    def extract_tables(pdf_path: str) -> Dict[int, List[List[Any]]]:
        """
        Extracts tables from native/scanned text pages utilizing pdfplumber.
        Returns a dictionary mapping 1-indexed page numbers to table list representation.
        """
        log_to_file("PDFParser.extract_tables: Initializing table extraction...")
        tables_by_page: Dict[int, List[List[Any]]] = {}
        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                log_to_file(f"PDFParser.extract_tables: Parsing {total_pages} pages for tables...")
                for idx, page in enumerate(pdf.pages):
                    page_num = idx + 1
                    
                    # SYSTEM SAFETY AND OPTIMIZATION CORES:
                    # In complex physical/academic charts (drawing lines, CAD matrices, vectors),
                    # pdfplumber attempts to form intersections which is O(N^2) or O(N^3) CPU-stuck loop.
                    # We check and pre-filter vectors.
                    rects_count = len(page.rects) if hasattr(page, "rects") else 0
                    lines_count = len(page.lines) if hasattr(page, "lines") else 0
                    images_count = len(page.images) if hasattr(page, "images") else 0
                    
                    log_to_file(f"PDFParser.extract_tables Check: Page {page_num} size/layout elements -> Rects: {rects_count}, Lines: {lines_count}, Images: {images_count}")
                    
                    if rects_count + lines_count > 500:
                        log_to_file(f"PDFParser.extract_tables WARNING: Skipping page {page_num} table extraction. Content has {rects_count + lines_count} vector objects, which can hang pdfplumber's line analyzer.")
                        tables_by_page[page_num] = []
                        continue
                    
                    log_to_file(f"PDFParser.extract_tables: Extracting tables from Page {page_num} of {total_pages}...")
                    extracted = page.extract_tables()
                    log_to_file(f"PDFParser.extract_tables: Completed extraction for Page {page_num}. Found {len(extracted) if extracted else 0} tables.")
                    
                    if extracted:
                        # Clean empty or None table values to empty strings
                        cleaned_extracted = []
                        for table in extracted:
                            cleaned_table = []
                            for row in table:
                                cleaned_row = [str(cell) if cell is not None else "" for cell in row]
                                cleaned_table.append(cleaned_row)
                            cleaned_extracted.append(cleaned_table)
                        tables_by_page[page_num] = cleaned_extracted
                    else:
                        tables_by_page[page_num] = []
        except Exception as e:
            log_to_file(f"PDFParser.extract_tables: CRITICAL ERROR in extracting tables: {str(e)}")
            tables_by_page[-1] = []  # sentinel key: worker checks for -1 to detect partial failure
        return tables_by_page

    @staticmethod
    def rasterize_pages(pdf_path: str, out_dir: str, dpi: int = 250) -> List[str]:
        """
        Rasterizes each page of the PDF to a high-quality PNG structure inside out_dir.
        Uses pdftoppm for rapid, layout-native rendering.
        """
        os.makedirs(out_dir, exist_ok=True)
        prefix = os.path.join(out_dir, "page")
        
        try:
            # Run pdftoppm -png -r {dpi} {pdf_path} {prefix}
            subprocess.run(
                ["pdftoppm", "-png", "-r", str(dpi), pdf_path, prefix],
                check=True,
                capture_output=True
            )
        except Exception as e:
            raise RuntimeError(f"Failed to rasterize PDF using pdftoppm: {str(e)}")

        # Find and sort all generated page files
        all_files = os.listdir(out_dir)
        page_files = [f for f in all_files if f.startswith("page-") and f.endswith(".png")]
        # Sort files by numeric page indicator (e.g. page-01.png or page-1.png)
        page_files.sort(key=lambda x: [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', x)])
        
        return [os.path.join(out_dir, f) for f in page_files]

    @staticmethod
    def ocr_page(img_path: str) -> str:
        """
        Performs optical character recognition (OCR) using pytesseract.
        Uses PSM mode 1 (automatic page segmentation with OSD).
        Cleans extracted text to strip typical scanner watermarks.
        """
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"Page image not found: {img_path}")
        try:
            custom_config = r'--psm 1'
            text = pytesseract.image_to_string(Image.open(img_path), config=custom_config)
            return PDFParser._clean_page_text(text)
        except Exception as e:
            raise RuntimeError(f"OCR execution failed on {img_path}: {str(e)}")

    @staticmethod
    def ocr_page_layout(img_path: str) -> List[Dict[str, Any]]:
        """
        Extracts OCR layout data with bounding box coordinates and categories.
        Uses pytesseract's image_to_data function.
        """
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"Page image not found: {img_path}")
        
        blocks: List[Dict[str, Any]] = []
        try:
            data = pytesseract.image_to_data(Image.open(img_path), output_type=pytesseract.Output.DICT)
            n_boxes = len(data['level'])
            for i in range(n_boxes):
                text = data['text'][i].strip()
                if not text:
                    continue  # Ignore empty text elements
                
                # Retrieve bounding box metadata
                block = {
                    "text": text,
                    "left": data['left'][i],
                    "top": data['top'][i],
                    "width": data['width'][i],
                    "height": data['height'][i],
                    "conf": data['conf'][i],
                    "block_num": data['block_num'][i],
                    "line_num": data['line_num'][i],
                    "word_num": data['word_num'][i]
                }
                blocks.append(block)
        except Exception as e:
            raise RuntimeError(f"OCR layout extraction failed on {img_path}: {str(e)}")
        return blocks

    @staticmethod
    def _clean_page_text(text: str) -> str:
        """
        Cleans headers, footers, and page numbers/watermarks.
        For example: CamScanner or Adobe Acrobat default footer strings.
        """
        lines = text.splitlines()
        cleaned_lines = []
        for line in lines:
            s_line = line.strip()
            # Drop obvious footer / page numbering indicators
            if re.match(r'^page \d+ of \d+$', s_line, re.IGNORECASE):
                continue
            if re.match(r'^\d+$', s_line):  # Lone raw page digits
                continue
            # Drop famous watermarks
            if "scanned with camscanner" in s_line.lower():
                continue
            if "scanned by camscanner" in s_line.lower():
                continue
            if "camscanner" in s_line.lower():
                # Strip just the trademark part if embedded
                line = re.sub(r'(?i)scanned with camscanner', '', line)
                line = re.sub(r'(?i)scanned by camscanner', '', line)
                line = re.sub(r'(?i)camscanner', '', line)
            cleaned_lines.append(line)
        return "\n".join(cleaned_lines)
