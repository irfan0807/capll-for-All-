s = "Python automation interview"

longest = ""
for word in s.split(" "):
        if len(word) > len(longest):
                longest = word

print(f"longest word in given sentence is {longest} with length {len(longest)}")
