"""Keep generated report variants synchronized with the current implementation appendix."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from xml.etree import ElementTree as ET

WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{" + WORD_NS + "}"


def append_current_implementation_status(output_path: str) -> None:
    """Append Appendix IV from OG.docx to a generated report if it is absent."""
    output = Path(output_path)
    source = output.with_name("OG.docx")
    if not source.exists() or not output.exists():
        raise FileNotFoundError(
            f"Report synchronization requires both {source} and {output}."
        )

    with ZipFile(source) as source_zip:
        source_root = ET.fromstring(source_zip.read("word/document.xml"))
        source_body = source_root.find(W + "body")
        if source_body is None:
            raise ValueError(f"Missing document body in {source}.")
        appendix = []
        found = False
        for child in list(source_body):
            text = "".join(node.text or "" for node in child.iter(W + "t"))
            if "APPENDIX - IV" in text:
                found = True
            if found and child.tag != W + "sectPr":
                appendix.append(child)
        if not appendix:
            raise ValueError(f"Appendix IV was not found in {source}.")

    with ZipFile(output) as output_zip:
        root = ET.fromstring(output_zip.read("word/document.xml"))
        body = root.find(W + "body")
        if body is None:
            raise ValueError(f"Missing document body in {output}.")
        existing_text = "".join(node.text or "" for node in body.iter(W + "t"))
        if "APPENDIX - IV" in existing_text:
            return

        sect_pr = body.find(W + "sectPr")
        insert_at = list(body).index(sect_pr) if sect_pr is not None else len(body)
        for offset, element in enumerate(appendix):
            body.insert(insert_at + offset, element)

        document_xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        entries = {
            name: output_zip.read(name)
            for name in output_zip.namelist()
            if name != "word/document.xml"
        }

    with ZipFile(output, "w", ZIP_DEFLATED) as output_zip:
        for name, data in entries.items():
            output_zip.writestr(name, data)
        output_zip.writestr("word/document.xml", document_xml)
