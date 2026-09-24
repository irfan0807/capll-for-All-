nums = [1, 2, 3, 4, 5, 6]

e = []
o = []

for i in nums:
        if i % 2 == 0:
                e.append(i)
        else:
                o.append(i)

print(f"even and odd numbers respectively {e} , {o}")
