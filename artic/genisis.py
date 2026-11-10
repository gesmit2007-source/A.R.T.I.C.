import os

VAULT = r"C:\Users\Lydia\ArticVault"

CORE = [
    {
        "title": "The Rule - Glass-Brain Execution",
        "body": "Every agent must strictly follow the operational loop: Read -> Cross-wReference -> Execute -> Commit. No state changes are permitted without prior verification.",
        "links": ["The Law - The Law of Permanent Accumulation", "The Equation - Compounding Intelligence"],
    },
    {
        "title": "The Law - The Law of Permanent Accumulation",
        "body": "A.R.T.I.C. shall never execute an action, synthesize a response, or alter its state without committing a durable, linked entry to its primary core.",
        "links": ["The Rule - Glass-Brain Execution", "The Equation - Compounding Intelligence"],
    },
    {
         "title": "The Equation - Compounding Intelligence",
        "body": r"$$I_t = I_0 + \sum_{k=1}^{t} f(D_k) \cdot e^{\gamma \cdot C_k}$$",
        "links": ["The Rule - Glass-Brain Execution", "The Law - The Law of Permanent Accumulation"],
    }

]

for note in CORE:
    path = os.path.join(VAULT, "Notes", note["title"] + ".md")

    if os.path.exists(path):
        print("Already exists, skipping:", note["title"])
        continue

    link_text = " ".join("[[" + link + "]]" for link in note["links"])

    with open(path, "a", encoding="utf-8") as f:
        f.write(f"# {note['title']}\n\n{note['body']}\n\nRelated: {link_text}\n#core\n")
    print("Written:", note["title"])