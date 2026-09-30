#!/usr/bin/env python3
"""Build baseline or one experimental variant in a fresh local workspace."""
from pathlib import Path
import argparse, subprocess,sys,json,os
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'reproduce'))
from materialize import materialize
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--variant',choices=['baseline','e1','e2','e5'],default='baseline');a=p.parse_args()
w=materialize(a.output,source_only=True);source=w/'Implementation/Source Code/maven-root'
if a.variant!='baseline':
    # The fresh source copy can be inside the public repository's ignored work/.
    # Stop Git discovery before its parent so patch paths remain source-relative.
    patch_env=dict(os.environ,GIT_CEILING_DIRECTORIES=str(source.parent.resolve()))
    patch=ROOT/'reproduce/solver-variants'/(a.variant+'.patch')
    subprocess.run(['git','apply','--check',str(patch)],cwd=source,env=patch_env,check=True)
    subprocess.run(['git','apply',str(patch)],cwd=source,env=patch_env,check=True)
subprocess.run([sys.executable,str(w/'fetch_assets.py'),'--root',str(w),'--asset','dependencies'],check=True)
subprocess.run(['mvn','-B','-f',str(source/'mtsa/pom.xml'),'package','-DskipTests','-Djacoco.skip=true'],cwd=w,check=True)
print('Local source build completed; tests were compiled, not executed.')
print('JAR:',source/'mtsa/target/mtsa-1.0-SNAPSHOT.jar')
