import os
import uuid
from pathlib import Path

WORKSPACE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'workspace')
os.makedirs(WORKSPACE, exist_ok=True)

TEXT_EXTS = {'txt', 'md', 'py', 'js', 'ts', 'jsx', 'tsx', 'json', 'csv', 'html', 'css', 'xml', 'yaml', 'yml', 'ini', 'cfg', 'log', 'sh', 'bat', 'ps1', 'env', 'rst', 'tex', 'c', 'cpp', 'h', 'java', 'rs', 'go', 'rb', 'php', 'swift', 'kt', 'scala', 'sql', 'r', 'lua'}


def _safe_path(filename: str) -> Path:
    abs_path = os.path.abspath(os.path.join(WORKSPACE, filename))
    if not abs_path.startswith(os.path.abspath(WORKSPACE)):
        raise ValueError("Path traversal detected")
    return Path(abs_path)


def _extract_text_from_pdf(path: Path) -> str:
    try:
        import PyPDF2
        text = ""
        with open(path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text.strip()
    except ImportError:
        return "[PDF text extraction requires PyPDF2]"
    except Exception as e:
        return f"[PDF extraction error: {e}]"


def _extract_text_from_docx(path: Path) -> str:
    try:
        from docx import Document
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs).strip()
    except ImportError:
        return "[DOCX text extraction requires python-docx]"
    except Exception as e:
        return f"[DOCX extraction error: {e}]"


def extract_text(file_path: str) -> str | None:
    path = _safe_path(file_path)
    if not path.exists():
        return None
    ext = path.suffix.lower().lstrip('.')
    if ext == 'pdf':
        return _extract_text_from_pdf(path)
    if ext == 'docx':
        return _extract_text_from_docx(path)
    if ext in TEXT_EXTS:
        try:
            return path.read_text(encoding='utf-8').strip()
        except Exception:
            return None
    return None


def save_upload(file_bytes: bytes, original_name: str) -> dict:
    safe_name = os.path.basename(original_name)
    if not safe_name:
        safe_name = f"unnamed_{uuid.uuid4()[:8]}"
    path = _safe_path(safe_name)
    path.write_bytes(file_bytes)
    size = len(file_bytes)
    text = extract_text(safe_name)
    result = {
        "file_id": safe_name,
        "name": safe_name,
        "saved_as": safe_name,
        "size": size,
        "path": str(path),
    }
    if text:
        result["extracted_text"] = text
    return result


def get_file_path(filename: str) -> Path | None:
    path = _safe_path(filename)
    if path.exists():
        return path
    return None


def read_file_content(filename: str) -> str:
    path = _safe_path(filename)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filename}")
    return path.read_text(encoding='utf-8')


def write_file_content(filename: str, content: str) -> str:
    path = _safe_path(filename)
    path.write_text(content, encoding='utf-8')
    return str(path)


def list_files() -> list[dict]:
    files = []
    for f in sorted(os.listdir(WORKSPACE)):
        fp = os.path.join(WORKSPACE, f)
        if os.path.isfile(fp):
            files.append({
                "name": f,
                "size": os.path.getsize(fp),
                "modified": os.path.getmtime(fp),
            })
    return files


def delete_file(filename: str) -> bool:
    try:
        path = _safe_path(filename)
        if path.exists():
            path.unlink()
            return True
    except ValueError:
        pass
    return False


def _safe_pdf_line(line: str, max_len: int = 80) -> str:
    """Break long unbreakable segments so FPDF2 multi_cell doesn't crash."""
    result = []
    for word in line.split(' '):
        while len(word) > max_len:
            result.append(word[:max_len])
            word = word[max_len:]
        result.append(word)
    return ' '.join(result)


def create_pdf(content: str, name: str = "report.pdf") -> str:
    try:
        from fpdf import FPDF
        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.set_left_margin(20)
        pdf.set_right_margin(20)
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.set_font("Helvetica", "B", 18)
        pdf.multi_cell(0, 10, "Report", align="C")
        pdf.ln(4)
        pdf.set_font("Helvetica", "", 10)
        for line in content.split('\n'):
            line = line.strip()
            if not line:
                pdf.ln(2)
                continue
            safe = _safe_pdf_line(line).encode('latin-1', 'replace').decode('latin-1')
            try:
                pdf.multi_cell(0, 5, safe)
            except RuntimeError as e:
                pdf.ln(2)
                continue
        path = os.path.join(WORKSPACE, name)
        pdf.output(path)
        return name
    except ImportError:
        raise RuntimeError("fpdf2 not installed")


def create_docx(content: str, name: str = "report.docx") -> str:
    try:
        from docx import Document
        doc = Document()
        doc.add_heading('Report', 0)
        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue
            if line.startswith('**') and line.endswith('**'):
                doc.add_heading(line.strip('*'), 2)
            elif line.startswith('- ') or line.startswith('* '):
                doc.add_paragraph(line[2:], style='List Bullet')
            elif line.startswith('# '):
                doc.add_heading(line[2:], 1)
            elif line.startswith('## '):
                doc.add_heading(line[2:], 2)
            elif line.startswith('### '):
                doc.add_heading(line[3:], 3)
            else:
                doc.add_paragraph(line)
        path = os.path.join(WORKSPACE, name)
        doc.save(path)
        return name
    except ImportError:
        raise RuntimeError("python-docx not installed")


def create_txt(content: str, name: str = "report.txt") -> str:
    path = os.path.join(WORKSPACE, name)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return name
