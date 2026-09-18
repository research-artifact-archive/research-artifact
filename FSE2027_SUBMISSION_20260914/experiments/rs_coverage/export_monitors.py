#!/usr/bin/env python3
"""Compile/export safety DFAs only; no controller/endpoint synthesis or campaign replay."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,time
HERE=Path(__file__).resolve().parent;SUBMISSION=HERE.parents[1]
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as stream:
  for data in iter(lambda:stream.read(1024*1024),b''):h.update(data)
 return h.hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repository',type=Path,default=SUBMISSION.parent)
 p.add_argument('--output',type=Path,default=HERE/'raw/expanded-predicates');p.add_argument('--jar',type=Path)
 a=p.parse_args();config=json.loads((HERE.parent/'rq3_xeon/configs/rq3.json').read_text())
 def anonymous(text):
  return text.replace(str(HERE),'<MODULE>').replace(str(a.repository.resolve()),'<REPOSITORY>').replace(str(Path.home()),'<USER_HOME>')
 env=json.loads((HERE.parent/'rq3_xeon/raw/rq3/environment.json').read_text());jar=a.jar or a.repository/config['classpath']
 if sha(jar)!=env['classpath']['sha256']:raise ValueError('Require the fixed experimental JAR for the exact frontend export')
 a.output.mkdir(parents=True,exist_ok=True)
 if any(a.output.glob('*.json')) or any(a.output.glob('*.log')):raise FileExistsError('Require a fresh output directory')
 classes=HERE/'build/classes';classes.mkdir(parents=True,exist_ok=True)
 compile_cmd=['javac','-cp',str(jar),'-d',str(classes),str(HERE/'cli/RsCoverageExport.java')]
 c=subprocess.run(compile_cmd,capture_output=True,text=True,timeout=60)
 (a.output/'compile.log').write_text(anonymous('COMMAND='+json.dumps(compile_cmd)+'\n'+c.stdout+c.stderr+'\nEXIT='+str(c.returncode)+'\n'))
 c.check_returncode()
 for model in config['models']:
  inp=a.repository/model['path'];target=a.output/(model['id']+'.json');log=a.output/(model['id']+'.log')
  if sha(inp)!=env['model_input_bytes'][model['path']]:raise ValueError('Input bytes differ: '+model['id'])
  if target.exists() or log.exists():raise FileExistsError('Refusing overwrite: '+str(target))
  command=['java','-Xmx2g','-Djava.awt.headless=true','-cp',os.pathsep.join([str(classes),str(jar)]),
           'ltsa.lts.RsCoverageExport',str(inp),str(target)]
  start=time.monotonic()
  try:
   run=subprocess.run(command,capture_output=True,text=True,timeout=60)
   log.write_text(anonymous('MODE=read-only monitor compilation; synthesis=false\nJAR_SHA256='+sha(jar)+'\nINPUT_SHA256='+sha(inp)+'\nCOMMAND='+json.dumps(command)+'\n'+
       run.stdout+run.stderr+'\nEXIT='+str(run.returncode)+'\nELAPSED='+str(time.monotonic()-start)+'\n'))
   print(model['id'],run.returncode,flush=True);run.check_returncode()
  except subprocess.TimeoutExpired as error:
   log.write_text(anonymous('TIMEOUT at 60 seconds; no synthesis was requested\n'+str(error)));raise
if __name__=='__main__':main()
