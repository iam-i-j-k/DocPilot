import os
import shutil
from typing import Dict, Any, List
from database import SessionLocal, Job
from engine.pdf_parser import PDFParser
from engine.image_extractor import ImageExtractor
from engine.image_describer import ImageDescriber
from engine.markdown_writer import MarkdownWriter

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
        
        try:
            # 1. Update status to parsing (15%)
            Pipeline._update_db_status(db, job_id, status="parsing", progress=15)
            
            # Detect scanned vs native
            is_scanned = PDFParser.is_scanned(pdf_path)
            
            pages_text: List[str] = []
            tables_by_page: Dict[int, List[Any]] = {}
            temp_raster_dir = os.path.join(output_base_dir, job_id, "temp_raster")

            if is_scanned:
                # Scanned PDF: Rasterize the pages to PNG first
                rastered_images = PDFParser.rasterize_pages(pdf_path, temp_raster_dir)
                # Run OCR page-by-page
                for img in rastered_images:
                    ocr_text = PDFParser.ocr_page(img)
                    pages_text.append(ocr_text)
            else:
                # Native PDF: Extract layout-preserved text directly
                pages_text = PDFParser.extract_text_pages(pdf_path)
                # Extract structured tabular arrays
                tables_by_page = PDFParser.extract_tables(pdf_path)

            page_count = len(pages_text) or 1

            # 2. Update status to extracting_images (35%)
            Pipeline._update_db_status(db, job_id, status="extracting_images", progress=35)
            
            job_output_dir = os.path.join(output_base_dir, job_id)
            assets_dir = os.path.join(job_output_dir, "extracted_assets")
            
            # Extract high-definition images using pdfimages
            extracted_images = ImageExtractor.extract(pdf_path, assets_dir)
            image_count = len(extracted_images)

            # 3. Update status to describing_images (40%)
            Pipeline._update_db_status(db, job_id, status="describing_images", progress=40)
            
            descriptions: List[str] = []
            if image_count > 0:
                describer = ImageDescriber()
                for idx, img_path in enumerate(extracted_images):
                    desc = describer.describe(img_path)
                    descriptions.append(desc)
                    
                    # Update progress proportionally between 40% and 85%
                    prog = 40 + int(((idx + 1) / image_count) * 45)
                    Pipeline._update_db_status(db, job_id, status="describing_images", progress=prog)
            else:
                # No images to describe, advance directly to 85%
                Pipeline._update_db_status(db, job_id, status="describing_images", progress=85)

            # 4. Update status to writing (90%)
            Pipeline._update_db_status(db, job_id, status="writing", progress=90)
            
            # Assemble markdown page structure + tables, copy files to assets/, write document.md
            final_md_path = MarkdownWriter.write(
                pages_text=pages_text,
                tables_by_page=tables_by_page,
                image_paths=extracted_images,
                descriptions=descriptions,
                output_dir=job_output_dir,
                is_scanned=is_scanned
            )

            # Cleanup temp raster page files to save local volume space
            if os.path.exists(temp_raster_dir):
                try:
                    shutil.rmtree(temp_raster_dir)
                except OSError:
                    pass

            # 5. Pipeline completion (100%)
            Pipeline._update_db_status(
                db, 
                job_id, 
                status="completed", 
                progress=100, 
                output_path=job_output_dir
            )

            return {
                "md_path": final_md_path,
                "assets_dir": os.path.join(job_output_dir, "assets"),
                "image_count": image_count,
                "page_count": page_count
            }

        except Exception as e:
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
