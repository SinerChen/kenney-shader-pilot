"""Real faulty implementations; private controls, never model attachments."""
from pathlib import Path
import json
import shutil
from numeric_backend import ROOT,write_json
from judge import numeric
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workspace_layout import copy_public

# (id, source file, exact replacement, faulty replacement, detector)
MUTATIONS={
"A_L1":[
 ("global_black","kernel.txt","float b=s(K_enabled)>0.?smoothstep(-s(K_width),s(K_width),q):0.;","float b=clamp(t*.2,0.,1.);","numeric"),
 ("moving_noise","kernel.txt","noise3(x*frequency)","noise3(x*frequency+vec3(t))","numeric"),
 ("camera_locked","display.gd","adapter._dispatch(\"burn_query\",{\"points\":points})","adapter._dispatch(\"burn_query\",{\"points\":points,\"origin_ref\":[bridge.camera.position.x*.2,0.,0.]})","camera_state"),
 ("fake_probe","display.gd",'texture(burn,[0,1,2,3],DISPLAY_SIZE)','constant_texture(Vector4(0,0,.4,.1))',"display_dependency"),
],
"A_L2":[
 ("fixed_emitter","adapter.gd","var pos = transform*Vector3(a[0],a[1],a[2])","var pos = Vector3.ZERO","numeric"),
 ("charred_emitter","adapter.gd","front[i][3] >= config.emit_threshold","front[i][2] >= config.emit_threshold","numeric"),
 ("delete_stock","adapter.gd",'if state.has("particle_state"):\n\t\t\t\tfor row','if not config.enable_emission: state.erase("particle_state")\n\t\t\tif state.has("particle_state"):\n\t\t\t\tfor row',"numeric"),
 ("euler","kernel.txt","x+=dt*velocity_at(x+.5*dt*velocity_at(x,t),t+.5*dt)","x+=dt*velocity_at(x,t)","numeric"),
 ("repeat_birth","adapter.gd"," and not emitted.has(i)","", "numeric"),
],
"B_L1":[
 ("decal_only","kernel.txt","output_data[b]=value;","output_data[b]=0.;","numeric"),
 ("clear_depth","adapter.gd",'_column(state.depth_field,0) if state.has("depth_field") else config.depth',"config.depth","numeric"),
 ("duplicate_stamp","kernel.txt","if(duplicate)continue;","if(false)continue;","numeric"),
 ("wrong_pom_sign","kernel.txt","start-depth*slope","start+depth*slope","numeric"),
 ("constant_offset","kernel.txt","hit=.5*(lo+hi);break;","hit=s(K_d_max);break;","numeric"),
],
"B_L2":[
 ("ignore_depth","kernel.txt","lam=s(K_lambda0)/(1.+s(K_beta)*at(K_depth,id)/s(K_d_max))","lam=s(K_lambda0)","numeric"),
 ("global_wet","display.gd","float wet=b.x;","float wet=1.;","display_dependency"),
 ("source_only","kernel.txt","w+dt*(s(K_diffusion)*lap(K_wetness,ivec2(id%grid().x,id/grid().x))-lam*w+at(K_source,id))","dt*at(K_source,id)","numeric"),
 ("directional_update","kernel.txt","s(K_diffusion)*lap(K_wetness,ivec2(id%grid().x,id/grid().x))","s(K_diffusion)*(lap(K_wetness,ivec2(id%grid().x,id/grid().x))+(field(K_wetness,ivec2(id%grid().x-1,id/grid().x))-w)/spacing().x)","numeric"),
 ("style_changes_state","kernel.txt","float w=at(K_wetness,id)","float w=at(K_wetness,id)*s(K_dry_roughness)","numeric"),
],
"C_L1":[
 ("independent_shadow","kernel.txt","float tau=s(K_cloud_sigma)*sum*ds;","float tau=abs(sin(p.x+p.z));","numeric"),
 ("density_slice","kernel.txt","vec3 f=(q-lo)/(hi-lo)*vec3(size)-.5;","q.y=.5*(lo.y+hi.y); vec3 f=(q-lo)/(hi-lo)*vec3(size)-.5;","numeric"),
 ("omit_length","kernel.txt","s(K_cloud_sigma)*sum*ds","s(K_cloud_sigma)*sum","numeric"),
 ("darken_ambient","display.gd","vec3 color=base_color+secondary_color*a.x;","vec3 color=(base_color+secondary_color)*a.x;","ambient_preservation"),
 ("negative_start","kernel.txt","float a=0.,b=1e30;","float a=-1e30,b=1e30;","numeric"),
],
"C_L2":[
 ("shared_opacity","kernel.txt","output_data[b+4]=T;","output_data[b+4]=T*output_data[b+5];","numeric"),
 ("fake_cloud","kernel.txt","float tc=cloud_at(x,valid).w;","float tc=1.;","numeric"),
 ("phase_reversed","kernel.txt","-2.*g*dot(L,d)","+2.*g*dot(L,d)","numeric"),
 ("omit_sun_fog","kernel.txt","float tl=inside?exp(-k*light_ab.y):1.;","float tl=1.;","numeric"),
 ("double_shadow","display.gd","vec3 color=base_color+secondary_color*a.x;","vec3 color=base_color+secondary_color*a.x*a.x;","shadow_linearity"),
],
"D_L1":[
 ("single_phase","kernel.txt","vec3 col=w0*texture3(K_color_texture,q0,1)+w1*texture3(K_color_texture,q1,1);","vec3 col=texture3(K_color_texture,q0,1);","numeric"),
 ("bad_weights","kernel.txt","w1=1.-w0;","w1=1.;","numeric"),
 ("decode_velocity","kernel.txt","/v2(K_domain_size,0);\n        float p0","*2.-vec2(1.);\n        float p0","numeric"),
 ("srgb_normal","kernel.txt","n=normalize(n);","n=normalize(sign(n)*pow(abs(n),vec3(2.2)));","numeric"),
 ("unbounded_uv","kernel.txt","p0=fract(t/s(K_period)+s(K_phase))","p0=t/s(K_period)+s(K_phase)","numeric"),
],
"D_L2":[
 ("moving_source","kernel.txt","vec2 delta=pos-v2(K_sources,4*i);","vec2 delta=pos-v2(K_sources,4*i)-t*v2(K_flow,id*2);","numeric"),
 ("source_only","kernel.txt","tex2(K_foam,domain_uv(q),grid(),1,0,2)*exp(-s(K_decay)*dt)+dt*source","dt*source","numeric"),
 ("carry_field_with_source","kernel.txt","q=pos-dt*v2(K_flow,id*2)","q=pos-dt*v2(K_flow,id*2)-v2(K_sources,0)","numeric"),
 ("tiling_velocity","kernel.txt","q=pos-dt*v2(K_flow,id*2)","q=pos-dt*v2(K_flow,id*2)*s(K_tiling)","numeric"),
 ("forward_sample","kernel.txt","q=pos-dt*v2(K_flow,id*2)","q=pos+dt*v2(K_flow,id*2)","numeric"),
],
"E_L1":[
 ("schlick","kernel.txt","F=.5*(rs*rs+rp*rp);","F=pow((ei-et)/(ei+et),2.)+(1.-pow((ei-et)/(ei+et),2.))*pow(1.-ci,5.);","numeric"),
 ("eta_inverse","kernel.txt","eta=ei/et","eta=et/ei","numeric"),
 ("no_directional_refraction","kernel.txt","vec4(x+s(K_ell)*T,1)","vec4(x,1)","numeric"),
 ("clamp_invalid_uv","kernel.txt","vec3 bg=valid>0.?texture3","uv=clamp(uv,vec2(0),vec2(1)); valid=transmit; vec3 bg=valid>0.?texture3","numeric"),
 ("fake_probe","display.gd","float f=texture(optical_f,UV).r;","uv=vec4(UV,1.,0.); float f=.1;","display_dependency"),
],
"E_L2":[
 ("loop_wave","kernel.txt","output_data[b]=(2.-s(K_gamma)*dt)*h","output_data[b]=sin(t+float(id))*.01+(2.-s(K_gamma)*dt)*h","numeric"),
 ("stale_background","bridge.gd","SubViewport.UPDATE_ALWAYS","SubViewport.UPDATE_ONCE","layer_current"),
 ("missing_rear","bridge.gd",'else "RearCapture"\n\treturn capture_views','else "OpaqueCapture"\n\treturn capture_views',"layer_current"),
 ("hide_front","display.gd","if(visibility<.5)discard;","if(front || visibility<.5)discard;","display_dependency"),
 ("recursive_capture","bridge.gd",'else 3\n','else 7\n',"layer_exclusion"),
],
}


