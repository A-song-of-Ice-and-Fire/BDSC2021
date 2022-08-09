import math
from typing import (
    Callable,
    Union ,

)
from text import CMD
class ToolBox:
    def __init__(self) -> None:
        pass
    
    '''
    getBetaFunction方法返回函数getBeta，该函数输入距离，输出对应的感染概率
    '''
    @staticmethod
    def getBetaFunction(beta_init:float,critical_distance:Union[int,float])->Callable[[Union[int,float]],float]:
        def getBeta(distance):
            if distance<=critical_distance:
                return beta_init
            else:
                return beta_init * math.exp(critical_distance-distance)
        return getBeta
    


        

if __name__ == "__main__":
    cmd = CMD()
    res = cmd.execute("netstat -ano | findstr 8521")[0].split("\n")
    pid_set = set()
    
    for res_str in res:
        if res_str.find(":") == -1:
            continue
        res_str = res_str.strip().split()
        pid = res_str[1].split(":")[-1]
        if pid == "8521":
            pid_set.add(res_str[-1])
    print(pid_set)
    for pid in pid_set:
        cmd.execute(f"taskkill -PID {pid} -F")
    
    print("结束进程成功！")

