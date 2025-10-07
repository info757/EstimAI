"""FastAPI main application entry point."""
from backend.app.app import create_app

# Create the application using the factory
app = create_app()