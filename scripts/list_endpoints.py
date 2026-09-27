import json

with open("openapi.json", "r") as f:
    spec = json.load(f)

for path, methods in spec["paths"].items():
    for method in methods:
        print(f"{method.upper()} {path}")
