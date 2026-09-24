s = "Python is easy"

result = ""
for char in s:
        if char != " ":
                result +=char

print(result)


#reverse words in sentence

s = s.split(" ")

res = " ".join(s[::-1])

print(res)
