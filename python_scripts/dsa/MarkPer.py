raw_marks = [42, 38, 47, 29, 45]

def per(marks):
        return round(marks/50*100)



def grade(raw_marks):
        percentage = list(map(per , raw_marks))
        return percentage
items = grade(raw_marks)
for per , mar in zip(grade(raw_marks),raw_marks):
        print(f"{per} and marks{mar}")



ardes = list(map(lambda p:"Pass" if p >= 60 else "Fail" , items))

print(ardes)
