from enum import Enum
import math
import numpy as np
from typing import (
    Optional,
    Tuple   ,
    Set     ,
    Iterable
)

Coordinate = Tuple[int,int]




class ToolBox():
    def __init__(self) -> None:
        pass

    @staticmethod
    def rotation(vector: Tuple[int, int], angle: int) -> Tuple[int, int]:
        rotation_mat = np.array((
            (math.cos(math.radians(angle)), -math.sin(math.radians(angle))),
            (math.sin(math.radians(angle)), math.cos(math.radians(angle)))
        ))
        _vector = np.expand_dims(np.array(vector), -1)
        res_vector = np.matmul(rotation_mat, _vector).squeeze().tolist()
        return tuple([int(x) for x in res_vector])

    @staticmethod
    def getEuclideanDistance(coo_1: Tuple[int, int], coo_2: Tuple[int, int]) -> None:
        distance = math.sqrt((coo_1[0] - coo_2[0]) ** 2 + (coo_1[1] - coo_2[1]) ** 2)
        return distance

    '''
    getSpecifiedCoo方法返回圆心为center、半径为r的圆中所有的整数坐标
    '''
    @staticmethod
    def getSpecifiedCoo(center:Tuple[int,int],r:int,*,only_edge:bool=False)->Set[Tuple[int,int]]:
        x_list = [x for x in range(math.ceil(center[0]-r),math.floor(center[0]+r+1))]
        coo_res = set([])
        for x in x_list:
            temp = math.sqrt(r**2-(x-center[0])**2)
            low , high = center[1]-temp , center[1]+temp
            if only_edge:
                coo_res.add((x,math.ceil(low)))
                coo_res.add((x,math.floor(high)))
            else:   
                for y in range(math.ceil(low),math.floor(high+1)):
                    coo_res.add((x,y))
        return coo_res

    @staticmethod
    def isParallel(vector1:Coordinate,vector2:Coordinate):
        assert len(vector1) == len(vector2) , "向量维度不同"
        
        return vector1[0] * vector2[1] - vector1[1] * vector2[0]

    @staticmethod
    def isVertical(vector1:Coordinate,vector2:Coordinate):
        assert len(vector1) == len(vector2) , "向量维度不同"
        return not (vector1[0] * vector2[0] + vector1[1] * vector2[1])
    @staticmethod
    def subForVector(vector1:Coordinate,vector2:Coordinate):
        res = (x1-x2 for x1,x2 in zip(vector1,vector2))
        return tuple(res)


    @staticmethod
    def sign(x):
        if x>0:
            return 1
        elif x == 0:
            return 0
        else:
            return -1

