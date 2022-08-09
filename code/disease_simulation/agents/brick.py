from .utilities import Coordinate
from mesa import Agent
from typing import (
    Optional,
    Tuple,
    Set
)
class Brick(Agent):
    def __init__(self, unique_id, model,build):
        super().__init__(unique_id, model)
        self.model = model
        self.pos = None
        self.build = build
    def step(self):
        pass


class Build():
    def __init__(self, id_counter, model, pos: Tuple, width=1, height=1,watch_time=0):
        self.width, self.height = width, height
    
        self.model = model
        self.bricks = []
        self.bricks_pos = []
        self.edge_bricks = []
        self.audiences = set()
        self.layer = 0
        self.game_had_begun = False
        self.gate_pos:Optional[Coordinate] = None
        self.givePositions(pos, id_counter)

        self.watch_time = watch_time if watch_time >=0 else 0
    
    def startWatch(self):
        if len(self.audiences)>0:
            for audience in self.audiences:
                audience.action_status[-1].start_time = self.model.schedule.steps
                audience.action_status[-1].in_time = self.watch_time
    
    def givePositions(self, init_pos:Coordinate, id_counter):  #Build的坐标应该是一个集合，里面包含了所有Brick对象的坐标
        def is_pos_available(pos):
            res = True
            for dx in range(0, self.width):
                for dy in range(0, self.height):
                    try:
                        if not self.model.grid.is_cell_empty((pos[0] + dx, pos[1] + dy)):
                            res = False
                    except IndexError as e:
                        res = False
                     
            return res

        for _ in range(20):
            if is_pos_available(init_pos):
                self.gate_pos = init_pos
                for dx in range(0, self.width):
                    for dy in range(0, self.height):
                        brick = Brick(id_counter.send(True), self.model,self)
                        self.bricks.append(brick)                        
                        self.model.schedule.agents.append(brick)
                        self.model.grid.place_agent(brick, (self.gate_pos[0] + dx, self.gate_pos[1] + dy))
                        self.bricks_pos.append(brick.pos)
                        if (dx in (0 , self.width-1)) or (dy in (0,self.width-1)):
                            self.edge_bricks.append(brick)
                return
        raise Exception("grid中没有空的位置分配给新的brick")
    def getCornerPos(self):
        corners_pos = []
        corners_pos.append(self.gate_pos)
        corners_pos.append(self.gate_pos[0] + self.width - 1 , self.init_pos[1])
        corners_pos.append(self.gate_pos[0] + self.width - 1 , self.init_pos[1] + self.height - 1)
        corners_pos.append(self.gate_pos[0] , self.init_pos[1] + self.height - 1)
        return corners_pos
    def getExits(self)->Set:
        exits_pos = set()
        for brick in self.edge_bricks:
            neighborhoods = self.model.grid.get_neighborhood(brick.pos,True)
            for neighborhood in neighborhoods:
                content = self.model.grid[neighborhood[0]][neighborhood[1]]
                if not isinstance(content,Brick):
                    exits_pos.add(neighborhood)
        return exits_pos