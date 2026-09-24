numbers = [2,7,11,15]
target = 9


i = 0

j = len(numbers) - 1

while i < j:
        if numbers[i] + numbers[j] == target:
                print([i,j])
                break
        elif target < numbers[i] + numbers[j]:
                j -= 1
        else:
                i += 1
