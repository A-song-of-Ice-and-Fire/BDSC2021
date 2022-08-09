from .utilities import Coordinate , ToolBox
from enum import Enum
from typing import Optional
class ActionEnum(Enum):
    go_to = 0
    in_somewhere = 1
    detour = 2
    waiting = 3
    walk = 4

class ActionStatus():
    def __init__(self,status:ActionEnum):
        self.status =status

class ModeEnum(Enum):
    local = 0
    global_ = 1


class Goto(ActionStatus):
    


    def __init__(
                self,
                start_pos:Coordinate,
                end_pos:Coordinate,
                last_v:Coordinate,
                mode:ModeEnum=ModeEnum.global_,
                initial_expect_v:Optional[Coordinate]=None    #初始的期望速度，一般在局部goto模式下使用
                ):
        super().__init__(ActionEnum.go_to)
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.last_v = last_v
        self.mode = mode
        self.initial_expect_v = initial_expect_v
        
    def reverse(self):
        self.start_pos , self.end_pos = self.end_pos , self.start_pos
    def isEnd(self,pos): #判断状态是否应该结束
        if pos == self.end_pos: #不管任何一种模式的goto，只要到达了终点，则状态结束
            return True
        elif pos == self.start_pos:
            return False
        elif self.mode == ModeEnum.local: #对于局部模式下的goto：
            '''
            从起始位置向当前位置引出一个向量，从起始位置向终点位置引出一个向量，若两者的差向量与最初的期望速度向量平行，则局部绕行
            结束
            '''
            start_to_cur_vector = ToolBox.subForVector(pos,self.start_pos)
            start_to_end_vector = ToolBox.subForVector(self.end_pos,self.start_pos)
            if ToolBox.isVertical(
                ToolBox.subForVector(start_to_cur_vector,start_to_end_vector) ,
                self.initial_expect_v):
                return True
        
        return False




class Waiting(ActionStatus):
    def __init__(self, 
                expect_next:Coordinate,
                start_time:int,
                waiting_time:int,
                last_status_v:Coordinate
                ):
        super().__init__(ActionEnum.waiting)
        self.expect_next = expect_next
        self.start_time = start_time
        self.waiting_time = waiting_time
        self.last_status_v = last_status_v
    def isDepart(self,cur_time:int):
        return cur_time - self.start_time > self.waiting_time

class InSomewhere(ActionStatus):
    def __init__(self, 
                start_time:Optional[int]=None,
                in_time:Optional[int]=None):
        super().__init__(ActionEnum.in_somewhere)
        self.start_time = start_time
        self.in_time = in_time
    def isDepart(self,cur_time:int):
        if self.in_time is None:
            return False
        
        return cur_time - self.start_time > self.in_time

class Walk(ActionStatus):
    def __init__(self):
        super().__init__(ActionEnum.walk)
    
        