import os
import shutil
import datetime
from typing import Dict, Any, List
from database import SessionLocal, Job
from engine.pdf_parser import PDFParser
from engine.image_extractor import ImageExtractor
from engine.image_describer import ImageDescriber
from engine.markdown_writer import MarkdownWriter

def log_to_file(message: str):
    """
    Writes persistent tracking logs to the shared output directory so host users can monitor real-time worker execution.
    """
    try:
        log_path = os.path.join(os.getenv("OUTPUT_DIR", "/app/output"), "docpilot_pipeline.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        timestamp = datetime.datetime.now().isoformat()
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass

class Pipeline:
    """
    Main pipeline orchestrator that processes a single PDF, detects whether it is scanned,
    runs either text layout extraction or page-by-page OCR, extracts high-resolution image assets,
    calls Groq vision description, and writes a standard Markdown conversion package.
    """

    @staticmethod
    def run(pdf_path: str, job_id: str, output_base_dir: str) -> Dict[str, Any]:
        """
        Orchestrates all four engine classes, reporting checkpoints and updating status
        and progress inside the SQLite database at each phase.
        Returns metadata summarizing the conversion results.
        """
        db = SessionLocal()
        log_to_file(f"--- STARTING PIPELINE RUN FOR JOB: {job_id} ---")
        log_to_file(f"Target PDF Path: {pdf_path}")
        
        try:
            # 1. Update status to parsing (15%)
            log_to_file("Phase 1: Status set to 'parsing' (15%)")
            Pipeline._update_db_status(db, job_id, status="parsing", progress=15)
            
            # Detect scanned vs native
            log_to_file("Calling PDFParser.is_scanned...")
            is_scanned = PDFParser.is_scanned(pdf_path)
            log_to_file(f"PDFParser.is_scanned result: {is_scanned}")
            
            pages_text: List[str] = []
            tables_by_page: Dict[int, List[Any]] = {}
            temp_raster_dir = os.path.join(output_base_dir, job_id, "temp_raster")

            if is_scanned:
                log_to_file("Scanned PDF detected. Initiating page rasterization via pdftoppm...")
                rastered_images = PDFParser.rasterize_pages(pdf_path, temp_raster_dir)
                log_to_file(f"Rasterized {len(rastered_images)} pages. Starting page OCR with Tesseract...")
                # Run OCR page-by-page
                for idx, img in enumerate(rastered_images):
                    log_to_file(f"Performing OCR on Page {idx + 1} of {len(rastered_images)}: {img}")
                    ocr_text = PDFParser.ocr_page(img)
                    pages_text.append(ocr_text)
                log_to_file("OCR parsing sequence completed.")
            else:
                log_to_file("Native layout PDF detected. Running direct pdftotext extraction...")
                pages_text = PDFParser.extract_text_pages(pdf_path)
                log_to_file(f"Extracted direct layout text for {len(pages_text)} pages.")
                
                log_to_file("Calling PDFParser.extract_tables via pdfplumber...")
                tables_by_page = PDFParser.extract_tables(pdf_path)
                log_to_file("Table structure extraction completed.")

            page_count = len(pages_text) or 1

            # 2. Update status to extracting_images (35%)
            log_to_file("Phase 2: Updating status to 'extracting_images' (35%)")
            Pipeline._update_db_status(db, job_id, status="extracting_images", progress=35)
            
            job_output_dir = os.path.join(output_base_dir, job_id)
            assets_dir = os.path.join(job_output_dir, "extracted_assets")
            
            # Extract high-definition images using pdfimages
            log_to_file("Extracting high-definition images via native pdfimages...")
            extracted_images = ImageExtractor.extract(pdf_path, assets_dir, page_count=page_count)
            image_count = len(extracted_images)
            log_to_file(f"Image extraction completed. Found {image_count} high-resolution image assets.")

            # 3. Update status to describing_images (40%)
            log_to_file("Phase 3: Updating status to 'describing_images' (40%)")
            Pipeline._update_db_status(db, job_id, status="describing_images", progress=40)
            
            descriptions: List[str] = []
            if image_count > 0:
                describer = ImageDescriber()
                for idx, (img_path, page_num) in enumerate(extracted_images):
                    log_to_file(f"Calling Groq vision describer model for image {idx + 1} of {image_count}: {img_path} (Page {page_num})")
                    desc = describer.describe(img_path)
                    descriptions.append(desc)
                    log_to_file(f"Received vision description for image {idx + 1}")
                    
                    # Update progress proportionally between 40% and 85%
                    prog = 40 + int(((idx + 1) / image_count) * 45)
                    Pipeline._update_db_status(db, job_id, status="describing_images", progress=prog)
            else:
                log_to_file("No image assets extracted. Advancing directly to 85%")
                # No images to describe, advance directly to 85%
                Pipeline._update_db_status(db, job_id, status="describing_images", progress=85)

            # 4. Update status to writing (90%)
            log_to_file("Phase 4: Updating status to 'writing' (90%)")
            Pipeline._update_db_status(db, job_id, status="writing", progress=90)
            
            source_filename = os.path.basename(pdf_path)
            
            # Assemble markdown page structure + tables, copy files to assets/, write document.md
            log_to_file("Assembling final document.md structure...")
            final_md_path = MarkdownWriter.write(
                pages_text=pages_text,
                tables_by_page=tables_by_page,
                image_paths=extracted_images,
                descriptions=descriptions,
                output_dir=job_output_dir,
                is_scanned=is_scanned,
                source_filename=source_filename
            )
            log_to_file(f"Final document.md compiled and saved to: {final_md_path}")

            # Cleanup temp raster page files to save local volume space
            if os.path.exists(temp_raster_dir):
                log_to_file("Cleaning up transient scanned raster page images...")
                try:
                    shutil.rmtree(temp_raster_dir)
                except OSError as r_err:
                    log_to_file(f"Warning: Non-blocking error cleaning up temp raster files: {str(r_err)}")
                    pass

            # 5. Pipeline completion (100%)
            log_to_file("Phase 5: Task fully completed. Refreshing status to 'completed' (100%)")
            Pipeline._update_db_status(
                db, 
                job_id, 
                status="completed", 
                progress=100, 
                output_path=job_output_dir
            )
            log_to_file("--- PIPELINE RUN FINISHED SUCCESS ---")

            return {
                "md_path": final_md_path,
                "assets_dir": os.path.join(job_output_dir, "assets"),
                "image_count": image_count,
                "page_count": page_count
            }

        except Exception as e:
            log_to_file(f"!!! CRITICAL EXCEPTION IN PIPELINE RUN: {str(e)}")
            import traceback
            log_to_file(traceback.format_exc())
            # Propagate error so that worker processes can handle fail state writing
            raise e
        finally:
            db.close()

    @staticmethod
    def _update_db_status(db, job_id: str, status: str, progress: int, output_path: str = None):
        """
        Internal utility helper to safely edit job state on SQLite.
        """
        job = db.query(Job).filter(Job.job_id == job_id).first()
        if job:
            job.status = status
            job.progress = progress
            if output_path:
                job.output_path = output_path
            db.commit()
            db.refresh(job)
