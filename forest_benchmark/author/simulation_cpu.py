"""Independent state/event oracle using float64 arrays."""
import copy
import numpy as np
from model import defaults
from reference_cpu import evaluate


class Simulator:
    def __init__(self):
        self.reset({})

    def reset(self,config):
        self.p=defaults();self.p.update(copy.deepcopy(config))
        self.time=self.p["t0"];self.p["time"]=self.time
        self.state={};self.emitted=set();self.processed=set();self.births=[];self.ids=[]
        return {"status":"OK"}

    def eval(self,name,**values):
        p=copy.deepcopy(self.p);p.update(values)
        return evaluate(name,p)

    def advance(self,dt,events):
        self.p["time"]=self.time;self.p["dt"]=dt
        contacts=[];water=[];sources=[]
        for event in events:
            if event["type"]=="set":
                self.p.update(copy.deepcopy(event["values"]));continue
            eid=str(event.get("event_id",""))
            if not eid or eid in self.processed:continue
            self.processed.add(eid)
            if event["type"]=="contact":contacts.append(event["contact"])
            if event["type"]=="water":
                stamp=event["contact"].copy();stamp[6]=event["amount"]/dt;water.append(stamp)
            if event["type"]=="wave":sources.append(event["source"])
        task=self.p.get("task_id","A_L1");state=self.state;p=self.p
        if task.startswith("A"):
            state["burn_state"]=self.eval("burn_query",points=p["anchors"])
            if task.endswith("L2"):
                parts=state.get("particle_state",np.empty((0,6)))[:,:4].tolist()
                tr=np.array(p["instance_transform"]).reshape(4,4,order="F")
                for i,anchor in enumerate(p["anchors"]):
                    if p["enable_emission"] and i not in self.emitted and state["burn_state"][i,3]>=p["emit_threshold"]:
                        self.emitted.add(i);parts.append([*(tr@np.r_[anchor,1])[:3],0.])
                        self.ids.append(i);self.births.append({"anchor_id":i,"birth_time":self.time})
                state["particle_state"]=self.eval("particle_step",particles=parts) if parts else np.empty((0,6))
        if task.startswith("B"):
            depth=state["depth_field"][:,0] if "depth_field" in state else p["depth"]
            state["depth_field"]=self.eval("stamp_query",depth=depth,contacts=contacts)
            if task.endswith("L2"):
                wet=state["wetness_field"][:,0] if "wetness_field" in state else p["wetness"]
                source=self.eval("stamp_query",depth=p["source"],contacts=water,d_max=1e6)[:,0] if water else p["source"]
                state["wetness_field"]=self.eval("wet_step",depth=state["depth_field"][:,0],wetness=wet,source=source)
        if task=="D_L2":
            old=state["foam_field"][:,0] if "foam_field" in state else p["foam"]
            state["foam_field"]=self.eval("foam_step",foam=old)
        if task=="E_L2":
            h=state["wave_height_current"][:,0].copy() if "wave_height_current" in state else np.array(p["height"])
            prev=state["wave_height_prev"][:,0] if "wave_height_prev" in state else p["height_prev"]
            force=self.eval("foam_step",foam=np.zeros(len(h)),sources=sources)[:,1] if sources else p["force"]
            state["wave_height_current"]=self.eval("wave_step",height=h,height_prev=prev,force=force)
            state["wave_height_prev"]=h.reshape(-1,1)
            state["wave_normal"]=self.eval("wave_normal_query",height=state["wave_height_current"][:,0])
        self.time+=dt;self.p["time"]=self.time
        return {"status":"OK","time":self.time}

    def outputs(self):
        return {**self.state,"status":"OK","simulation_time":self.time,"birth_log":copy.deepcopy(self.births),
                "particle_ids":self.ids.copy(),"emitted":sorted(self.emitted)}

    def execute(self,commands):
        responses=[]
        for command in commands:
            op=command["op"]
            if op=="reset":response=self.reset(command["config"])
            elif op=="advance":response=self.advance(command["dt"],command.get("events",[]))
            elif op=="outputs" or (op=="query" and command["name"]=="state"):response=copy.deepcopy(self.outputs())
            elif op=="query":response=self.eval(command["name"],**command.get("payload",{}))
            else:raise ValueError(op)
            responses.append(response)
        return responses
