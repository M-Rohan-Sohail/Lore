import json
import sys
import os

# Add the root project directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app

def export_openapi():
    openapi_schema = app.openapi()
    with open("openapi.json", "w") as f:
        json.dump(openapi_schema, f, indent=2)
    print("Exported OpenAPI schema to openapi.json")

if __name__ == "__main__":
    export_openapi()
