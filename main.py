from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
import os
from pathlib import Path
from datetime import datetime

app = FastAPI(title="File Storage API", version="1.0.0")

# Directory where files will be stored
STORAGE_DIR = Path("storage")
STORAGE_DIR.mkdir(exist_ok=True)


# Counter for files stored (initialize with existing files count)
def get_file_count():
    return len([f for f in STORAGE_DIR.iterdir() if f.is_file()])


files_stored_counter = get_file_count()


@app.get("/")
async def root():
    return {
        "message": "File Storage API",
        "endpoints": [
            "GET /files/{filename}",
            "POST /files",
            "GET /files",
            "GET /health",
            "GET /metrics",
        ],
    }


@app.get("/files/{filename}")
async def get_file(filename: str):
    """
    Retrieve a file by filename.

    Args:
        filename: Name of the file to retrieve

    Returns:
        FileResponse with the requested file

    Raises:
        HTTPException: If file is not found
    """
    file_path = STORAGE_DIR / filename

    # Security check: prevent directory traversal
    if not file_path.resolve().is_relative_to(STORAGE_DIR.resolve()):
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found")

    return FileResponse(
        path=file_path, filename=filename, media_type="application/octet-stream"
    )


@app.post("/files")
async def store_file(file: UploadFile = File(...)):
    """
    Store a file locally on the filesystem.

    Args:
        file: The file to upload

    Returns:
        JSON response with file information

    Raises:
        HTTPException: If file storage fails
    """
    try:
        # Security check: prevent directory traversal in filename
        filename = os.path.basename(file.filename)
        if not filename or filename in (".", ".."):
            raise HTTPException(status_code=400, detail="Invalid filename")

        file_path = STORAGE_DIR / filename

        # Read file content
        content = await file.read()

        # Write file to storage directory
        file_exists = file_path.exists()
        with open(file_path, "wb") as f:
            f.write(content)

        # Increment counter only if it's a new file
        global files_stored_counter
        if not file_exists:
            files_stored_counter += 1

        return {
            "message": "File stored successfully",
            "filename": filename,
            "size": len(content),
            "content_type": file.content_type,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store file: {str(e)}")


@app.get("/files")
async def list_files():
    """
    List all stored files.

    Returns:
        JSON response with list of filenames
    """
    files = [f.name for f in STORAGE_DIR.iterdir() if f.is_file()]
    return {"files": files, "count": len(files)}


@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        JSON response indicating server health status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "File Storage API",
    }


@app.get("/metrics")
async def metrics():
    """
    Metrics endpoint providing server statistics.

    Returns:
        JSON response with various metrics
    """
    files = [f for f in STORAGE_DIR.iterdir() if f.is_file()]
    total_size = sum(f.stat().st_size for f in files)

    return {
        "files_stored_total": files_stored_counter,
        "files_current": len(files),
        "total_storage_bytes": total_size,
        "total_storage_mb": round(total_size / (1024 * 1024), 2),
        "timestamp": datetime.utcnow().isoformat(),
    }
