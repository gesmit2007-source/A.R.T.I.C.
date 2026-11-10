from mynotes import save_note

last_title = none

while True:
    title = input("Title (or quit: ")
    if title == "quit":
        break

    body = imput("What did you learn? ")
    tag input("One tag: ")

    links = []
    if last_title:
        links.append(last_title)

    save_note(title, body, [tag], links)

print("Saved. Open Myvault in Obsidian.")
    