def build(task,mutation):
    name,file,old,new,detector=mutation
    source=ROOT/"author/references"/task/"gpu_solution"
    destination=ROOT/"author/mutations"/task/name/"project"
    shutil.copytree(source,destination,dirs_exist_ok=True,ignore=shutil.ignore_patterns(".godot"))
    copy_public(source,destination)
    path=destination/("fixture" if file=="bridge.gd" else "solution")/file
    text=path.read_text(encoding="utf-8")
    if old not in text:raise ValueError(f"Mutation not applied: {task}/{name}")
    if name=="shared_opacity":text=text.replace("writeonly buffer Output","buffer Output")
    text=text.replace(old,new)
    path.write_text(text,encoding="utf-8")
    if file=="kernel.txt":
        import re
        from gold import kernel_subset
        wire_path=destination/"solution/wire.json"
        wire=json.loads(wire_path.read_text(encoding="utf-8"))
        for opcode,operation in enumerate(wire["operations"]):
            subset=kernel_subset(text,[opcode])
            used=set(re.findall(r"K_(\w+)",subset[subset.index("float at("):]))
            used.update(["time","dt"])
            wire["fields_by_operation"][operation]=sorted(used)
        write_json(wire_path,wire)
    write_json(destination.parent/"mutation.json",{"task":task,"name":name,"file":str(path.relative_to(destination)),"detector":detector,"source_occurrences":text.count(new)})
    return destination


def run_numeric_controls():
    results=[]
    for task,mutations in MUTATIONS.items():
        for mutation in mutations:
            project=build(task,mutation)
            name=mutation[0]
            if mutation[-1]!="numeric":
                results.append({"task":task,"mutation":name,"status":"NOT_RUN","detector":mutation[-1]});continue
            try:
                report=numeric(task,project,tag="mutations/"+name)
                rejected=report["pass"]<report["total"]
                results.append({"task":task,"mutation":name,"status":"REJECTED" if rejected else "SURVIVED","numeric_pass":report["pass"],"total":report["total"]})
            except Exception as exc:
                # A broken control is not proof that the judge rejects the intended defect.
                results.append({"task":task,"mutation":name,"status":"CONTROL_ERROR","error":str(exc)})
            print(task,name,results[-1]["status"],flush=True)
    write_json(ROOT/"author/reports/mutations_numeric.json",results)
    return results


if __name__=="__main__":run_numeric_controls()
