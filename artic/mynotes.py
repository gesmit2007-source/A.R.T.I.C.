import os

VAULT = r"C:\Users\Lydia\MyVault"

def save_note(title, body, tags):
    os.makedirs(VAULT, exist_ok=True)
    path = os.path.join(VAULT, title + ".md")
    tag_text = " ".join("#" + t for t in tags)

    if os.path.exists(path):
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"\n## Addendum\n{body}\n\n{tag_text}\n")
    else:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"# {title}\n\n{body}\n\n{tag_text}\n")
