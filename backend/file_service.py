import os
import shutil
import uuid
from pathlib import Path

WORKSPACE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'workspace')
os.makedirs(WORKSPACE, exist_ok=True)


def _safe_path(filename: str) -> Path:
    abs_path = os.path.abspath(os.path.join(WORKSPACE, filename))
    if not abs_path.startswith(os.path.abspath(WORKSPACE)):
        raise ValueError("Path traversal detected")
    return Path(abs_path)


def save_upload(file_bytes: bytes, original_name: str) -> dict:
    ext = os.path.splitext(original_name)[1]
    file_id = str(uuid.uuid4())[:8]
    safe_name = f"{file_id}{ext}"
    path = _safe_path(safe_name)
    path.write_bytes(file_bytes)
    return {
        "file_id": file_id,
        "name": original_name,
        "saved_as": safe_name,
        "size": len(file_bytes),
        "path": str(path),
    }


def get_file_path(file_id: str) -> Path | None:
    for f in os.listdir(WORKSPACE):
        if f.startswith(file_id):
            return Path(os.path.join(WORKSPACE, f))
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


def delete_file(file_id: str) -> bool:
    path = get_file_path(file_id)
    if path and path.exists():
        path.unlink()
        return True
    return False


def create_pdf(content: str, name: str = "report.pdf") -> str:
    try:
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Report", ln=True, align="C")
        pdf.ln(5)
        pdf.set_font("Helvetica", "", 11)
        for line in content.split('\n'):
            line = line.strip()
            if not line:
                pdf.ln(3)
                continue
            safe = line.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 6, safe)
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
