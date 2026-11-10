import argparse
import os
import sys

from .agent import Artic
from .core import open_index
from .llm import make_engine
from .vault import Vault


def main():
    ap = argparse.ArgumentParser(prog="artic", description="A.R.T.I.C. - never forgets.")
    ap.add_argument("cmd", choices=["init", "chat", "dream", "search", "stats", "act"])
    ap.add_argument("query", nargs="*")
    ap.add_argument("--vault", default=os.environ.get("ARTIC_VAULT", "~/ArticVault"))
    ap.add_argument("--engine", default=None, help="anthropic | openai | echo")
    a = ap.parse_args()

    vault = Vault(a.vault)
    vault.init()
    index = open_index(str(vault.root))
    agent = Artic(vault, make_engine(a.engine), index)

    if a.cmd == "init":
        print(f"Vault ready at {vault.root} (index backend: {index.backend})")
    elif a.cmd == "stats":
        print(index.stats(), "backend:", index.backend)
    elif a.cmd == "search":
        for h in index.search(" ".join(a.query), 8):
            print(f"{h['score']:.2f}  [[{h['title']}]]")
    elif a.cmd == "dream":
        print("Wrote:", agent.dream() or "nothing to consolidate yet")
    elif a.cmd == "act":
        goal = " ".join(a.query).strip()
        if not goal:
            print('usage: artic act "what to build"')
        else:
            print(agent.act(goal))
    else:
        print(f"A.R.T.I.C. online (engine={agent.engine.name}, memory={index.backend}). Ctrl-Z then Enter to exit.")
        try:
            while True:
                print("\n" + agent.chat(input("you> ")))
        except (EOFError, KeyboardInterrupt):
            print("\nEverything is saved. Nothing is forgotten.")


if __name__ == "__main__":
    sys.exit(main())
