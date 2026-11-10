import os

class MiniVault:
    def __init__(self, folder):
        self.folder = folder
        os.makedirs(self.folder, exist_ok=True)

    def save_note(self, title, body, tags, links):
        path = os.path.join(self.folder, title + ".md")
        tag_text = " ".join("#" + tag for tag in tags)
        link_text = " ".join("[[" + link + "]]" for link in links)

        if os.path.exists(path):
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"\n## Addendum\n{body}\n\nRelated: {link_text}\n{tag_text}\n")
        else:
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"# {title}\n\n{body}\n\nRelated: {link_text}\n{tag_text}\n")

vault = MiniVault(r"C:\Users\Lydia\MyVault")
vault.save_note("Python Classes", "A class is a blueprint.", ["python"], ["Python Functions"])
