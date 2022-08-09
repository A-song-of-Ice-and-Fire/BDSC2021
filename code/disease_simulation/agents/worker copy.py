import numpy as np
from .individual import Coordinate, Individual
from .brick import Brick
from enum import Enum
from .utilities import ToolBox
from typing import (
    Optional,
    NoReturn,
    Tuple,
    Set
)
class ActionStatus(Enum):
    go_to = 0
    in_somewhere = 1
    go_back = 2
    waiting = 3

class Worker(Individual):
    speed_set = set([(1, 0), (0, 1), (-1, 0), (0, -1)])
    def __init__(self,unique_id:int,model):     #定义self.unique_id、self.model和self.status
        super().__init__(unique_id,model)
        self.action_status = ActionStatus.go_to
    def gridInit(self, start_pos: Optional[Coordinate], end_pos: Optional[Coordinate],end_distance:Optional[int],in_step:Optional[int],waiting_step:Optional[int]=2) -> NoReturn:
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
                elif self.model.grid.out_of_bounds(pos):
                    continue
                end_pos_set.add(pos)

            try:
                end_pos = self.model.random.sample(end_pos_set,1)[0]
            except ValueError as e:
                end_pos = self.model.grid.find_empty()
        self.start_pos = self.cur_start_pos = self.pos
        self.end_pos = self.cur_end_pos = end_pos 
        self.in_step , self.waiting_step = in_step , waiting_step
        self.last_v = self.random.sample(self.__class__.speed_set,1)[0]            
        self.commuting_path:list[Coordinate] = []
        self.commuting_path.append(self.pos)    #已经定义了最初的速度向量self.last_v和最初的位置坐标self.pos
        self.direction_vectors = [] 
    def move(self)->NoReturn:
        '''
        移动方法，该移动方法分为两个阶段，即上班、等待和下班
        '''
        if self.action_status == ActionStatus.waiting:
            if  self.model.grid.is_cell_empty(self.expect_next):        #等待过程中发现前面格子空掉，则进入前面格子继续前行
                self.model.grid.move_agent(self,self.expect_next)
                self.expect_next = None
                self.action_status = self.last_status
            elif self.model.schedule.steps-self.start_step > self.waiting_step:       #若等待超过预期时长，进行随机绕行
                reverse_last_v = (-self.last_v[0],-self.last_v[1])
                new_pos_available = set()
                for speed in self.__class__.speed_set-set([reverse_last_v]):
                    _pos = (self.pos[0]+speed[0] , self.pos[1]+speed[1])
                    
                    if self.model.grid.torus:
                        _pos = self.model.grid.torus_adj(_pos)
                    elif self.model.grid.out_of_bounds(_pos):
                        continue
                    new_pos_available.add(_pos)
    
                if len(new_pos_available) > 0:
                    new_pos = self.model.random.sample(new_pos_available,1)[0]
                    if self.model.grid.is_cell_empty(new_pos):    
                        self.model.grid.move_agent(self,new_pos)
                        self.action_status = self.last_status
            else:
                ... 
            #这里可能要加，worker在下班途中如果遇到了堵塞，其寻找原路径的方法

        elif self.action_status == ActionStatus.go_to:                              #
            self.last_v = self._move_goto(self.last_v)
            if self.pos == self.cur_end_pos:
                self.last_status = self.action_status
                self.action_status = ActionStatus.in_somewhere
                self.start_step = self.model.schedule.steps
                
        elif self.action_status == ActionStatus.in_somewhere and self.model.schedule.steps-self.start_step>self.in_step:
            self.start_step = None 
            self.action_status = ActionStatus.go_to 
            self.last_status = ActionStatus.in_somewhere
            self.cur_start_pos , self.cur_end_pos = self.cur_end_pos , self.cur_start_pos
            self.last_v = (-self.last_v[0] , -self.last_v[1]) if self.cur_start_pos != self.start_pos else self.random.sample(self.__class__.speed_set,1)[0]
            self.move()
            
    #进行移动，移动有可能会发生，有可能不会，取决于速度向量方向是否存在其他人
    def _move_goto(self,last_v:Coordinate)->Tuple[Coordinate,Coordinate]:
        assert last_v in self.__class__.speed_set  , '速度矢量不正确'
        if  self.direction_vectors:                                                                   #若处于绕行模式下
            v = self.direction_vectors[0]
            new_pos = (self.pos[0] + v[0], self.pos[1] + v[1])
            next_content = self.model.grid[new_pos[0]][new_pos[1]]
            if isinstance(next_content, Individual):
                v = last_v
                ... #绕行模式下的行人拥堵策略
            else:
                self.model.grid.move_agent(self,new_pos)
                self.direction_vectors = self.direction_vectors[1:]
        else:
            v = self.move_naive(last_v)

        return v 

    def step(self)->NoReturn:
        if self.pos is not None:
            self.spread()
            self.move()

    def move_naive(self,last_v:Coordinate)->Tuple[Coordinate,Coordinate]:                        #普通的随机走动
        distance = (self.cur_end_pos[0] - self.pos[0], self.cur_end_pos[1] - self.pos[1])
        dot_res = np.dot(np.array(distance), np.array(last_v))
        angle = 0
        if dot_res == 0:
            angle = 90 * ToolBox.sign(np.cross(np.array(last_v), np.array(distance)))  # 利用二维叉乘判定速度向量和距离向量的相对角度关系（顺逆时针关系）
        elif dot_res < 0:
            angle = 180
        v = ToolBox.rotation(last_v, angle)
        new_pos = (self.pos[0] + v[0], self.pos[1] + v[1])
        next_content = self.model.grid[new_pos[0]][new_pos[1]]
        if isinstance(next_content, Individual):
            self.waitInit(last_v,new_pos)
            v = last_v
        elif isinstance(next_content,Brick):
            angle = self.random.sample([-90,90],1)[0]                                                     #生成方向向量列表
            self.direction_vectors.append(ToolBox.rotation(v,angle))
            self.direction_vectors.append(v)
            self.direction_vectors.append(v)
            self.direction_vectors.append(ToolBox.rotation(v,-angle))
            self.direction_vectors.append(v)
            v = self.move(last_v)
        else:
            self.model.grid.move_agent(self, new_pos)
        return v

    def waitInit(self,last_v:Tuple[int,int],expect_next:Tuple[int,int]):
        self.last_v = last_v
        self.start_step = self.model.schedule.steps
        self.last_status = self.action_status
        self.action_status = ActionStatus.waiting
        self.expect_next = expect_next
        self.move()

# if __name__ == "__main__":
#     a = Worker()
