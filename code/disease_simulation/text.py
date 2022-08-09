import sys
import ctypes
import os
from typing import (
    Iterable , 
    Union   ,
    List
)

class CMD(object):
    __instance__ = None
    def __new__(cls,*args,**kwargs):
        
        if cls.__instance__ is  None:
            cls.__instance__ =  object.__new__(cls)
        return cls.__instance__

    def __init__(self):
        ...

    
    def execute(self,commands:Union[str,Iterable],isAdmin=True)->str:
        commands = [commands] if isinstance(commands,str) else commands
        if isAdmin and self.isAdmin() == False:
            ctypes.windll.shell32.ShellExecuteW(None,"runas",sys.executable,__file__,None,1)
        result_list:List[str] = []
        for command in commands:
            result_list.append(os.popen(command).read())
        return result_list


    @staticmethod
    def isAdmin():
        return ctypes.windll.shell32.IsUserAnAdmin()
if __name__ == "__main__":
    cmd = CMD()
    print(len(cmd.execute("netstat -ano")))
    cmd1 = CMD()
    print(cmd is cmd1)