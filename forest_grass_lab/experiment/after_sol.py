"""User-requested one-shot queue: wait for Sol to exit, then rerun Claude L1-L3."""
import os
import json
from pathlib import Path
from run import ROOT, worker, wait_if_paused, stamp
from state import save_json
from local_lock import file_lock


def main():
    runtime=ROOT/'runtime'
    record=runtime/'after_sol.json'
    with file_lock(runtime/'after_sol.lock',wait=False):
        data=dict(status='waiting',pid=os.getpid(),created=stamp(),updated=stamp(),
                  predecessor='openai_main',model='claude_main',mode='fresh_rerun',levels=[1,2,3],
                  budget_per_level=dict(requests=80,checks=24))
        save_json(record,data)
        print('Waiting for the Sol worker to finish its chain.',flush=True)
        try:
            # Sol holds this lock for its whole L1->L2->L3 worker, including HTTP waits.
            # Retain it while running Claude to enforce the requested serial order.
            with file_lock(runtime/'openai_main.lock'):
                wait_if_paused()
                data.update(status='running',updated=stamp(),started=stamp())
                save_json(record,data)
                processes=runtime/'processes.json'
                process_data=json.loads(processes.read_text(encoding='utf-8')) if processes.exists() else {'pids':{}}
                process_data.setdefault('pids',{})['claude_main']=os.getpid()
                process_data['updated']=stamp()
                save_json(processes,process_data)
                print('Sol worker ended. Archiving old Claude output and starting a fresh chain.',flush=True)
                worker('claude_main',restart_all=True)
            data.update(status='finished',updated=stamp(),finished=stamp())
            save_json(record,data)
        except Exception as error:
            data.update(status='error',updated=stamp(),error=str(error))
            save_json(record,data)
            raise


if __name__=='__main__': main()
