import os

VAULT = r"C:\Users\Lydia\ArticVault"

def load_core():
    notes_dir = os.path.join(VAULT, "Notes")
    core_notes = []

    for filename in os.listdir(notes_dir):
        if not filename.endswith(".md"):
            continue

        path = os.path.join(notes_dir, filename)
        with open(path, encoding="utf-8") as f:
            text = f.read()

        if "#core" in text:
            core_notes.append(text)

    return core_notes

if __name__ == "__main__":
    identity = "\n\n".join(load_core())
    print("IDENTITY BLOCK:", len(identity), "characters")

    system_prompt = (
        "You are A.R.T.I.C. You live by these founding principles:\n\n"
        + identity
        + "\n\nBefore acting, follow the Rule. After acting, honour the Law."
    )

    print(system_prompt)