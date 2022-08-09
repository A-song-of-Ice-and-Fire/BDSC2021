import math, time, os
from datetime import datetime
import numpy as np
from alive_progress import alive_bar
from agents.action_status import ActionEnum
from scipy.stats import poisson
from mesa import Model
from mesa.space import SingleGrid
from mesa.time import RandomActivation
from mesa.datacollection import DataCollector
from rewrite_method import model_methods
from agents import * 
from typing import (
    Tuple , 
    List ,
    Callable ,
    Union , 
    Dict , 
    Iterable
)


def compute_i_ratio(model):
    agent_nums = model.total_individuals
    i_nums= 0
    for agent in model.schedule.agents:
        if agent.disease_status == DiseaseStatus.I:
            i_nums += 1
    return i_nums / agent_nums

def compute_s_ratio(model):
    agent_nums = model.total_individuals
    s_nums= 0
    for agent in model.schedule.agents:
        if agent.disease_status == DiseaseStatus.S:
            s_nums += 1

    return s_nums / agent_nums
x = 0
class DiseaseModel(Model):
    def __new__(cls,*args,**kwargs):
        return super().__new__(cls,*args,**kwargs)



    def __init__(
                self,
                individual_nums:Dict[int,Union[int,Tuple[int,...]]],
                init_I_nums:Dict[int,Union[int,Tuple[int,...]]],
                grid_size:Tuple[int,int],
                getBeta:Callable[[float],float]=0.5,
                infect_scope:int=3,
                min_contact_distance:int = 0,
                avg_end_distance:int=30,
                seed = time.time(),
                **log_params
    ):
        '''
        individual_nums:应该为一个dict，包含以下三个键：
            person：普通人的数量
            worker：工作者的数量
            audience：一个元组，记录了各场馆观赛者的数量
        init_I_nums:应该为一个dict，包含以下三个键：
            person：普通人中感染者的数量
            worker：工作者中感染者的数量
            audience：一个元组，记录的各场馆观赛者中感染病人的数量
        '''
        assert len(individual_nums) == len(init_I_nums) , "指定个体数量列表与指定感染者数量列表长度应该相等"
        

        np.random.seed(seed)

        self.running = True
        self.schedule = RandomActivation(self)          #调度器固定名称，不可更改
        self.grid = SingleGrid(*grid_size,False)
        #self.running = True
        self.getBeta = getBeta
        self.min_contact_distance = min_contact_distance
        self.infect_scope = infect_scope 
        self.id_counter = self.id_count()               #id计数器
        self.id_counter.send(None)
        print(log_params)
        self.step_in_record = log_params.get("step_in_record",None)
        self.log_dir = log_params.get("log_dir",".")
        
        if not isinstance(individual_nums["audience"],Iterable):
            individual_nums["audience"] = [individual_nums["audience"]]
        
        if not isinstance(init_I_nums["audience"],Iterable):
            init_I_nums["audience"] = [init_I_nums["audience"]]
 

        #生成建筑，根据individual["audience"]的长度
        self.builds = []
        center = (grid_size[0] // 2 , grid_size[1] // 2) 

        games_num = len(individual_nums["audience"]) if isinstance(individual_nums["audience"],Iterable) else 1
        end_point_coo = (center[0] - 24 *  math.floor(games_num/2),center[1])
        for i in range(games_num):
            self.builds.append( 
                  Build(
                        self.id_counter , 
                        self, 
                        ( end_point_coo[0] + i * 20 , end_point_coo[1] + self.random.randint(-5,5)),
                        width=self.random.randint(2,8),
                        height=self.random.randint(2,8),
                        watch_time=10
                        )
            )                             


        self.sortForDict(individual_nums , ("audience","worker","person"))      #创建个体的顺序按照audience、worker以及person的顺序
        self.sortForDict(init_I_nums,("audience","worker","person"))


        #生成各个个体的感染者序号,并计算总人数
        infected_ids = []
        left , right = None , self.id_counter.send(True)+1  
        self.total_individuals = 0
        for individual_num,init_I_num in zip(individual_nums.values(),init_I_nums.values()):              
            if not isinstance(individual_num,Iterable):
                individual_num , init_I_num = [individual_num] , [init_I_num]
            for _individual_num , _init_I_num in zip(individual_num,init_I_num):
                left , right = right , right + _individual_num
                infected_ids += self.random.sample(range(left,right),_init_I_num)
                self.total_individuals += _individual_num
        self.infected_ids = sorted(infected_ids) 
        infected_index_of_ids = 0



        with alive_bar(self.total_individuals) as bar:

        #创建观赛者
            for audience_num,build in zip(individual_nums["audience"],self.builds):    
                for _ in range(audience_num):
                    agent = Audience(self.id_counter.send(True),self,waiting_time=1)
                    if infected_index_of_ids < sum(init_I_nums["audience"]) and self.infected_ids[infected_index_of_ids] == agent.unique_id:
                        agent.disease_status = DiseaseStatus.I
                        infected_index_of_ids += 1
                    #agent.gridInit(start_pos = (70,45),end_point=self.end_point)
                    agent.gridInit(end_point=build)
                    build.audiences.add(agent)
                    self.schedule.add(agent)
                    bar()

            #创建工作者，对于每个工作者，从poisson分布中抽样一个数作为其固定的移动步长
            distances_list = poisson.rvs(avg_end_distance,size = individual_nums["worker"])                
            #flag = False
            for _ , end_distance in zip(range(individual_nums["worker"]),distances_list):
                agent = Worker(self.id_counter.send(True),self)
                if infected_index_of_ids < sum(init_I_nums["audience"])+init_I_nums["worker"] and  \
                    self.infected_ids[infected_index_of_ids] == agent.unique_id:
                    agent.disease_status = DiseaseStatus.I
                    infected_index_of_ids += 1
                # if not flag:
                #     agent.gridInit((20,10),(20,16),None,in_step=10)
                #     flag = True
                # elif flag:
                #     agent.gridInit((20,16),(20,10),None,in_step=10)
                agent.gridInit(None,None,end_distance,in_step=40,waiting_step=1)
                self.schedule.add(agent)
                bar()

            #创建普通人
            for _ in range(individual_nums["person"]):     
                agent = Individual(self.id_counter.send(True),self)
                if infected_index_of_ids < sum(init_I_nums["audience"])+init_I_nums["worker"]+init_I_nums["person"] \
                    and self.infected_ids[infected_index_of_ids] == agent.unique_id:
                    agent.disease_status = DiseaseStatus.I
                    infected_index_of_ids += 1
                agent.gridInit()
                self.schedule.add(agent)
                bar()


        self.data_collector = DataCollector(
            model_reporters = {"s_ratio" : compute_s_ratio , "i_ratio" : compute_i_ratio}
        )

        for method in model_methods: 
            exec(f"self.grid.{method.__name__}=method")
            
    def step(self):
        self.schedule.step()

        #检查所有观众，若所有观众均到了，则开始观看比赛
        for build in self.builds:
            if not build.game_had_begun:
                for audience in build.audiences:
                    cur_action = audience.action_status[-1]
                    if (cur_action.status != ActionEnum.in_somewhere) or (cur_action.start_time is not None):
                        break        
                else:
                    build.startWatch()

        self.data_collector.collect(self)
        print(f"self.schedule.steps={self.schedule.steps}\nself.self.step_in_record={self.step_in_record}")
        if self.schedule.steps == self.step_in_record:
            log_path = os.path.join(self.log_dir,f"{self.schedule.steps}_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv ")
            self.data_collector.get_model_vars_dataframe().to_csv(log_path,index=False)
    
    @staticmethod
    def sortForDict(_dict:Dict,keys_sort:List): #_dict按照keys_sort进行排序
        assert set(_dict.keys()) == set(keys_sort) , "keys_sort与_dict的键应该一致"
        res = []
        for key in keys_sort:
            res.append(
                (key , _dict[key])
            )
        return dict(res)
    

            


    def id_count(self):         #初始化时为-1，若send为False，则输出与上一个输出相同，否则在上一个输出的基础上加1
        cur_id , max_id = -1 , self.grid.width * self.grid.height
        while cur_id < max_id:
            status = yield cur_id
            if status:
                cur_id += 1
        raise StopIteration("已达最大编号")
    
    @staticmethod
    def getBasePortrayal(Agent):
        portrayal_brick = {
                "Shape" : "rect",
                "Color" : "black",
                "Filled" : "false",
                "Layer" : 0,
                "w"     : 0.8,
                "h"     : 0.8
            }
        portrayal_individual = {
                "Shape" : "circle",
                "Color" : "blue",
                "Filled" : "false",
                "Layer" : 0,
                "r"     : 0.8
            }
        portrayal_audience = {
            "Shape" : "rect",
            "Color" : "blue",
            "Filled" : "false",
            "Layer" : 0,
            "w"     : 0.5,           #绘制圆的直径，一般一个格子的边长为1
            "h"     : 0.5
        }

        portrayal_worker = {
            "Shape" : "triangle_blue.png",
            "scale" : 0.8,
            "Layer" :0
        }
        if isinstance(Agent,Brick):
            return portrayal_brick
        elif isinstance(Agent,Audience):
            return portrayal_audience
        elif isinstance(Agent,Worker):
            return portrayal_worker
        else:
            return portrayal_individual


if __name__ == "__main__":
    beta = DiseaseModel.getBetaFunction(0.5,2)
    print(beta(4))