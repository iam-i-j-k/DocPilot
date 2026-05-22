import os
import shutil
from typing import List, Dict, Any


class MarkdownWriter:
    """
    Writer class responsible for compiling extracted document structures into standardized Markdown.
    Copies image assets, sets up metadata frontmatter, converts tabular structures,
    and renders images inline at their source page rather than at the bottom.
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

        # Zip descriptions with image_paths upfront so skipped images
        # don't shift the description index
        padded_descriptions = list(descriptions) + [""] * len(image_paths)

        for idx, ((src_path, page_num), desc) in enumerate(zip(image_paths, padded_descriptions)):
            if not os.path.exists(src_path):
                continue

            filename = os.path.basename(src_path)
            ext = os.path.splitext(filename)[1] or ".png"
            clean_filename = f"image_{idx + 1}{ext}"
            dest_path = os.path.join(assets_dest_dir, clean_filename)

            try:
                shutil.copy2(src_path, dest_path)
            except Exception as e:
                print(f"Non-blocking warning: Failed to copy {src_path} to {dest_path}: {e}")
                continue

            copied_images_info.append({
                "filename": clean_filename,
                "relative_path": f"./assets/{clean_filename}",
                "description": desc,
                "page_num": page_num
            })

        # Build page → images lookup for inline rendering
        images_by_page: Dict[int, List[Dict]] = {}
        for img_info in copied_images_info:
            p = img_info["page_num"]
            if p not in images_by_page:
                images_by_page[p] = []
            images_by_page[p].append(img_info)

        # ── Assemble Markdown ─────────────────────────────────────────────────

        md_lines = []

        # 1. YAML frontmatter
        md_lines.append("---")
        md_lines.append("docpilot_parser_node: V1.0")
        md_lines.append(f"source_file: {source_filename}")
        md_lines.append(f"is_scanned: {is_scanned}")
        md_lines.append(f"total_pages: {len(pages_text)}")
        md_lines.append(f"total_images: {len(copied_images_info)}")
        md_lines.append("---")
        md_lines.append("")

        # 2. Title
        md_lines.append(f"# {source_filename}")
        md_lines.append("This file was automatically generated and parsed via DocPilot pipeline.")
        md_lines.append("")

        # 3. Page-by-page assembly — text, tables, then inline images
        for page_idx, raw_text in enumerate(pages_text):
            page_num = page_idx + 1
            md_lines.append(f"## Page {page_num}")
            md_lines.append("")

            # Page body text
            if raw_text.strip():
                md_lines.append(raw_text)
            else:
                md_lines.append("*[Page layout contains only empty space or non-textual elements]*")
            md_lines.append("")

            # Tables extracted on this page
            tables = tables_by_page.get(page_num, [])
            if tables:
                md_lines.append("### Tables Extracted")
                for table_idx, tbl in enumerate(tables):
                    md_lines.append(f"#### Table {table_idx + 1}")
                    md_lines.append(MarkdownWriter._list_to_md_table(tbl))
                    md_lines.append("")

            # Images extracted from this page — rendered inline
            page_images = images_by_page.get(page_num, [])
            if page_images:
                md_lines.append("### Page Images")
                md_lines.append("")
                for fig_num, img in enumerate(page_images, start=1):
                    md_lines.append(f"![Figure {fig_num} — Page {page_num}]({img['relative_path']})")
                    if img["description"]:
                        md_lines.append(f"> **Figure {fig_num} (Page {page_num}):** {img['description']}")
                    md_lines.append("")

        # 4. Write to disk
        output_md_path = os.path.join(output_dir, "document.md")
        with open(output_md_path, "w", encoding="utf-8") as md_file:
            md_file.write("\n".join(md_lines) + "\n")

        return output_md_path

    @staticmethod
    def _list_to_md_table(table_data: List[List[str]]) -> str:
        """
        Converts a 2D array of strings into a standard Markdown table.
        Handles ragged rows (too few or too many columns) and None cells.
        """
        if not table_data or not table_data[0]:
            return ""

        headers = table_data[0]
        rows = table_data[1:]

        cleaned_headers = [
            str(c).replace("\n", " ").strip() if c is not None else ""
            for c in headers
        ]

        header_row = "| " + " | ".join(cleaned_headers) + " |"
        separator_row = "| " + " | ".join(["---"] * len(cleaned_headers)) + " |"

        md_rows = [header_row, separator_row]

        for r in rows:
            if len(r) < len(headers):
                r = list(r) + [""] * (len(headers) - len(r))
            elif len(r) > len(headers):
                r = r[:len(headers)]

            cleaned_row = [
                str(c).replace("\n", " ").strip() if c is not None else ""
                for c in r
            ]
            md_rows.append("| " + " | ".join(cleaned_row) + " |")

        return "\n".join(md_rows) + "\n"