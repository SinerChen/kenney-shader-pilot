// Independent GPU implementation. The host prepends version, bindings and field indices.
float at(int key,int i) { return input_data[int(input_data[4+key])+i]; }
float s(int key) { return at(key,0); }
vec2 v2(int key,int i) { return vec2(at(key,i),at(key,i+1)); }
vec3 v3(int key,int i) { return vec3(at(key,i),at(key,i+1),at(key,i+2)); }
vec4 v4(int key,int i) { return vec4(at(key,i),at(key,i+1),at(key,i+2),at(key,i+3)); }
mat4 m4(int key) { return mat4(v4(key,0),v4(key,4),v4(key,8),v4(key,12)); }
int imod(int x,int n) { return ((x%n)+n)%n; }
int perm(int x) { return int(at(K_P,imod(x,256))); }
const vec3 gradients[12]=vec3[12](vec3(1,1,0),vec3(-1,1,0),vec3(1,-1,0),vec3(-1,-1,0),vec3(1,0,1),vec3(-1,0,1),vec3(1,0,-1),vec3(-1,0,-1),vec3(0,1,1),vec3(0,-1,1),vec3(0,1,-1),vec3(0,-1,-1));
float contribution(ivec3 cell,vec3 d) { return dot(gradients[perm(perm(perm(cell.x)+cell.y)+cell.z)%12],d); }
float noise3(vec3 x) {
    ivec3 b=ivec3(floor(x)); vec3 f=fract(x),u=f*f*f*(f*(f*6.-15.)+10.);
    float a[8];
    for(int k=0;k<2;k++) for(int j=0;j<2;j++) for(int i=0;i<2;i++)
        a[i+2*j+4*k]=contribution(b+ivec3(i,j,k),f-vec3(i,j,k));
    return mix(mix(mix(a[0],a[1],u.x),mix(a[2],a[3],u.x),u.y),mix(mix(a[4],a[5],u.x),mix(a[6],a[7],u.x),u.y),u.z);
}
vec4 burn_at(vec3 x,float t) {
    float sum=0.,weights=0.,weight=1.,frequency=s(K_base_frequency);
    for(int k=0;k<int(s(K_octaves));k++){sum+=weight*noise3(x*frequency);weights+=weight;weight*=s(K_gain);frequency*=s(K_lacunarity);}
    float n=sum/weights;
    float q=s(K_R0)+s(K_speed)*(t-s(K_t0))-length(x-v3(K_origin_ref,0))+s(K_noise_amplitude)*n;
    float b=s(K_enabled)>0.?smoothstep(-s(K_width),s(K_width),q):0.;
    return vec4(n,q,b,4.*b*(1.-b));
}
vec3 potential(vec3 x,float t) {
    vec3 q=s(K_frequency)*x+v3(K_drift,0)*t;
    return vec3(noise3(q+v3(K_offsets,0)),noise3(q+v3(K_offsets,3)),noise3(q+v3(K_offsets,6)));
}
vec3 curl_at(vec3 x,float t) {
    float e=s(K_epsilon);
    vec3 dx=(potential(x+vec3(e,0,0),t)-potential(x-vec3(e,0,0),t))/(2.*e);
    vec3 dy=(potential(x+vec3(0,e,0),t)-potential(x-vec3(0,e,0),t))/(2.*e);
    vec3 dz=(potential(x+vec3(0,0,e),t)-potential(x-vec3(0,0,e),t))/(2.*e);
    return vec3(dy.z-dz.y,dz.x-dx.z,dx.y-dy.x);
}
vec3 velocity_at(vec3 x,float t) { return vec3(0,s(K_up_speed),0)+s(K_curl_strength)*curl_at(x,t); }
float tex2(int key,vec2 uv,ivec2 dims,int channels,int channel,int mode) {
    if(mode==2 && (any(lessThan(uv,vec2(0)))||any(greaterThan(uv,vec2(1))))) return 0.;
    vec2 q=uv*vec2(dims)-.5; ivec2 b=ivec2(floor(q));vec2 w=fract(q);
    float values[4];
    for(int y=0;y<2;y++) for(int x=0;x<2;x++){
        ivec2 ij=b+ivec2(x,y);
        if(mode==1)ij=ivec2(imod(ij.x,dims.x),imod(ij.y,dims.y));
        else ij=clamp(ij,ivec2(0),dims-1);
        values[y*2+x]=at(key,(ij.y*dims.x+ij.x)*channels+channel);
    }
    return mix(mix(values[0],values[1],w.x),mix(values[2],values[3],w.x),w.y);
}
vec3 texture3(int key,vec2 uv,int mode) {
    ivec2 dims=ivec2(v2(K_texture_size,0));
    return vec3(tex2(key,uv,dims,3,0,mode),tex2(key,uv,dims,3,1,mode),tex2(key,uv,dims,3,2,mode));
}
ivec2 grid() {return ivec2(v2(K_grid_size,0));}
vec2 spacing() {return v2(K_domain_size,0)/vec2(grid());}
vec2 center(int index) {return v2(K_domain_min,0)+(vec2(index%grid().x,index/grid().x)+.5)*spacing();}
vec2 domain_uv(vec2 x) {return (x-v2(K_domain_min,0))/v2(K_domain_size,0);}
float field(int key,ivec2 ij) {ij=clamp(ij,ivec2(0),grid()-1);return at(key,ij.y*grid().x+ij.x);}
float lap(int key,ivec2 ij) {
    vec2 dd=spacing()*spacing();
    return (field(key,ij+ivec2(1,0))-2.*field(key,ij)+field(key,ij-ivec2(1,0)))/dd.x+
           (field(key,ij+ivec2(0,1))-2.*field(key,ij)+field(key,ij-ivec2(0,1)))/dd.y;
}
bool slab(vec3 o,vec3 d,vec3 lo,vec3 hi,out vec2 ab) {
    float a=0.,b=1e30;
    for(int axis=0;axis<3;axis++){
        if(abs(d[axis])<1e-10){if(o[axis]<lo[axis]||o[axis]>hi[axis]) {ab=vec2(0);return false;}}
        else {float u=(lo[axis]-o[axis])/d[axis],v=(hi[axis]-o[axis])/d[axis];a=max(a,min(u,v));b=min(b,max(u,v));}
    }
    ab=vec2(a,b);return b>a;
}
float density_at(vec3 world) {
    vec3 q=(m4(K_cloud_world_to_local)*vec4(world,1)).xyz;
    vec3 lo=v3(K_cloud_min,0),hi=v3(K_cloud_max,0);
    if(any(lessThan(q,lo))||any(greaterThan(q,hi)))return 0.;
    ivec3 size=ivec3(v3(K_density_size,0));
    vec3 f=(q-lo)/(hi-lo)*vec3(size)-.5;
    ivec3 b=ivec3(floor(f));f=fract(f);float value=0.;
    for(int z=0;z<2;z++)for(int y=0;y<2;y++)for(int x=0;x<2;x++){
        ivec3 ijk=clamp(b+ivec3(x,y,z),ivec3(0),size-1);
        float w=(x==1?f.x:1.-f.x)*(y==1?f.y:1.-f.y)*(z==1?f.z:1.-f.z);
        value+=w*at(K_density,(ijk.z*size.y+ijk.y)*size.x+ijk.x);
    } return value;
}
vec4 cloud_at(vec3 p,out bool valid) {
    mat4 tr=m4(K_cloud_world_to_local); vec3 L=v3(K_light_dir,0);vec2 ab;
    valid=slab((tr*vec4(p,1)).xyz,(tr*vec4(L,0)).xyz,v3(K_cloud_min,0),v3(K_cloud_max,0),ab);
    if(!valid)return vec4(0,0,0,1);
    float ds=(ab.y-ab.x)/s(K_cloud_steps),sum=0.;
    for(int i=0;i<int(s(K_cloud_steps));i++)sum+=density_at(p+(ab.x+(float(i)+.5)*ds)*L);
    float tau=s(K_cloud_sigma)*sum*ds;
    return vec4(ab,tau,exp(-tau));
}
void optical(vec3 I,vec3 N,vec3 x,out float F,out vec3 T,out vec3 R,out vec3 absorb,out float transmit,out vec2 uv,out float valid,out vec3 color) {
    float ci=-dot(I,N),ei=s(K_eta_i),et=s(K_eta_t),eta=ei/et,k=1.-eta*eta*(1.-ci*ci);
    transmit=1.;
    if(ei==et){F=0.;T=I;}
    else if(k<0.){F=1.;T=vec3(0);transmit=0.;}
    else{
        float ct=sqrt(k),rs=(ei*ci-et*ct)/(ei*ci+et*ct),rp=(et*ci-ei*ct)/(et*ci+ei*ct);
        F=.5*(rs*rs+rp*rp);T=eta*I+(eta*ci-ct)*N;
    }
    R=I+2.*ci*N;absorb=exp(-v3(K_sigma_a,0)*s(K_ell));
    vec4 clip=m4(K_view_projection)*vec4(x+s(K_ell)*T,1);
    uv=abs(clip.w)>1e-15?(clip.xy/clip.w*vec2(1,-1)+1.)*.5:vec2(0);
    valid=transmit>0. && clip.w>0. && all(greaterThanEqual(uv,vec2(0))) && all(lessThanEqual(uv,vec2(1))) && clip.z/clip.w>=0. && clip.z/clip.w<=1.?1.:0.;
    vec3 bg=valid>0.?texture3(K_color_texture,uv,0):v3(K_fallback_color,0);
    color=F*v3(K_reflection_color,0)+(1.-F)*absorb*bg;
}
void put(int base,int offset,vec3 value){for(int k=0;k<3;k++) output_data[base+offset+k]=value[k];}
void main() {
    int id=int(gl_GlobalInvocationID.x),op=int(input_data[0]),rows=int(input_data[1]),channels=int(input_data[2]);
    if(id>=rows)return;
    int b=id*channels; float t=s(K_time),dt=s(K_dt);
    if(op==0){
        vec4 v=burn_at(v3(K_points,id*3),t);for(int k=0;k<4;k++)output_data[b+k]=v[k];
    }else if(op==1){
        vec3 x=v3(K_points,id*3);put(b,0,curl_at(x,t));put(b,3,velocity_at(x,t));
    }else if(op==2){
        vec3 x=v3(K_particles,id*4);x+=dt*velocity_at(x+.5*dt*velocity_at(x,t),t+.5*dt);
        float age=at(K_particles,id*4+3)+dt;put(b,0,x);output_data[b+3]=age;output_data[b+4]=age<s(K_lifetime)?1.:0.;output_data[b+5]=max(0.,1.-age/s(K_lifetime));
    }else if(op==3){
        float value=at(K_depth,id);vec2 pos=center(id);
        for(int i=0;i<int(s(K_contact_count));i++){
            bool duplicate=false;for(int k=0;k<i;k++) if(at(K_contacts,k*7)==at(K_contacts,i*7))duplicate=true;
            if(duplicate)continue;
            int off=i*7;float a=at(K_contacts,off+3);vec2 delta=pos-v2(K_contacts,off+1);
            vec2 q=vec2(cos(a)*delta.x+sin(a)*delta.y,-sin(a)*delta.x+cos(a)*delta.y)/v2(K_contacts,off+4)+.5;
            value=min(s(K_d_max),value+at(K_contacts,off+6)*tex2(K_mask,q,ivec2(v2(K_mask_size,0)),1,0,2));
        }output_data[b]=value;
    }else if(op==4){
        vec2 start=v2(K_pom_rays,id*5),slope=vec2(at(K_pom_rays,id*5+2),at(K_pom_rays,id*5+4))/at(K_pom_rays,id*5+3);
        float previous=0.,hit=-1.;bool valid=true;
        vec2 u0=domain_uv(start);
        if(any(lessThan(u0,vec2(0)))||any(greaterThan(u0,vec2(1))))valid=false;
        if(valid && tex2(K_depth,u0,grid(),1,0,0)<=0.)hit=0.;
        if(valid && hit<0.)for(int step=1;step<=2048;step++){
            float depth=s(K_d_max)*float(step)/2048.;vec2 uv=domain_uv(start-depth*slope);
            if(any(lessThan(uv,vec2(0)))||any(greaterThan(uv,vec2(1)))){valid=false;break;}
            if(depth>=tex2(K_depth,uv,grid(),1,0,0)){
                float lo=previous,hi=depth;
                for(int j=0;j<20;j++){float mid=.5*(lo+hi);if(mid>=tex2(K_depth,domain_uv(start-mid*slope),grid(),1,0,0))hi=mid;else lo=mid;}
                hit=.5*(lo+hi);break;
            }previous=depth;
        }
        if(!valid||hit<0.)for(int k=0;k<6;k++)output_data[b+k]=0.;
        else{vec2 x=start-hit*slope,uv=domain_uv(x);output_data[b]=1.;output_data[b+1]=hit;output_data[b+2]=uv.x;output_data[b+3]=uv.y;output_data[b+4]=x.x;output_data[b+5]=x.y;}
    }else if(op==5){
        float w=at(K_wetness,id),lam=s(K_lambda0)/(1.+s(K_beta)*at(K_depth,id)/s(K_d_max));
        output_data[b]=clamp(w+dt*(s(K_diffusion)*lap(K_wetness,ivec2(id%grid().x,id/grid().x))-lam*w+at(K_source,id)),0.,1.);output_data[b+1]=lam;
    }else if(op==6){
        bool valid;vec4 value=cloud_at(v3(K_points,id*3),valid);output_data[b]=valid?1.:0.;
        for(int i=0;i<4;i++)output_data[b+1+i]=value[i];
    }else if(op==7){
        vec3 o=v3(K_view_rays,id*7),d=v3(K_view_rays,id*7+3),L=v3(K_light_dir,0);float opaque=at(K_view_rays,id*7+6);
        float g=s(K_g),phase=(1.-g*g)/(12.566370614359172*pow(1.+g*g-2.*g*dot(L,d),1.5));
        int n=int(s(K_view_steps));float T=1.;vec3 col=vec3(0);vec2 ab;
        for(int i=0;i<2*n;i++)output_data[b+5+i]=1.;
        if(slab(o,d,v3(K_fog_min,0),v3(K_fog_max,0),ab)){
            ab.y=min(ab.y,opaque);
            if(ab.y>ab.x){
                float ds=(ab.y-ab.x)/float(n),k=s(K_fog_density)*(s(K_fog_scatter)+s(K_fog_absorb));
                float attenuation=exp(-k*ds);
                float z=k*ds,integral=abs(z)<.001?ds*(1.-z*.5+z*z/6.-z*z*z/24.):(1.-attenuation)/k;
                for(int i=0;i<n;i++){
                    vec3 x=o+(ab.x+(float(i)+.5)*ds)*d;bool valid;float tc=cloud_at(x,valid).w;
                    vec2 light_ab;bool inside=slab(x,L,v3(K_fog_min,0),v3(K_fog_max,0),light_ab);float tl=inside?exp(-k*light_ab.y):1.;
                    vec3 j=s(K_fog_density)*s(K_fog_scatter)*v3(K_light_rgb,0)*tc*tl*phase;
                    col+=T*j*integral;T*=attenuation;
                    output_data[b+5+i]=tc;output_data[b+5+n+i]=tl;
                }
            }
        }output_data[b]=phase;put(b,1,col);output_data[b+4]=T;
    }else if(op==8){
        vec2 uv=v2(K_uvs,id*2),speed=vec2(tex2(K_flow,uv,grid(),2,0,0),tex2(K_flow,uv,grid(),2,1,0))/v2(K_domain_size,0);
        float p0=fract(t/s(K_period)+s(K_phase)),p1=fract(p0+.5),w0=1.-abs(2.*p0-1.),w1=1.-w0;
        vec2 q0=s(K_tiling)*(uv-s(K_period)*p0*speed),q1=s(K_tiling)*(uv-s(K_period)*p1*speed);
        vec3 col=w0*texture3(K_color_texture,q0,1)+w1*texture3(K_color_texture,q1,1);
        vec3 n=w0*texture3(K_normal_texture,q0,1)+w1*texture3(K_normal_texture,q1,1);if(s(K_normal_encoded)>0.)n=2.*n-1.;n=normalize(n);
        output_data[b]=q0.x;output_data[b+1]=q0.y;output_data[b+2]=q1.x;output_data[b+3]=q1.y;output_data[b+4]=w0;output_data[b+5]=w1;put(b,6,col);put(b,9,n);
    }else if(op==9){
        vec2 pos=center(id),q=pos-dt*v2(K_flow,id*2);float source=0.;
        for(int i=0;i<int(s(K_source_count));i++){vec2 delta=pos-v2(K_sources,4*i);float radius=at(K_sources,4*i+2),v=max(0.,1.-dot(delta,delta)/(radius*radius));source+=at(K_sources,4*i+3)*v*v;}
        output_data[b]=clamp(tex2(K_foam,domain_uv(q),grid(),1,0,2)*exp(-s(K_decay)*dt)+dt*source,0.,1.);output_data[b+1]=source;
    }else if(op==10){
        float F,has,valid;vec3 T,R,A,C;vec2 uv;
        optical(v3(K_optical_rays,id*9),v3(K_optical_rays,id*9+3),v3(K_optical_rays,id*9+6),F,T,R,A,has,uv,valid,C);
        output_data[b]=F;put(b,1,T);put(b,4,R);put(b,7,A);output_data[b+10]=has;output_data[b+11]=uv.x;output_data[b+12]=uv.y;output_data[b+13]=valid;put(b,14,C);
    }else if(op==11){
        float h=at(K_height,id),old=at(K_height_prev,id);
        output_data[b]=(2.-s(K_gamma)*dt)*h-(1.-s(K_gamma)*dt)*old+s(K_wave_speed)*s(K_wave_speed)*dt*dt*lap(K_height,ivec2(id%grid().x,id/grid().x))+dt*dt*at(K_force,id);
    }else if(op==12){
        ivec2 ij=ivec2(id%grid().x,id/grid().x);vec2 step=spacing();
        vec3 n=normalize(vec3(-(field(K_height,ij+ivec2(1,0))-field(K_height,ij-ivec2(1,0)))/(2.*step.x),1.,-(field(K_height,ij+ivec2(0,1))-field(K_height,ij-ivec2(0,1)))/(2.*step.y)));
        put(b,0,n);
    }
}
