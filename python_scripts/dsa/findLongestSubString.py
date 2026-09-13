test_str = "hlohlohelo"

seen = set()
max_len = 0
left = 0


for right in test_str:
        if test_str[right] in seen:
