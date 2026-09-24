height = [1,8,6,2,5,4,8,3,7]
 # maxWater = 49



l = 0
maxWater = 0
r = len(height) -1

while l < r:
        currentWaterLevel = (r - l) * min(height[l],height[r])
        if currentWaterLevel > maxWater:
                maxWater = currentWaterLevel
        if height[l] < height[r]:
                l +=1
        else:
                r -=1

print(maxWater)
