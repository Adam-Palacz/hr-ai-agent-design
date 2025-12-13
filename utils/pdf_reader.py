"""Utility functions for reading PDF files using LLM Vision as OCR."""
from typing import Optional, List
import base64
from pathlib import Path
import PyPDF2
import time
from core.logger import logger

# Check for pdf2image
try:
    from pdf2image import convert_from_path, convert_from_bytes
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

# Check for PyMuPDF
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


def _pdf_to_images_pdf2image(pdf_path: str) -> List[bytes]:
    """Convert PDF to images using pdf2image."""
    from pdf2image import convert_from_path
    
    images = convert_from_path(pdf_path, dpi=300)
    image_bytes_list = []
    
    for img in images:
        from io import BytesIO
        buf = BytesIO()
        img.save(buf, format='PNG')
        image_bytes_list.append(buf.getvalue())
    
    return image_bytes_list


def _pdf_to_images_pymupdf(pdf_path: str) -> List[bytes]:
    """Convert PDF to images using PyMuPDF."""
    import fitz  # PyMuPDF
    
    doc = fitz.open(pdf_path)
    image_bytes_list = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        # Render page to image (pixmap)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
        # Convert to PNG bytes
        image_bytes = pix.tobytes("png")
        image_bytes_list.append(image_bytes)
    
    doc.close()
    return image_bytes_list


def pdf_to_images(pdf_path: str) -> List[bytes]:
    """
    Convert PDF pages to images.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        List of image bytes (one per page)
    """
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    # Try pdf2image first, then PyMuPDF
    if PDF2IMAGE_AVAILABLE:
        try:
            return _pdf_to_images_pdf2image(str(pdf_path))
        except Exception as e:
            if PYMUPDF_AVAILABLE:
                return _pdf_to_images_pymupdf(str(pdf_path))
            raise Exception(f"Failed to convert PDF to images: {str(e)}")
    elif PYMUPDF_AVAILABLE:
        return _pdf_to_images_pymupdf(str(pdf_path))
    else:
        raise ImportError(
            "Neither pdf2image nor PyMuPDF is installed. "
            "Please install one: pip install pdf2image or pip install pymupdf"
        )


def extract_text_from_pdf_with_ocr(
    pdf_path: str,
    vision_model,
    use_ocr: bool = True,
    verbose: bool = False
) -> str:
    """
    Extract text from PDF using LLM Vision model as OCR.
    
    Args:
        pdf_path: Path to the PDF file
        vision_model: LangChain ChatOpenAI vision model instance
        use_ocr: If True, use vision model for OCR. If False, try text extraction first.
        
    Returns:
        Extracted text content as string
    """
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    # First, try to extract text directly (for text-based PDFs)
    if not use_ocr:
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text_content = []
                
                for page_num, page in enumerate(pdf_reader.pages):
                    text = page.extract_text()
                    if text.strip():
                        text_content.append(f"--- Page {page_num + 1} ---\n{text}")
                
                extracted_text = "\n\n".join(text_content)
                # If we got substantial text, return it
                if len(extracted_text.strip()) > 100:
                    return extracted_text
        except Exception:
            pass  # Fall through to OCR
    
    # Convert PDF to images
    logger.info("Starting OCR process: Converting PDF to images")
    ocr_start_time = time.time()
    
    if verbose:
        print("  🖼️ Converting PDF to images...")
    
    try:
        image_conversion_start = time.time()
        image_bytes_list = pdf_to_images(str(pdf_path))
        image_conversion_time = time.time() - image_conversion_start
        logger.info(f"PDF converted to {len(image_bytes_list)} images in {image_conversion_time:.2f}s")
        
        if verbose:
            print(f"  ✅ Converted {len(image_bytes_list)} pages to images ({image_conversion_time:.2f}s)")
    except Exception as e:
        logger.error(f"Failed to convert PDF to images: {str(e)}")
        raise Exception(f"Failed to convert PDF to images: {str(e)}")
    
    # Use vision model to extract text from each page
    text_content = []
    ocr_prompt = """Extract all text from this CV/resume image. 
    Preserve the structure, formatting, and layout as much as possible.
    Include all sections: personal information, summary, education, experience, skills, certifications, etc.
    Return the extracted text exactly as it appears, maintaining line breaks and structure."""
    
    try:
        from langchain_core.messages import HumanMessage
        
        total_pages = len(image_bytes_list)
        logger.info(f"Starting OCR processing for {total_pages} page(s)")
        
        for page_num, image_bytes in enumerate(image_bytes_list):
            page_start_time = time.time()
            
            if verbose:
                print(f"  🔍 OCR page {page_num + 1}/{total_pages}...")
            
            logger.info(f"Processing page {page_num + 1}/{total_pages} with vision model")
            
            # Encode image to base64
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            image_size_kb = len(image_bytes) / 1024
            logger.debug(f"Page {page_num + 1}: Image size {image_size_kb:.2f} KB, base64 length: {len(base64_image)}")
            
            # Create message with image
            message = HumanMessage(
                content=[
                    {"type": "text", "text": ocr_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        }
                    }
                ]
            )
            
            # Get response from vision model
            if verbose:
                print(f"    ⏳ Sending to vision model (this may take 10-30 seconds per page)...")
            
            logger.info(f"Sending page {page_num + 1} to vision model...")
            vision_request_start = time.time()
            
            response = vision_model.invoke([message])
            vision_request_time = time.time() - vision_request_start
            
            page_text = response.content if hasattr(response, 'content') else str(response)
            page_processing_time = time.time() - page_start_time
            
            logger.info(f"Page {page_num + 1} OCR completed: {len(page_text)} characters in {page_processing_time:.2f}s (vision: {vision_request_time:.2f}s)")
            
            if page_text.strip():
                text_content.append(f"--- Page {page_num + 1} ---\n{page_text}")
                if verbose:
                    print(f"    ✅ Extracted {len(page_text)} characters from page {page_num + 1} ({page_processing_time:.2f}s)")
        
        result = "\n\n".join(text_content) if text_content else ""
        total_ocr_time = time.time() - ocr_start_time
        
        logger.info(f"OCR completed: {len(result)} total characters in {total_ocr_time:.2f}s")
        
        if verbose:
            print(f"  ✅ OCR completed. Total {len(result)} characters ({total_ocr_time:.2f}s)")
        
        return result
    
    except Exception as e:
        logger.error(f"Error extracting text with vision model: {type(e).__name__}: {str(e)}", exc_info=True)
        raise Exception(f"Error extracting text with vision model: {str(e)}")


