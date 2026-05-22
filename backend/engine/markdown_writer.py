import os
import shutil
from typing import List, Dict, Any

class MarkdownWriter:
    """
    Writer class responsible for compiling extracted document structures into standardized Markdown.
    Copies image assets, sets up metadata frontmatter, converts tabular structures,
    and formats descriptions as blockquotes inside the final Markdown layout.
    """

    @staticmethod
    def write(
        pages_text: List[str],
        tables_by_page: Dict[int, List[List[Any]]],
        image_paths: List[tuple[str, int]],
        descriptions: List[str],
        output_dir: str,
        is_scanned: bool,
        source_filename: str = "Document"
    ) -> str:
        """
        Assembles a comprehensive Markdown file inside output_dir and places all referenced 
        images into a local assets/ directory.
        Returns the absolute path to the generated .md index file.
        """
        os.makedirs(output_dir, exist_ok=True)
        assets_dest_dir = os.path.join(output_dir, "assets")
        os.makedirs(assets_dest_dir, exist_ok=True)

        copied_images_info = []

        # Copy the filtered images into the document's local assets directory
        for idx, (src_path, page_num) in enumerate(image_paths):
            if not os.path.exists(src_path):
                continue
            
            filename = os.path.basename(src_path)
            # Give it a clean name prefix
            ext = os.path.splitext(filename)[1] or ".png"
            clean_filename = f"image_{idx + 1}{ext}"
            dest_path = os.path.join(assets_dest_dir, clean_filename)
            
            try:
                shutil.copy2(src_path, dest_path)
            except Exception as e:
                print(f"Non-blocking warning: Failed to copy {src_path} to {dest_path}: {e}")
                continue
            
            # Map description
            desc = descriptions[idx] if idx < len(descriptions) else ""
            copied_images_info.append({
                "filename": clean_filename,
                "relative_path": f"./assets/{clean_filename}",
                "description": desc,
                "page_num": page_num
            })

        # Assemble Markdown Content
        md_lines = []
        
        # 1. YAML Metadata frontmatter
        md_lines.append("---")
        md_lines.append("docpilot_parser_node: V1.0")
        md_lines.append(f"source_file: {source_filename}")
        md_lines.append(f"is_scanned: {is_scanned}")
        md_lines.append(f"total_pages: {len(pages_text)}")
        md_lines.append(f"total_images: {len(copied_images_info)}")
        md_lines.append("---")
        md_lines.append("")

        # Header Title
        md_lines.append(f"# {source_filename}")
        md_lines.append("This file was automatically generated and parsed via DocPilot pipeline.")
        md_lines.append("")

        # 2. Page-by-page output assembly
        for page_idx, raw_text in enumerate(pages_text):
            page_num = page_idx + 1
            md_lines.append(f"## Page {page_num}")
            md_lines.append("")

            # Render Page body
            if raw_text.strip():
                md_lines.append(raw_text)
            else:
                md_lines.append("*[Page layout contains only empty space or non-textual elements]*")
            md_lines.append("")

            # Render tables extracted on this page
            tables = tables_by_page.get(page_num, [])
            if tables:
                md_lines.append("### Tables Extracted")
                for table_idx, tbl in enumerate(tables):
                    md_lines.append(f"#### Table {table_idx + 1}")
                    md_lines.append(MarkdownWriter._list_to_md_table(tbl))
                    md_lines.append("")

        # 3. Dedicated Extracted Images section at the end
        if copied_images_info:
            md_lines.append("## Extracted Images")
            md_lines.append("")
            for idx, img in enumerate(copied_images_info):
                md_lines.append(f"![Figure {idx + 1} — Page {img['page_num']}]({img['relative_path']})")
                if img['description']:
                    md_lines.append(f"> **Figure {idx + 1} (Page {img['page_num']}):** {img['description']}")
                md_lines.append("")

        # Write lines to file
        output_md_path = os.path.join(output_dir, "document.md")
        with open(output_md_path, "w", encoding="utf-8") as md_file:
            md_file.write("\n".join(md_lines) + "\n")

        return output_md_path

    @staticmethod
    def _list_to_md_table(table_data: List[List[str]]) -> str:
        """
        Converts a 2D array of strings into standard Markdown tabbed block grids.
        """
        if not table_data or not table_data[0]:
            return ""

        headers = table_data[0]
        rows = table_data[1:]

        # Every cell must go through: str(c).replace('\n', ' ').strip() if c is not None else ''
        cleaned_headers = [str(c).replace('\n', ' ').strip() if c is not None else '' for c in headers]

        # Handle formatting
        header_row = "| " + " | ".join(cleaned_headers) + " |"
        separator_row = "| " + " | ".join(["---"] * len(cleaned_headers)) + " |"
        
        md_rows = [header_row, separator_row]
        for r in rows:
            # Ensure row matches headers length
            if len(r) < len(headers):
                r = list(r) + [""] * (len(headers) - len(r))
            elif len(r) > len(headers):
                r = r[:len(headers)]
            
            cleaned_row = [str(c).replace('\n', ' ').strip() if c is not None else '' for c in r]
            md_rows.append("| " + " | ".join(cleaned_row) + " |")

        return "\n".join(md_rows) + "\n"
