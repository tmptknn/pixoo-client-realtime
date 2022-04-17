from operator import truediv
import random

from scipy.fftpack import ifftn

class Display:
    def __init__(self):
        self.index = 0
        self.current = 0
        self.displays = [self.make_display(),self.make_display()]

        self.colors = []
        for i in range(0,256):
            self.colors.append((random.randint(0,255), random.randint(0,255), random.randint(0,255)))


    def make_display(self):
        table = []
        for i in range(0, 16):
            row = []
            for j in range(0, 16):
                if random.randint(0,1):
                    row.append((0,0,0))
                else:
                    row.append((255,255,255))

            table.append(row)
        return table


    def step(self):
        self.current = (self.current + 1) % 2
        last = (self.current + 1) % 2
        self.life(self.displays[last], self.displays[self.current])
        

    def get_pixel(self, x,y):
        return  self.displays[self.current][x][y]


    def putData(self, data):
        for i in range(0, 16):
            for j in range(0, 16):
                offset = (i+16*j)*3
                self.displays[self.current][i][j] = (data[offset],data[offset+1],data[offset+2])


    def life(self, bufferFrom, bufferTo):
        width = 16
        height = 16
        bits = [0,0,0,0,0,0,0,0,0]
        for row in range(0,width):
            for col in range(0,height):
                sum=0
                for x in range(-1,2):
                    for y in range(-1,2):
                        pixelrow = (row+x)%width
                        if row+x<0:
                            pixelrow = width+(row+x)
                        pixelcolumn = (col+y)%height
                        if col+y<0:
                            pixelcolumn = height+(col+y)
                        currentbitr, currentbitg, currentbitb = bufferFrom[pixelrow][pixelcolumn]
                        currentbit = 0
                        if currentbitb == 255:
                            currentbit = 1
                        bits[(x+1)+(y+1)*3] = currentbit
                        sum+=currentbit
            
                alive = bits[4]
                cell= bufferFrom[row][col]
                sum -= alive
                
                live = False
                if (alive and sum > 1 and sum < 4) or ( not alive and sum >2 and sum <4):
                    live = True
                
                if live:
                    bufferTo[row][col] = (max(cell[0]-10,0),max(cell[1]-10,0),255)

                else:
                    if alive:
                        bufferTo[row][col] = (255,0,0)

                    else:
                        bufferTo[row][col] = (max(cell[0]-10,0),0,0)