def extract_text_from_pdf(pdf_path: str, vision_model=None, use_ocr: bool = True, verbose: bool = False) -> str:
    """
    Extract text content from a PDF file.
    Uses vision model as OCR if provided, otherwise tries text extraction.
    
    Args:
        pdf_path: Path to the PDF file
        vision_model: Optional vision model for OCR (ChatOpenAI with vision capabilities)
        use_ocr: If True and vision_model provided, use OCR. Otherwise try text extraction first.
        
    Returns:
        Extracted text content as string
        
    Raises:
        FileNotFoundError: If PDF file doesn't exist
        Exception: If PDF reading fails
    """
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    # First, try to extract text directly (for text-based PDFs)
    # Only use OCR if explicitly requested or if text extraction fails
    text_content = []
    
    logger.info("Starting text extraction from PDF (standard method)")
    if verbose:
        print("  📖 Attempting to extract text from PDF...")
    
    try:
        text_extraction_start = time.time()
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            num_pages = len(pdf_reader.pages)
            
            logger.info(f"PDF opened successfully: {num_pages} page(s)")
            if verbose:
                print(f"  📄 PDF has {num_pages} page(s)")
            
            for page_num, page in enumerate(pdf_reader.pages):
                if verbose and num_pages > 5 and (page_num + 1) % 5 == 0:
                    print(f"  ⏳ Processing page {page_num + 1}/{num_pages}...")
                
                text = page.extract_text()
                if text.strip():
                    text_content.append(f"--- Page {page_num + 1} ---\n{text}")
            
            extracted_text = "\n\n".join(text_content)
            text_extraction_time = time.time() - text_extraction_start
            
            logger.info(f"Text extraction completed: {len(extracted_text)} characters in {text_extraction_time:.2f}s")
            if verbose:
                print(f"  ✅ Extracted {len(extracted_text)} characters of text ({text_extraction_time:.2f}s)")
            
            # If we got substantial text, return it (don't use OCR)
            if len(extracted_text.strip()) > 100:
                logger.info("Sufficient text extracted, skipping OCR")
                return extracted_text
            
            # If we got little text and OCR is enabled, try OCR
            if len(extracted_text.strip()) < 100 and vision_model and use_ocr:
                logger.warning(f"Too little text extracted ({len(extracted_text.strip())} chars), switching to OCR")
                if verbose:
                    print("  🔍 Too little text, switching to OCR...")
                return extract_text_from_pdf_with_ocr(pdf_path, vision_model, use_ocr=True, verbose=verbose)
            
            if len(extracted_text.strip()) < 50:
                raise Exception("Failed to extract text from PDF")
            
            return extracted_text
    
    except Exception as e:
        logger.warning(f"Text extraction failed: {type(e).__name__}: {str(e)}")
        # If text extraction fails and vision model is available, try OCR
        if vision_model and use_ocr:
            logger.info("Falling back to OCR method")
            if verbose:
                print(f"  ⚠️ Text extraction error: {str(e)}")
                print("  🔍 Switching to OCR...")
            return extract_text_from_pdf_with_ocr(pdf_path, vision_model, use_ocr=True, verbose=verbose)
        logger.error(f"Text extraction failed and OCR not available: {str(e)}")
        raise Exception(f"Error reading PDF file: {str(e)}")


def extract_text_from_pdf_bytes(pdf_bytes: bytes, vision_model=None) -> str:
    """
    Extract text content from PDF bytes.
    
    Args:
        pdf_bytes: PDF file content as bytes
        vision_model: Optional vision model for OCR
        
    Returns:
        Extracted text content as string
    """
    from io import BytesIO
    import tempfile
    import os
    
    # Save to temporary file and process
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_file.write(pdf_bytes)
        tmp_path = tmp_file.name
    
    try:
        return extract_text_from_pdf(tmp_path, vision_model=vision_model)
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

