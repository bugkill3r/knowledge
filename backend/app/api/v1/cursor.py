"""Cursor CLI management endpoints"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import subprocess
import os
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class CursorStatusResponse(BaseModel):
    """Response model for Cursor status"""
    installed: bool
    authenticated: bool
    version: str | None
    user_email: str | None
    message: str


@router.get("/status", response_model=CursorStatusResponse)
async def get_cursor_status():
    """Check if Cursor Agent is installed and authenticated"""
    cursor_path = os.path.expanduser('~/.local/bin/cursor-agent')
    
    # Check if installed
    if not os.path.exists(cursor_path):
        return CursorStatusResponse(
            installed=False,
            authenticated=False,
            version=None,
            user_email=None,
            message="Cursor Agent not installed. Run: curl https://cursor.com/install -fsS | bash"
        )
    
    try:
        # Check version
        version_result = subprocess.run(
            [cursor_path, '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if version_result.returncode != 0:
            return CursorStatusResponse(
                installed=True,
                authenticated=False,
                version=None,
                user_email=None,
                message="Cursor Agent installed but not working properly"
            )
        
        version = version_result.stdout.strip()
        
        # Check authentication status
        status_result = subprocess.run(
            [cursor_path, 'status'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if status_result.returncode == 0 and 'Logged in as' in status_result.stdout:
            # Extract email from output
            lines = status_result.stdout.split('\n')
            email = None
            for line in lines:
                if 'Logged in as' in line:
                    email = line.split('Logged in as')[-1].strip()
                    break
            
            return CursorStatusResponse(
                installed=True,
                authenticated=True,
                version=version,
                user_email=email,
                message=f"Authenticated as {email}"
            )
        else:
            return CursorStatusResponse(
                installed=True,
                authenticated=False,
                version=version,
                user_email=None,
                message="Not authenticated. Run 'cursor-agent login' to authenticate"
            )
    
    except Exception as e:
        logger.error(f"Error checking Cursor status: {e}")
        return CursorStatusResponse(
            installed=True,
            authenticated=False,
            version=None,
            user_email=None,
            message=f"Error checking status: {str(e)}"
        )


@router.post("/install")
async def install_cursor_agent():
    """Trigger Cursor Agent installation"""
    try:
        result = subprocess.run(
            ['curl', 'https://cursor.com/install', '-fsS'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Installation failed: {result.stderr}")
        
        # Pipe to bash
        install_result = subprocess.run(
            ['bash'],
            input=result.stdout,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if install_result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Installation failed: {install_result.stderr}")
        
        return {
            "success": True,
            "message": "Cursor Agent installed successfully. Please restart the backend."
        }
    
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Installation timed out")
    except Exception as e:
        logger.error(f"Installation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login")
async def trigger_cursor_login():
    """Trigger Cursor Agent login (opens browser)"""
    cursor_path = os.path.expanduser('~/.local/bin/cursor-agent')
    
    if not os.path.exists(cursor_path):
        raise HTTPException(status_code=404, detail="Cursor Agent not installed")
    
    try:
        # Start login process (non-blocking)
        process = subprocess.Popen(
            [cursor_path, 'login'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a bit to see if it starts successfully
        import time
        time.sleep(2)
        
        if process.poll() is not None:
            # Process ended quickly, might be an error
            stdout, stderr = process.communicate()
            if stderr:
                raise HTTPException(status_code=500, detail=stderr)
        
        return {
            "success": True,
            "message": "Login process started. Please complete authentication in your browser."
        }
    
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

