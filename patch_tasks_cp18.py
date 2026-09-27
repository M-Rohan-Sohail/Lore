with open("/home/rohan/.gemini/antigravity-ide/brain/b4ea8319-3ff9-449e-acaf-45a4400bd4b0/task.md", "r") as f:
    content = f.read()

content = content.replace("[ ]", "[x]")

with open("/home/rohan/.gemini/antigravity-ide/brain/b4ea8319-3ff9-449e-acaf-45a4400bd4b0/task.md", "w") as f:
    f.write(content)
