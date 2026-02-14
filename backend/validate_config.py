#!/usr/bin/env python3
"""
Configuration Validation Script
Validates that all required environment variables are set correctly
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def validate_config():
    """Validate configuration"""
    print("Validating configuration...\n")
    
    errors = []
    warnings = []
    
    # Check Obsidian Vault Path
    vault_path = os.getenv('OBSIDIAN_VAULT_PATH')
    if not vault_path:
        errors.append("OBSIDIAN_VAULT_PATH is not set")
    else:
        vault_path_obj = Path(vault_path)
        
        # Check if absolute
        if not vault_path_obj.is_absolute():
            errors.append(
                f"OBSIDIAN_VAULT_PATH must be absolute. Got: {vault_path}"
            )
        else:
            print("OBSIDIAN_VAULT_PATH is absolute")
        
        # Check if exists
        if not vault_path_obj.exists():
            warnings.append("Vault path does not exist; will be created on start.")
        else:
            print("Vault path exists")
            
            # Check if writable
            if not os.access(vault_path, os.W_OK):
                errors.append("Vault path is not writable")
            else:
                print("Vault path is writable")
    
    vault_root = os.getenv('VAULT_ROOT_FOLDER', 'Knowledge')
    print(f"VAULT_ROOT_FOLDER: {vault_root}")
    if vault_path:
        full_root = Path(vault_path) / vault_root
        print(f"   Content root: {full_root}")
    
    # Check Google OAuth
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
    
    if not client_id or client_id == 'your-google-client-id.apps.googleusercontent.com':
        errors.append("GOOGLE_CLIENT_ID not configured")
    else:
        print("GOOGLE_CLIENT_ID is set")
    if not client_secret or client_secret == 'your-google-client-secret':
        errors.append("GOOGLE_CLIENT_SECRET not configured")
    else:
        print("GOOGLE_CLIENT_SECRET is set")
    ai_provider = os.getenv('AI_PROVIDER', 'openai')
    print("AI_PROVIDER:", ai_provider)
    
    if ai_provider == 'openai':
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key or api_key == 'your-openai-api-key':
            warnings.append("OPENAI_API_KEY not set (AI features disabled)")
        else:
            print("OPENAI_API_KEY is set")
    elif ai_provider == 'anthropic':
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key or api_key == 'your-anthropic-api-key':
            warnings.append("ANTHROPIC_API_KEY not set (AI features disabled)")
        else:
            print("ANTHROPIC_API_KEY is set")
    secret_key = os.getenv('SECRET_KEY')
    if not secret_key or secret_key == 'your-secret-key-change-this-in-production':
        warnings.append("SECRET_KEY is default (change in production)")
    else:
        print("SECRET_KEY is set")
    print("\n" + "="*60)
    if warnings:
        print("\nWARNINGS:")
        for w in warnings:
            print(" ", w)
    if errors:
        print("\nERRORS:")
        for e in errors:
            print(" ", e)
        print("\nValidation failed. Fix errors above.\n")
        return False
    print("\nValidation passed.\n")
    return True

if __name__ == "__main__":
    success = validate_config()
    sys.exit(0 if success else 1)

