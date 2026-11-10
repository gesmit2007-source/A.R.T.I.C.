names = []

while True:
    name = input("What is your name? (Type quit to stop) ")
    if name == "quit":
        break
    
    names.append(name)

    if name == "Lydia":
        print("Welcome back, creator of A.R.T.I.C.!")
    else:
        print(f"Hello, {name}!")
        
print("Goodbye.")
print("You met:")
for n in names:
    print("-", n)