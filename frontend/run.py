import sys
import os

# Set working directory to this file's folder to resolve relative references
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from app.main import main

if __name__ == "__main__":
    main()
