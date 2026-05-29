import os

# Pymupdf was creating too much hurdle so i did safety check before importing
try:
    import pymupdf.layout
except ImportError:
    print("Warning: pymupdf.layout not found, to_text might fail.")

# 
import pymupdf4llm as pm          
import docx                       

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
# Use SPACE_ID to detect HuggingFace Spaces — os.path.exists('/data') is unreliable on Windows
if os.environ.get('SPACE_ID'):
    UPLOADS_ROOT = "/data/uploads"
else:
    UPLOADS_ROOT = os.path.join(PROJECT_ROOT, "uploads")

def extract_user_docs(user_id: str):
    os.makedirs(os.path.join(UPLOADS_ROOT, user_id), exist_ok=True)
    user_dir = os.path.join(UPLOADS_ROOT, user_id)
    
    if not os.path.exists(user_dir):
        return f"Error: Directory for user {user_id} does not exist at {user_dir}"

    output_path = os.path.join(user_dir, "output.txt")
    collected = []

    print(f"[extract] Scanning {user_dir}: {os.listdir(user_dir)}")
    for name in os.listdir(user_dir):
        path = os.path.join(user_dir, name)
        
        # Skip directories and the output file itself
        if not os.path.isfile(path) or name == "output.txt":
            continue

        ext = os.path.splitext(name)[1].lower()
        text = ""

        try:
            # PyMuPDF4LLM handles PDF, EPUB, and many others natively
            # It converts them to clean Markdown to preserve structure
            if ext in {".pdf", ".epub", ".xps", ".fb2", ".cbz"}:
                text = pm.to_text(path)

            # DOCX processing
            elif ext == ".docx":
                d = docx.Document(path)
                text = "\n".join(p.text for p in d.paragraphs)

            # Plain text files
            elif ext == ".txt":
                with open(path, "r", encoding="utf-8") as f:
                    text = f.read()

            else:
                # if unsupported type — skip
                continue

            collected.append(f"===== {name} =====\n{text}\n")
            print(f"Successfully processed: {name}")

        except Exception as e:
            collected.append(f"===== {name} (ERROR) =====\n{str(e)}\n")
            print(f"Error processing {name}: {e}")

    print(f"[extract] Writing {len(collected)} chunks to {output_path}")
    if not collected:
        print("Warning: No content collected from files!")
        
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(collected))

    return output_path

