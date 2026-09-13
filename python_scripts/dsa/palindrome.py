st = "madam"


def palindromCheck(s):
        if st == st[::-1]:
                return True
        else:
                return False



print(palindromCheck(st))
