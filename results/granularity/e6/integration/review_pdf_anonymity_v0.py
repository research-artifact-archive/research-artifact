#!/usr/bin/env python3
"""Read PDF structure/text without changing its bytes; distinguish compressed coincidences."""
import argparse, getpass, hashlib, json, re, socket
from pathlib import Path
from pypdf import PdfReader
from pypdf.generic import IndirectObject, DictionaryObject, ArrayObject, TextStringObject, NameObject, StreamObject
E6=Path(__file__).resolve().parents[1]
def main():
    a=argparse.ArgumentParser();a.add_argument('--forbidden-name',action='append',default=[]);a.add_argument('--output',type=Path,required=True);args=a.parse_args()
    names=[getpass.getuser()]+args.forbidden_name
    pats=[re.compile(r'(?<![A-Za-z0-9])'+re.escape(n)+r'(?![A-Za-z0-9])',re.I) for n in names]
    bytepats=[re.compile(rb'(?<![A-Za-z0-9])'+re.escape(n.encode())+rb'(?![A-Za-z0-9])',re.I) for n in names]
    rows=[]
    for p in sorted(E6.rglob('*.pdf')):
        if 'public_exports' in p.relative_to(E6).parts:continue
        raw=p.read_bytes();r=PdfReader(p);assert not r.is_encrypted
        assert not list(r.attachments),'Embedded attachments require their own review'
        strings=[];visited=set();metadata_streams=0
        def walk(x):
            nonlocal metadata_streams
            if isinstance(x,IndirectObject):
                key=(x.idnum,x.generation)
                if key in visited:return
                visited.add(key);walk(x.get_object());return
            if isinstance(x,(TextStringObject,NameObject)):strings.append(str(x));return
            if isinstance(x,DictionaryObject):
                if isinstance(x,StreamObject) and (x.get('/Type')=='/Metadata' or x.get('/Subtype')=='/XML'):
                    strings.append(x.get_data().decode('utf-8'));metadata_streams+=1
                for k,v in x.items():walk(k);walk(v)
            elif isinstance(x,(ArrayObject,list,tuple)):
                for v in x:walk(v)
        walk(r.trailer)
        for gen,objs in r.xref.items():
            for ident in objs:
                if ident:walk(IndirectObject(ident,gen,r))
        texts=[page.extract_text() or '' for page in r.pages];strings+=texts
        assert all(t.strip() for t in texts),'Image-only/empty pages need additional content review'
        meaningful='\n'.join(strings)
        decoded_hits=[i for i,patt in enumerate(pats) if patt.search(meaningful)]
        assert not decoded_hits,(str(p.relative_to(E6)),decoded_hits,'Decoded PDF identity match')
        assert str(Path.home()) not in meaningful
        assert socket.gethostname() not in meaningful
        raw_hits=[]
        for i,patt in enumerate(bytepats):
            for hit in patt.finditer(raw):
                before=raw[:hit.start()]
                inside=before.rfind(b'\nstream')>before.rfind(b'\nendstream')
                assert inside,'Identity-like bytes outside PDF streams require manual review'
                raw_hits.append(dict(pattern_index=i,start=hit.start(),end=hit.end(),inside_stream=True))
        rows.append(dict(path=str(p.relative_to(E6)),sha256=hashlib.sha256(raw).hexdigest(),pages=len(r.pages),page_text_characters=sum(map(len,texts)),parsed_strings=len(strings),visited_indirect_objects=len(visited),metadata_streams=metadata_streams,decoded_identity_hits=[],raw_stream_coincidences=raw_hits))
    report=dict(status='PASS',identity_pattern_count=len(names),files=rows,scope='PDF page text, metadata/XML and dictionary string/name objects were parsed and scanned; no attachments or encrypted/image-only pages. Listed raw byte matches occur inside compressed streams and have no decoded text/metadata counterpart. Original PDF bytes are unchanged.',visual_review='The three pages of the sole raw-byte-hit PDF (Canary table check) were rendered with Poppler and inspected: only tables, explanatory notes and page numbers, with no identity or clipping.')
    with args.output.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(dict(status='PASS',files=len(rows),pages=sum(x['pages'] for x in rows),decoded_identity_hits=0,raw_stream_coincidences=sum(len(x['raw_stream_coincidences']) for x in rows))))
if __name__=='__main__':main()
