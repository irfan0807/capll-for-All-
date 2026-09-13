s = "python automation"

vowels = 'aeiou'

count = 0
for i in s:
        if i in vowels:
                count +=1

print(f"vowels length {count} and consonent length {len(s) - count}")
