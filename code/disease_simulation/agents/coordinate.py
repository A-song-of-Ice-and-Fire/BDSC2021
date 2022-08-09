from typing import (
    Tuple ,
    Union ,
    Iterable
)
#继承自不可变对象
class Coordinate(tuple):
    def __new__(cls, coo:Union[Tuple[int,int],Iterable]):  # 重写__new__方法
        if isinstance(coo,Iterable):
            coo = tuple(coo)
        return super().__new__(cls, coo)  # 返回元组
    def __init__(self,coo:Tuple[int,int]):
        pass
    def __add__(self, other:Tuple[int,int]):
        self = (self[0]+other[0] , self[1]+other[1])
        return self
    def __mul__(self,other:int):
        self = tuple(other * value for value in self)
        return self
if __name__ == "__main__":
    c = Coordinate([3,4])
    a = Coordinate([1,2])
    print(a*3)
    print(a)