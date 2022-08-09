from os import walk
from agents.action_status import ActionStatus
import numpy as np
from .action_status import (
    ModeEnum,
    ActionEnum,
    Goto,
    InSomewhere,
    Walk,
    Waiting
)
from .individual import Individual
from .utilities import ToolBox,Coordinate
from .brick import Build,Brick
from typing import (
    Optional ,
    NoReturn ,
    Tuple,
    Set
)

class Audience(Individual):

    speed_set = set([(1, 0), (0, 1), (-1, 0), (0, -1)])
    waiting_time = None


    def __init__(self,unique_id:int,model,waiting_time=2):
        super().__init__(unique_id,model)
        self.action_status = []                  #行动状态栈
        self.__class__.waiting_time = waiting_time
    def gridInit(self,start_pos:Optional[Coordinate]=None,end_point:Optional[Build]=None):
        if self.__class__ is None:
            self.__class__.end_point = end_point

        if not start_pos:
            self.model.grid.position_agent(self)
        else:
            self.pos = start_pos
            self.model.grid._place_agent(start_pos,self)
        
        self.end_point = end_point 
        self.action_status.append(
            Goto(
                self.pos,
                self.end_point.gate_pos,
                self.random.sample(self.__class__.speed_set, 1)[0],
            )
        )

    def move(self):
        cur_action = self.action_status[-1]
        if cur_action.status == ActionEnum.go_to:
            if  cur_action.mode == ModeEnum.global_ and (                                                           #到达全局终点
                set(self.end_point.bricks_pos) & 
                set(self.model.grid.get_neighborhood(self.pos,False)) 
                            ):  
                self.model.grid.remove_agent(self)
                self.action_status.pop()
                self.inSomewhereInit()
                self.move()
            elif cur_action.mode == ModeEnum.local and cur_action.isEnd(self.pos):
                self.action_status.pop()
                self.action_status[-1].last_v = cur_action.initial_expect_v
                self.move()
            else:
                cur_action.last_v = self.moveGoto(cur_action.last_v,cur_action.mode)
        elif cur_action.status == ActionEnum.in_somewhere:
            if cur_action.isDepart(self.model.schedule.steps):
                #搜索观赛场地
                for exit_ in self.end_point.getExits():
                    if self.model.grid.is_cell_empty(exit_):
                        self.action_status.pop()
                        break
                else:
                    return
                self.model.grid.place_agent(self,exit_)
                self.walkInit()
        elif cur_action.status == ActionEnum.waiting:
            if  self.model.grid.is_cell_empty(cur_action.expect_next):        #等待过程中发现前面格子空掉，则进入前面格子继续前行
                self.model.grid.move_agent(self,cur_action.expect_next)
                self.action_status.pop()
            elif cur_action.isDepart(self.model.schedule.steps):       #若等待超过预期时长，进行随机绕行
                reverse_v = (-cur_action.last_status_v[0],-cur_action.last_status_v[1])
                new_pos_available = set()
                for speed in self.__class__.speed_set-set([reverse_v]):
                    _pos = (self.pos[0]+speed[0] , self.pos[1]+speed[1])
                    if self.model.grid.torus:
                        _pos = self.model.grid.torus_adj(_pos)
                    if self.model.grid.out_of_bounds(_pos) or (not self.model.grid.is_cell_empty(_pos)):
                        continue
                    new_pos_available.add(_pos)
    
                if len(new_pos_available) > 0:
                    new_pos = self.model.random.sample(new_pos_available,1)[0]
                    self.model.grid.move_agent(self,new_pos)
                    self.action_status.pop()
            else:
                ... 
        elif cur_action.status == ActionEnum.walk:
            super().move()


    def walkInit(self):
        self.action_status.append(
            Walk()
        )
    def waitInit(self,last_v:Tuple[int,int],expect_next:Tuple[int,int])->NoReturn:
        self.action_status.append(
            Waiting(
                expect_next,
                self.model.schedule.steps,
                self.waiting_time,
                self.action_status[-1].last_v
            )
        )
        self.move()


    def inSomewhereInit(self):
        self.action_status.append(
            InSomewhere()
        )


    def moveGoto(self,last_v:Coordinate,mode:ModeEnum)->Coordinate:
        '''
        计算当前速度，行为模式为：
            若上步的速度矢量与距离矢量夹角小于90度，则速度矢量不变
            若上步的速度矢量与距离矢量夹角为90度，则速度矢量旋转至于距离矢量同向
            若上步的速度矢量与距离矢量夹角大于90度，则速度矢量反向
        注意，速度矢量只可能为Union((1,0),(0,1),(-1,0),(0,-1))

        '''
        assert last_v in self.__class__.speed_set  , '速度矢量不正确'
        cur_end_pos = self.action_status[-1].end_pos
        distance = (cur_end_pos[0] - self.pos[0], cur_end_pos[1] - self.pos[1])
        dot_res = np.dot(np.array(distance), np.array(last_v))
        angle = 0
        if dot_res == 0:
            angle = 90 * ToolBox.sign(np.cross(np.array(last_v), np.array(distance)))  # 利用二维叉乘判定速度向量和距离向量的相对角度关系（顺逆时针关系）
            angle = angle if angle != 0 else self.model.random.sample([90,-90],1)[0]    
        elif dot_res < 0:
            angle = 180
        v = ToolBox.rotation(last_v, angle)
        new_pos = (self.pos[0] + v[0], self.pos[1] + v[1])
        next_content = self.model.grid[new_pos[0]][new_pos[1]]


        if isinstance(next_content, Individual):
            self.waitInit(last_v,new_pos)
            v = last_v
        elif mode==ModeEnum.global_ and isinstance(next_content,Brick): #若前方为建筑物，需提供建筑物的所在方向信息
            self.detourInit(v)
            v = last_v
        else:
            self.model.grid.move_agent(self, new_pos)
        return v
    def detourInit(self,expect_v:Coordinate)->NoReturn: #首先必须要确定局部目的地
        global_end_pos = self.action_status[0].end_pos
        distance = (global_end_pos[0] - self.pos[0] , global_end_pos[1] - self.pos[1])
        angle = 90 * ToolBox.sign(np.cross(np.array(expect_v), np.array(distance)))  # 利用二维叉乘判定速度向量和距离向量的相对角度关系（顺逆时针关系）                                                                        #判断distance在当前期望速度的方向（顺时针或者逆时针）
        if angle == 0:
            angle = self.random.sample([90,-90],1)[0]

        next_v = ToolBox.rotation(expect_v,angle)
        
        #判断沿此方向，建筑物是否与边缘接壤，并确定一个局部终点以使得绕行最优
        brick_ahead_pos =  (self.pos[0]+expect_v[0],self.pos[1]+expect_v[1])
        while isinstance(self.model.grid[brick_ahead_pos[0],brick_ahead_pos[1]],Brick):
            brick_ahead_pos = (brick_ahead_pos[0]+next_v[0] ,brick_ahead_pos[1]+next_v[1])
            if self.model.grid.out_of_bounds(brick_ahead_pos):
                next_v = ToolBox.rotation(180)
                brick_ahead_pos =  (self.pos[0]+expect_v[0],self.pos[1]+expect_v[1])
                while isinstance(self.model.grid[brick_ahead_pos[0]],self.model.grid[brick_ahead_pos[1]],Brick):
                    brick_ahead_pos = (brick_ahead_pos[0]+next_v[0] ,brick_ahead_pos[1]+next_v[1])
                break
        local_end_pos = brick_ahead_pos
        self.action_status.append(
            Goto(
                self.pos,
                local_end_pos,
                next_v,
                ModeEnum.local,
                expect_v
            )
        )
        self.move()

    def step(self)->NoReturn:
        if self.pos:
            self.spread()
        self.move()
            
if __name__ == "__main__":
    import os
    print(f"{os.path.split(os.path.realpath(__file__))[0]}")