def remember(name):
    with open("names.txt", "a") as f:
        f.write(name + "\n")

def recall():
    try:
        with open("names.txt") as f:
            return f.read()
    except FileNotFoundError:
        return "(nothing remembered yet)"

name = input("Who are you? ")
remember(name)
print(recall())