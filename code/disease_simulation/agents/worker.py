import numpy as np
from .individual import Coordinate, Individual
from .brick import Brick
from .action_status import *
from .utilities import ToolBox
from typing import (
    Optional,
    NoReturn,
    Tuple,
    Set
)

class Status():
    def __init__(self,status:ActionStatus,
                last_v:Optional[Coordinate]=None,
                expect_pos:Optional[Coordinate]=None) -> None:
        self.status = status
        self.last_v = last_v
        self.expect_pos = expect_pos
class Worker(Individual):
    speed_set = set([(1, 0), (0, 1), (-1, 0), (0, -1)])
    def __init__(self,unique_id:int,model):     #定义self.unique_id、self.model和self.status
        super().__init__(unique_id,model)
        self.action_status = []             #self.action_status是一个栈，用来存储当前累积的所有行为状态

    def gridInit(self, 
                start_pos: Optional[Coordinate], 
                end_pos: Optional[Coordinate]=None,
                end_distance:Optional[int]=None,
                in_step:Optional[int]=None,
                waiting_step:Optional[int]=2,
                init_v = None) -> NoReturn:

        if not start_pos:
            self.model.grid.position_agent(self)
        else:
            self.pos = start_pos
            self.model.grid._place_agent(start_pos,self)
        
        assert bool(end_pos) or bool(end_distance) , "end_pos与end_distance参数至少需要指定一个"
        if not end_pos:
            end_pos_set_temp = ToolBox.getSpecifiedCoo(self.pos,end_distance,only_edge=True)
            end_pos_set:Set[Tuple[int,int]] = set()
            for pos in end_pos_set_temp:
                if self.model.grid.torus:
                    pos = self.model.grid.torus_adj(pos)
                elif self.model.grid.out_of_bounds(pos) or not self.model.grid.is_cell_empty(pos):
                    continue
                end_pos_set.add(pos)
            try:
                end_pos = self.model.random.sample(end_pos_set,1)[0]
            except ValueError as e:
                end_pos = self.model.grid.find_empty()

        self.start_pos , self.end_pos = self.pos , end_pos 
        self.in_step , self.waiting_step = in_step , waiting_step
        init_v = self.random.sample(self.__class__.speed_set,1)[0]  if init_v is None else init_v         
        
        self.action_status.append(
            Goto(
                self.start_pos,
                self.end_pos,
                init_v
            )
        )

    def move(self)->NoReturn:
        '''
        移动方法，该移动方法分为两个阶段，即上班、等待和下班
        '''
        cur_action = self.action_status[-1]
        if cur_action.status == ActionEnum.go_to:
            if cur_action.isEnd(self.pos):
                if cur_action.mode == ModeEnum.global_:
                    self.action_status.append(
                    InSomewhere(
                        self.model.schedule.steps,
                        self.in_step
                    )
                    )
                else:
                    self.action_status.pop()
                    self.action_status[-1].last_v = cur_action.initial_expect_v
                self.move()
                                          #
            else:
                cur_action.last_v = self._move_goto(cur_action.last_v,cur_action.mode)
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
                
        elif cur_action.status == ActionEnum.in_somewhere and cur_action.isDepart(self.model.schedule.steps):
            
            self.action_status.pop()
            self.action_status[-1].reverse()
            if self.action_status[-1].start_pos != self.start_pos:
                self.action_status[-1].last_v = (-self.action_status[-1].last_v[0] , -self.action_status[-1].last_v[1])
            else:
                self.action_status[-1].last_v = self.model.random.sample(self.__class__.speed_set,1)[0]
            self.move()
            
    #进行移动，移动有可能会发生，有可能不会，取决于速度向量方向是否存在其他人 ，
    #添加：当速度向量方向存在建筑物时，进入绕行模式
    def _move_goto(self,last_v:Coordinate,mode:ModeEnum)->Tuple[Coordinate,Coordinate]:
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

    def step(self)->NoReturn:
        if self.pos is not None:
            self.spread()
        self.move()

                        #普通的随机走动


    def waitInit(self,last_v:Tuple[int,int],expect_next:Tuple[int,int])->NoReturn:
        self.action_status.append(
            Waiting(
                expect_next,
                self.model.schedule.steps,
                self.waiting_step,
                self.action_status[-1].last_v
            )
        )
        self.move()
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
# if __name__ == "__main__":
#     a = Worker()
