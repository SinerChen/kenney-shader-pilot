"""One-shot continuation: current scheduled Claude chain -> Kimi L3 checkpoint."""
import json
import os
from run import ROOT, worker, wait_if_paused, stamp
from state import save_json
from local_lock import file_lock


def main():
    runtime=ROOT/'runtime'
    record=runtime/'after_claude.json'
    with file_lock(runtime/'after_claude.lock',wait=False):
        upstream=json.loads((runtime/'after_sol.json').read_text(encoding='utf-8'))
        data=dict(status='waiting',pid=os.getpid(),created=stamp(),updated=stamp(),
                  predecessor='claude_main',predecessor_queue_created=upstream['created'],
                  model='kimi_retry_128k',levels=[3],mode='resume_checkpoint',
                  budget_per_level=dict(requests=80,checks=24))
        save_json(record,data)
        print('Waiting for the already scheduled Claude chain, including its wait for Sol.',flush=True)
        try:
            # This queue lock is held while waiting for Sol AND throughout Claude's run.
            # Waiting only on claude_main.lock could incorrectly start Kimi before Claude.
            with file_lock(runtime/'after_sol.lock'):
                upstream=json.loads((runtime/'after_sol.json').read_text(encoding='utf-8'))
                if upstream['created']!=data['predecessor_queue_created'] or upstream['status']!='finished':
                    raise RuntimeError('The scheduled Claude chain has not ended normally; Kimi has not started')
                wait_if_paused()
                data.update(status='running',updated=stamp(),started=stamp())
                save_json(record,data)
                processes=runtime/'processes.json'
                process_data=json.loads(processes.read_text(encoding='utf-8')) if processes.exists() else {'pids':{}}
                process_data.setdefault('pids',{})['kimi_retry_128k']=os.getpid()
                process_data['updated']=stamp();save_json(processes,process_data)
                worker('kimi_retry_128k',resume_errors=True,start_level=3)
            data.update(status='finished',updated=stamp(),finished=stamp())
            save_json(record,data)
        except Exception as error:
            data.update(status='error',updated=stamp(),error=str(error))
            save_json(record,data)
            raise


if __name__=='__main__': main()
