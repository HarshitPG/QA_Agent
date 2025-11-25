import json
import markdown
import fitz 
from bs4 import BeautifulSoup


def parse_pdf(file_bytes: bytes) -> str:
    try:
        import fitz
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text.strip()
    except Exception:
        try:
            return file_bytes.decode(errors="ignore")
        except Exception:
            return ""


def parse_markdown(file_bytes: bytes) -> str:
    md_str = file_bytes.decode("utf-8")
    html = markdown.markdown(md_str)
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator="\n").strip()


def parse_txt(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8").strip()


def parse_json(file_bytes: bytes) -> str:
    data = json.loads(file_bytes.decode("utf-8"))
    return json.dumps(data, indent=4)


def parse_html(file_bytes: bytes) -> str:
    html_str = file_bytes.decode("utf-8")
    soup = BeautifulSoup(html_str, "html.parser")

    visible_text = soup.get_text(separator="\n")

    structure = []
    for tag in soup.find_all():
        if tag.name in ["input", "button"]:
            structure.append(str(tag))

    html_metadata = "\n".join(structure)

    final = f"TEXT:\n{visible_text}\n\nSTRUCTURE:\n{html_metadata}"
    return final.strip()

def extract_text_from_file(filename: str, file_bytes: bytes) -> str:
    ext = filename.lower().split(".")[-1]

    if ext == "pdf":
        return parse_pdf(file_bytes)

    if ext == "md":
        return parse_markdown(file_bytes)

    if ext == "txt":
        return parse_txt(file_bytes)

    if ext == "json":
        return parse_json(file_bytes)

    if ext == "html":
        return parse_html(file_bytes)

    raise ValueError(f"Unsupported file type: {ext}")
