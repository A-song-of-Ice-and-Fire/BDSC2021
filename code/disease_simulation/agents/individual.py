from mesa import Agent
from enum import Enum
from .utilities import  ToolBox , Coordinate
from .action_status import InSomewhere , Walk
from typing import (
    Tuple,
    Optional
)


class DiseaseStatus(Enum):
    S = 0
    I = 1

class Individual(Agent):
    def __init__(self, unique_id:int, model):
        super().__init__(unique_id, model)
        self.disease_status = DiseaseStatus.S
        self.action_status = []

    #该方法用来初始化 其model已经初始化网格的Individual，给对象添加pos、start_pos属性
    def gridInit(self,start_pos:Optional[Coordinate]=None):
        if not start_pos:
            self.model.grid.position_agent(self)
        else:
            self.pos = start_pos
            self.model.grid._place_agent(start_pos,self)
        self.action_status.append(Walk())
    # 移动方式:随机移动，一个格子里至多只能有一个agent
    def move(self):
        neighborhoods = self.model.grid.get_neighborhood(
            self.pos,
            moore=False,
            include_center=False
        )

        empty_neighborhoods = []
        for neighborhood in neighborhoods:
            if self.model.grid.is_cell_empty(neighborhood):
                empty_neighborhoods.append(neighborhood)

        can_be_placed = []
        if self.model.min_contact_distance > 0:
            # 扫描警戒范围内是否存在Individual
            specifiedCoo = ToolBox.getSpecifiedCoo(self.pos, self.model.min_contact_distance)
            alert_distances = {}
            for coo in specifiedCoo:
                # 若为循环边界，则对其进行转化
                if self.model.grid.torus:
                    coo = self.model.grid.torus_adj(coo)
                if self.model.grid.out_of_bounds(coo):
                    continue
                
                if not self.model.grid.is_cell_empty(coo) and isinstance(self.model.grid[coo[0]][coo[1]], Individual):
                    alert_distances[coo] = ToolBox.getEuclideanDistance(self.pos, coo)
            # 在moore邻居中寻找可移动的邻居
            if len(alert_distances) > 0:
                for neighborhood in empty_neighborhoods:
                    for object_coo, object_distance in alert_distances.items():
                        if object_distance > ToolBox.getEuclideanDistance(neighborhood, object_coo):
                            break
                    else:
                        can_be_placed.append(neighborhood)
        can_be_placed = can_be_placed if len(can_be_placed) > 0 else empty_neighborhoods

        if can_be_placed:
            new_pos = self.random.choice(can_be_placed)
            self.model.grid.move_agent(self, new_pos)
            return new_pos
        return self.pos

    def spread(self):  # 向附近格子和当前
        if self.disease_status == DiseaseStatus.I:
            # neighbors_pos = self.model.grid.get_ring_neighborhood(self.model.grid,pos=self.pos,radius=self.model.infect_scope)
            # neighbors = self.model.grid.get_cell_list_contents(neighbors_pos)
            neighbors = self.model.grid.get_neighbors(pos=self.pos, moore=True, radius=self.model.infect_scope)
            for neighbor in neighbors:
                if  isinstance(neighbor, Individual) :
                    cur_status = neighbor.action_status[-1]
                    if isinstance(cur_status,InSomewhere):
                        continue
                    elif neighbor.disease_status == DiseaseStatus.S:
                        distance = self.relativeDistance(neighbor)
                        generated_number = self.random.random()
                        if generated_number < self.model.getBeta(distance):
                            neighbor.disease_status = DiseaseStatus.I

    def relativeDistance(self, other: Agent) -> float or None:
        if (other.pos is None) or (self.pos is None):
            return None
        return ToolBox.getEuclideanDistance(self.pos, other.pos)

    def step(self):
        if self.pos is not None:
            self.spread()
            self.move()
