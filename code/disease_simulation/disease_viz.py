from mesa.visualization.modules import CanvasGrid
from mesa.visualization.ModularVisualization import ModularServer
from mesa.visualization.modules import ChartModule
from disease_model import *
from typing import Dict, NoReturn,Union
import time
import os
def agent_portrayal(agent):
    if not agent.pos:
        return None
    
    
    portrayal = DiseaseModel.getBasePortrayal(agent)
    if isinstance(agent,Worker) and agent.disease_status == DiseaseStatus.I:
        portrayal["Shape"] = "triangle_red.png"
    if isinstance(agent,Individual) and agent.disease_status == DiseaseStatus.I:      #只支持圆和正方形
        portrayal["Color"] = "red"
    
    return portrayal


def run(space_params:Dict[str,Tuple[int,int]],
        population_params:Dict[str,List[int]],
        disease_params:Dict[str,Union[int,Callable[[float],float]]],
        log_params:Dict[str,Union[str,Iterable]],
        *,
        is_viz = True,
        seed = time.time(),
        load_port=8521) -> NoReturn:        
    '''
    space_params:size_by_grid ,  size_by_pixel 
    population_params:individual_nums , init_I_nums ,avg_end_distance=300
    disease_params:infect_scope , getBeta  , min_contact_distance
    '''
    space_viz = CanvasGrid(agent_portrayal,*space_params["size_by_grid"],*space_params["size_by_pixel"])
    chart_viz = ChartModule(
    [{"Label" : "s_ratio" , "Color" : "green"} , {"Label" : "i_ratio" , "Color" : "red"}] ,
    data_collector_name="data_collector"
    )

    model_params = {**population_params , **disease_params,**log_params}
    model_params["grid_size"] = space_params["size_by_grid"]
    model_params["seed"] = seed

    if is_viz:
        server = ModularServer(
            DiseaseModel,
            [space_viz,chart_viz],
            DiseaseModel.__name__,
            model_params
        )
        server.port = load_port
        try:
            server.launch()
        except OSError as e:
            res = os.popen(f"netstat -ano | findstr {load_port}").read().split("\n")
            pid_set = set()
            for res_str in res:
                if res_str.find(":") == -1:
                    continue
                res_str = res_str.strip().split()
                pid = res_str[1].split(":")[-1]
                if pid == "8521":
                    pid_set.add(res_str[-1])
                
            for pid in pid_set:
                os.popen(f"taskkill -PID {pid} -F")
            print(e)
            server.launch()
    else:
        model = DiseaseModel(**model_params)
        while model.schedule.steps <= model_params["step_in_record"]:
            model.step()
            print(f"cur_step:{model.schedule.steps}")
