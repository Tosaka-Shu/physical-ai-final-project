"""Normalize aspect ratio and concatenate supplied OP/body/ED, retaining source audio."""
import argparse,json,subprocess,tempfile
from pathlib import Path

def probe(path):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))

def compose(opening,body,ending,output):
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    sources=[opening,body,ending];report={'parts':[]}
    with tempfile.TemporaryDirectory() as tmp:
        for i,src in enumerate(sources):
            info=probe(src);duration=float(info['format']['duration']);audio=any(s['codec_type']=='audio' for s in info['streams'])
            dest=Path(tmp)/f'{i}.mp4'
            cmd=['ffmpeg','-v','error','-y','-i',str(src)]
            if not audio:cmd+=['-f','lavfi','-i','anullsrc=r=48000:cl=stereo']
            cmd+=['-map','0:v:0','-map','0:a:0' if audio else '1:a:0','-vf',
                  'scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30',
                  '-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','-af','apad','-t',str(duration),str(dest)]
            subprocess.run(cmd,check=True)
            report['parts'].append({'source':str(src),'duration_s':duration,'source_audio':audio,'audio_policy':'retain' if audio else 'silence'})
        listing=Path(tmp)/'concat.txt';listing.write_text(''.join(f"file '{i}.mp4'\n" for i in range(3)))
        subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(listing),'-c','copy','-movflags','+faststart',str(output)],check=True)
    subprocess.run(['ffmpeg','-v','error','-i',str(output),'-f','null','-'],check=True)
    info=probe(output);report['final_duration_s']=float(info['format']['duration']);report['decode']='passed';report['streams']=[{k:s[k] for k in ['codec_type','codec_name','width','height'] if k in s} for s in info['streams']]
    assert abs(report['final_duration_s']-sum(r['duration_s'] for r in report['parts']))<.3
    output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--opening',default='assets/opening.mp4');p.add_argument('--ending',default='assets/ending.mp4');p.add_argument('--body',required=True);p.add_argument('--output',default='submission/final_demo.mp4');a=p.parse_args()
    print(json.dumps(compose(a.opening,a.body,a.ending,a.output),indent=2))
