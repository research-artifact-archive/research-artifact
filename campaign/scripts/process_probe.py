#!/usr/bin/env python3
"""Check RSS and terminate a Python parent with a live child JVM on this host."""
from pathlib import Path
import argparse, csv, ctypes, json, os, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Implementation/Experiment/FSE2027/scripts'))
from harness_common import process_group_popen_kwargs, process_rss_kib, process_memory_probe_kind, terminate_process_tree

def alive(pid):
    if os.name=='nt':
        api=ctypes.WinDLL('kernel32',use_last_error=True)
        api.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong];api.OpenProcess.restype=ctypes.c_void_p
        api.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
        api.CloseHandle.argtypes=[ctypes.c_void_p]
        handle=api.OpenProcess(0x1000,False,pid)
        if not handle:return False
        code=ctypes.c_ulong()
        try:return bool(api.GetExitCodeProcess(handle,ctypes.byref(code))) and code.value==259
        finally:api.CloseHandle(handle)
    result=subprocess.run(['ps','-o','stat=','-p',str(pid)],capture_output=True,text=True)
    return bool(result.stdout.strip()) and not result.stdout.strip().startswith('Z')

def main():
    p=argparse.ArgumentParser();p.add_argument('--java',default='java');p.add_argument('--output',type=Path,required=True);p.add_argument('--child',action='store_true');a=p.parse_args()
    if a.child:
        child=subprocess.Popen([a.java,str(ROOT/'scripts/PortableProcessProbe.java')],stdout=subprocess.PIPE,text=True)
        ready=child.stdout.readline().strip()
        print(json.dumps(dict(child_pid=child.pid,ready=ready)),flush=True)
        child.wait();return
    a.output.parent.mkdir(parents=True,exist_ok=True)
    process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--child','--java',a.java,'--output',str(a.output)],stdout=subprocess.PIPE,text=True,**process_group_popen_kwargs())
    child_pid=None
    try:
        # Source-file launcher compiles this tiny infrastructure probe; never part of timing.
        import threading, queue
        lines=queue.Queue()
        threading.Thread(target=lambda:lines.put(process.stdout.readline()),daemon=True).start()
        details=json.loads(lines.get(timeout=40));child_pid=details['child_pid']
        if details.get('ready')!='ready':raise RuntimeError('Child JVM did not start')
        rss=process_rss_kib(child_pid)
        action=terminate_process_tree(process)
        deadline=time.monotonic()+8
        while alive(child_pid) and time.monotonic()<deadline:time.sleep(.1)
        result=dict(platform=sys.platform,parent_pid=process.pid,child_jvm_pid=child_pid,
                    child_jvm_rss_kib=rss,rss_probe=process_memory_probe_kind(),termination_action=action,
                    parent_terminated=process.poll() is not None,child_jvm_terminated=not alive(child_pid),
                    passed=process.poll() is not None and not alive(child_pid) and rss is not None and rss>0)
        with a.output.open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=list(result));writer.writeheader();writer.writerow(result)
        print(json.dumps(result),flush=True)
        if not result['passed']:raise RuntimeError('RSS/process-tree probe failed')
    finally:
        if process.poll() is None:terminate_process_tree(process)
        if child_pid is not None and alive(child_pid):
            # Cleanup only the child created by this infrastructure probe.
            if os.name=='nt':subprocess.run(['taskkill','/PID',str(child_pid),'/T','/F'],capture_output=True)
            else:
                import signal
                try:os.kill(child_pid,signal.SIGKILL)
                except ProcessLookupError:pass
if __name__=='__main__':main()
