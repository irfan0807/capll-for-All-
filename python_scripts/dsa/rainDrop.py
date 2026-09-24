# height = [0,1,0,2,1,0,1,3,2,1,2,1]


# cache  = {}
# maxLeft = 0
# maxRight = 0
# for i in range(len(height)):
#       maxLeft = max(maxLeft ,height[i])
#       cache[i] = [maxLeft,0]
#       print(cache)
# for i in range(len(height)-1 ,-1,-1):
#       maxRight = max(maxRight,height[i])
#       cache[i][1] = maxRight
#       print(cache)
# water = 0

# for i in range(len(height)):
#       water += min(cache[i][0] , cache[i][1]) - height[i]

# print(water)

height = [0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1]

cache = {}

# --------------------------------
# STEP 1: Store maxLeft
# --------------------------------

maxLeft = 0

for i in range(len(height)):
    maxLeft = max(maxLeft, height[i])
    cache[i] = [maxLeft, 0]

print("After LEFT pass:")
print(cache)


# --------------------------------
# STEP 2: Store maxRight
# --------------------------------

maxRight = 0

for i in range(len(height) - 1, -1, -1):
    maxRight = max(maxRight, height[i])
    cache[i][1] = maxRight

print("\nAfter RIGHT pass:")
print(cache)


# --------------------------------
# STEP 3: Calculate water
# --------------------------------

water = 0

for i in range(len(height)):

    leftMax = cache[i][0]
    rightMax = cache[i][1]

    waterLevel = min(leftMax, rightMax)

    trapped = waterLevel - height[i]

    water += trapped

    print(
        "i =", i,
        "| height =", height[i],
        "| leftMax =", leftMax,
        "| rightMax =", rightMax,
        "| waterLevel =", waterLevel,
        "| trapped =", trapped,
        "| totalWater =", water
    )

print("\nFinal Water:", water)
