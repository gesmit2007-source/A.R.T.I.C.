person = {"name": "Lydia", "project": "A.R.T.I.C."}

print(person["name"])
person["goal"] = "never forget"

for key in person:
    print(key, "=", person[key])

note = {"title": "My First Note", "body": "Dictionaries hold labelled values.", "tag": "python"}

for key in note:
    print(key, "=", note[key])