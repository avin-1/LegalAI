import fitz
import os

def extract(userid: int, base_upload_dir: str = 'upload'):
    """
    Extracts text from PDF files in a specified directory corresponding to a given user ID
    and writes the extracted text to an output file.

    :param userid: The user ID as an integer.
    :param base_upload_dir: The base directory where user folders are located.
    """
    # Convert userid to string for path creation
    userid_str = str(userid)
    
    # Define the specific directory path for the user
    dir_path = os.path.join(base_upload_dir, userid_str)
    
    # Ensure the directory exists before proceeding
    if not os.path.isdir(dir_path):
        print(f"Error: User directory not found at {dir_path}")
        return

    # Define the output file path
    output_path = os.path.join(dir_path, 'output.txt')

    try:
        # Open the output file in write mode with UTF-8 encoding
        with open(output_path, 'w', encoding='utf-8') as out:
            # Iterate over files in the directory
            for filename in os.listdir(dir_path):
                # Check if the file is a PDF
                if filename.lower().endswith('.pdf'):
                    pdf_path = os.path.join(dir_path, filename)
                    
                    # Ensure it's actually a file and not a subdirectory named like a PDF
                    if os.path.isfile(pdf_path):
                        try:
                            # Open the PDF document using fitz
                            with fitz.open(pdf_path) as doc:
                                for page in doc:
                                    # Extract text from each page and write to the output file
                                    out.write(page.get_text() + '\n')
                            print(f"Successfully processed {filename}")
                        except Exception as e:
                            print(f"Error processing PDF file {filename}: {e}")
            print(f"Text extraction complete. Output written to {output_path}")

    except IOError as e:
        print(f"Error handling file operation: {e}")

