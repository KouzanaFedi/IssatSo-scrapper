from concurrent.futures.thread import ThreadPoolExecutor
from concurrent.futures.process import ProcessPoolExecutor

from functools import partial
import time 

class ThreadPoolWrapper:

    def __init__(self,max_w):
        self.max_workers = max_w
        self.thread_executor = ThreadPoolExecutor(max_workers=self.max_workers)


class ConcurrentPipeline:



    def __init__(self,*args ):
        self.stages = []
        self.futures = {}
        self.commands_list = []
        for i in args: 
            if i<=0:
                raise ValueError("Number of workers cannot be 0")
            self.stages.append(ThreadPoolExecutor(max_workers=i))
            for stage in self.stages:
                self.futures[stage] =[]

    def terminateThread(self,future):
        result = future.result()
        print("Terminating "+ str(future))

    def pipeToNext(self,callback,pool,future):
        result = future.result()
        nextFuture = pool.submit(callback,result)
        self.futures[pool].append(nextFuture)


    def addToQueue(self,func,*callbacks):
        if len(self.stages)<=0:
            return
        self.commands_list.append((func,callbacks))



    def result(self,asDic = True):
        if len(self.stages)<=0:
            return None
        if len(self.commands_list)<=0:
            return None
        for cmnd in self.commands_list:
            future = self.stages[0].submit(cmnd[0])
            i = 0
            for callback in cmnd[1]:
                i+=1
                future.add_done_callback(partial(self.pipeToNext,callback,self.stages[i]))
            self.futures[self.stages[0]].append(future)
            future.add_done_callback(partial(self.terminateThread))

        
        for stage in self.stages:
            stage.shutdown()

        lst = []
        if(not asDic):
            for lastFuture in self.futures[self.stages[-1]]:
                lst.append(lastFuture.result())
            return lst
        
        dic = {}
        for lastFuture in self.futures[self.stages[-1]]:
            dic.update(lastFuture.result())
        return dic

    def shutdown(self):
        if len(self.stages)<=0:
            return
        self.stages[0].shutdown()