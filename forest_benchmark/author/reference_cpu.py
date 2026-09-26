"""Independent float64 oracle. Never export this module to a solver."""
import math
from itertools import product
import numpy as np

G = np.array([(1,1,0),(-1,1,0),(1,-1,0),(-1,-1,0),(1,0,1),(-1,0,1),
              (1,0,-1),(-1,0,-1),(0,1,1),(0,-1,1),(0,1,-1),(0,-1,-1)], float)


def sample2(a, uv, mode="clamp"):
    a = np.asarray(a, dtype=float)
    nz, nx = a.shape[:2]
    uv = np.asarray(uv)
    if mode == "zero" and (np.any(uv < 0) or np.any(uv > 1)):
        return np.zeros(a.shape[2:]) if a.ndim > 2 else 0.
    q = uv * [nx, nz] - .5
    base = np.floor(q).astype(int)
    f = q - base
    result = 0.
    for y, x in product(range(2), repeat=2):
        ij = base + [x, y]
        ij = ij % [nx,nz] if mode == "repeat" else np.clip(ij, 0, [nx-1,nz-1])
        result = result + a[ij[1],ij[0]] * (f[0] if x else 1-f[0]) * (f[1] if y else 1-f[1])
    return result


def noise(x, p):
    base = np.floor(x).astype(int)
    frac = x-base
    fade = frac**3*(frac*(frac*6-15)+10)
    value = 0.
    for k,j,i in product(range(2), repeat=3):
        cell=base+[i,j,k]
        index=int(p[(int(p[(int(p[cell[0]%256])+cell[1])%256])+cell[2])%256])%12
        weight=np.prod([fade[axis] if bit else 1-fade[axis] for axis,bit in enumerate((i,j,k))])
        value += weight*np.dot(G[index],frac-[i,j,k])
    return value


def burn(points, p):
    result=[]
    for point in np.asarray(points):
        weights=p["gain"]**np.arange(p["octaves"])
        n=sum(w*noise(point*p["base_frequency"]*p["lacunarity"]**k,p["P"]) for k,w in enumerate(weights))/sum(weights)
        q=p["R0"]+p["speed"]*(p["time"]-p["t0"])-np.linalg.norm(point-p["origin_ref"])+p["noise_amplitude"]*n
        b=np.clip((q+p["width"])/(2*p["width"]),0,1)
        b=b*b*(3-2*b) if p["enabled"] else 0.
        result.append([n,q,b,4*b*(1-b)])
    return np.array(result)


def curl(x, t, p):
    def potential(q):
        return np.array([noise(p["frequency"]*q+np.array(p["drift"])*t+offset,p["P"]) for offset in p["offsets"]])
    eps=p["epsilon"]
    deriv=np.array([(potential(x+np.eye(3)[a]*eps)-potential(x-np.eye(3)[a]*eps))/(2*eps) for a in range(3)])
    return np.array([deriv[1,2]-deriv[2,1],deriv[2,0]-deriv[0,2],deriv[0,1]-deriv[1,0]])


def velocity(x,t,p):
    return np.array([0,p["up_speed"],0])+p["curl_strength"]*curl(x,t,p)


def centers(p):
    nx,nz=p["grid_size"]
    return np.array([p["domain_min"]+np.array([(i+.5)/nx,(j+.5)/nz])*p["domain_size"]
                     for j in range(nz) for i in range(nx)])


def laplacian(a,p):
    v=np.pad(a,1,mode="edge")
    dx,dz=np.array(p["domain_size"])/p["grid_size"]
    return (v[1:-1,2:]-2*a+v[1:-1,:-2])/dx**2+(v[2:,1:-1]-2*a+v[:-2,1:-1])/dz**2


def interval(o,d,lo,hi):
    a,b=0.,float("inf")
    for x,v,l,h in zip(o,d,lo,hi):
        if abs(v)<1e-12:
            if x<l or x>h: return None
        else:
            t1,t2=sorted(((l-x)/v,(h-x)/v))
            a=max(a,t1); b=min(b,t2)
    return (a,b) if b>a else None


def density(point,p):
    # cloud_world_to_local is column-major homogeneous rigid transform.
    mat=np.array(p["cloud_world_to_local"]).reshape(4,4,order="F")
    q=(mat@np.r_[point,1])[:3]
    lo,hi=np.array(p["cloud_min"]),np.array(p["cloud_max"])
    if np.any(q<lo) or np.any(q>hi): return 0.
    nx,ny,nz=p["density_size"]
    a=np.array(p["density"]).reshape(nz,ny,nx)
    f=(q-lo)/(hi-lo)*[nx,ny,nz]-.5
    base=np.floor(f).astype(int); f-=base
    ans=0.
    for k,j,i in product(range(2),repeat=3):
        idx=np.clip(base+[i,j,k],0,[nx-1,ny-1,nz-1])
        w=np.prod([f[axis] if bit else 1-f[axis] for axis,bit in enumerate((i,j,k))])
        ans+=w*a[idx[2],idx[1],idx[0]]
    return ans


def cloud(point,p):
    mat=np.array(p["cloud_world_to_local"]).reshape(4,4,order="F")
    o=(mat@np.r_[point,1])[:3]; d=(mat@np.r_[p["light_dir"],0])[:3]
    ab=interval(o,d,p["cloud_min"],p["cloud_max"])
    if ab is None: return np.array([0,0,0,0,1.])
    a,b=ab; ds=(b-a)/p["cloud_steps"]
    tau=p["cloud_sigma"]*ds*sum(density(np.array(point)+(a+(i+.5)*ds)*np.array(p["light_dir"]),p) for i in range(p["cloud_steps"]))
    return np.array([1,a,b,tau,math.exp(-tau)])


def optics(I,N,p,x):
    I,N,x=map(np.asarray,(I,N,x))
    ci=-I@N; ei,et=p["eta_i"],p["eta_t"]
    ratio=ei/et; k=1-ratio*ratio*(1-ci*ci)
    if ei == et: F,T,has=0.,I,True
    elif k < 0: F,T,has=1.,np.zeros(3),False
    else:
        ct=math.sqrt(k)
        F=.5*(((ei*ci-et*ct)/(ei*ci+et*ct))**2+((et*ci-ei*ct)/(et*ci+ei*ct))**2)
        T=ratio*I+(ratio*ci-ct)*N; has=True
    R=I+2*ci*N; A=np.exp(-np.array(p["sigma_a"])*p["ell"])
    clip=np.array(p["view_projection"]).reshape(4,4,order="F")@np.r_[x+p["ell"]*T,1]
    uv=(clip[:2]/clip[3]*np.array([1,-1])+1)*.5 if abs(clip[3])>1e-15 else np.zeros(2)
    valid=has and clip[3]>0 and np.all(uv>=0) and np.all(uv<=1) and 0<=clip[2]/clip[3]<=1
    bg=sample2(np.array(p["color_texture"]).reshape(*p["texture_size"][::-1],3),uv) if valid else p["fallback_color"]
    col=F*np.array(p["reflection_color"])+(1-F)*A*bg
    return np.r_[F,T,R,A,float(has),uv,float(valid),col]


def evaluate(name,p):
    """Return [rows,channels]; no use of GPU implementation or captured images."""
    size=p["grid_size"]; shape=(size[1],size[0])
    if name=="burn_query": return burn(p["points"],p)
    if name=="curl_query":
        return np.array([np.r_[curl(np.array(x),p["time"],p),velocity(np.array(x),p["time"],p)] for x in p["points"]])
    if name=="particle_step":
        out=[]
        for row in p["particles"]:
            x=np.array(row[:3]); age=row[3]+p["dt"]
            x=x+p["dt"]*velocity(x+.5*p["dt"]*velocity(x,p["time"],p),p["time"]+.5*p["dt"],p)
            out.append(np.r_[x,age,float(age<p["lifetime"]),max(0,1-age/p["lifetime"])])
        return np.array(out)
    if name=="stamp_query":
        d=np.array(p["depth"]).reshape(shape).copy()
        seen=set()
        mask=np.array(p["mask"]).reshape(*p["mask_size"][::-1])
        for event in p["contacts"]:
            eid,cx,cz,angle,sx,sz,inc=event
            if eid in seen: continue
            seen.add(eid)
            cs,sn=math.cos(angle),math.sin(angle)
            rot=np.array([[cs,sn],[-sn,cs]])
            for index,s in enumerate(centers(p)):
                uv=rot@(s-[cx,cz])/[sx,sz]+.5
                d.flat[index]=min(p["d_max"],d.flat[index]+inc*sample2(mask,uv,"zero"))
        return d.reshape(-1,1)
    if name=="pom_query":
        d=np.array(p["depth"]).reshape(shape)
        lo=np.array(p["domain_min"]); extent=np.array(p["domain_size"])
        out=[]
        for ray in p["pom_rays"]:
            x=np.array(ray[:2]); v=np.array(ray[2:])
            def at(s): return x-s*v[[0,2]]/v[1]
            def f(s): return s-sample2(d,(at(s)-lo)/extent,"zero")
            valid=True; hit=None; previous=0.
            if f(0)>=0: hit=0.
            else:
                for s in np.linspace(0,p["d_max"],4097)[1:]:
                    uv=(at(s)-lo)/extent
                    if np.any(uv<0) or np.any(uv>1): valid=False; break
                    if f(s)>=0:
                        a,b=previous,s
                        for _ in range(40):
                            mid=(a+b)/2
                            if f(mid)>=0: b=mid
                            else: a=mid
                        hit=(a+b)/2; break
                    previous=s
            if not valid or hit is None: out.append([0,0,0,0,0,0])
            else: out.append(np.r_[1,hit,(at(hit)-lo)/extent,at(hit)])
        return np.array(out)
    if name=="wet_step":
        w=np.array(p["wetness"]).reshape(shape); d=np.array(p["depth"]).reshape(shape)
        lam=p["lambda0"]/(1+p["beta"]*d/p["d_max"])
        value=np.clip(w+p["dt"]*(p["diffusion"]*laplacian(w,p)-lam*w+np.array(p["source"]).reshape(shape)),0,1)
        return np.c_[value.ravel(),lam.ravel()]
    if name=="cloud_query": return np.array([cloud(x,p) for x in p["points"]])
    if name=="fog_query":
        result=[]
        for ray in p["view_rays"]:
            o,d,opaque=np.array(ray[:3]),np.array(ray[3:6]),ray[6]
            g=p["g"]; phase=(1-g*g)/(4*math.pi*(1+g*g-2*g*np.dot(p["light_dir"],d))**1.5)
            ab=interval(o,d,p["fog_min"],p["fog_max"])
            n=p["view_steps"]; tc=np.ones(n); tl=np.ones(n); col=np.zeros(3); T=1.
            if ab:
                a,b=ab; b=min(b,opaque)
                if b>a:
                    ds=(b-a)/n; k=p["fog_density"]*(p["fog_scatter"]+p["fog_absorb"])
                    attenuation=math.exp(-k*ds); integral=-math.expm1(-k*ds)/k if k>0 else ds
                    for i in range(n):
                        x=o+(a+(i+.5)*ds)*d
                        tc[i]=cloud(x,p)[4]
                        light_ab=interval(x,p["light_dir"],p["fog_min"],p["fog_max"])
                        tl[i]=math.exp(-k*light_ab[1]) if light_ab else 1.
                        j=p["fog_density"]*p["fog_scatter"]*np.array(p["light_rgb"])*tc[i]*tl[i]*phase
                        col+=T*j*integral; T*=attenuation
            result.append(np.r_[phase,col,T,tc,tl])
        return np.array(result)
    if name=="flow_query":
        tex=np.array(p["color_texture"]).reshape(*p["texture_size"][::-1],3)
        normal=np.array(p["normal_texture"]).reshape(*p["texture_size"][::-1],3)
        flow=np.array(p["flow"]).reshape(*shape,2)
        out=[]
        for uv in p["uvs"]:
            velocity_uv=sample2(flow,uv)/p["domain_size"]
            p0=(p["time"]/p["period"]+p["phase"])%1; p1=(p0+.5)%1
            w0=1-abs(2*p0-1); w1=1-w0
            q0=p["tiling"]*(np.array(uv)-p["period"]*p0*velocity_uv)
            q1=p["tiling"]*(np.array(uv)-p["period"]*p1*velocity_uv)
            col=w0*sample2(tex,q0,"repeat")+w1*sample2(tex,q1,"repeat")
            nor=w0*sample2(normal,q0,"repeat")+w1*sample2(normal,q1,"repeat")
            if p["normal_encoded"]: nor=2*nor-1
            nor/=np.linalg.norm(nor)
            out.append(np.r_[q0,q1,w0,w1,col,nor])
        return np.array(out)
    if name=="foam_step":
        old=np.array(p["foam"]).reshape(shape); out=[]
        for s,v in zip(centers(p),p["flow"]):
            source=sum(rate*max(0,1-np.dot(s-[x,z],s-[x,z])/r**2)**2 for x,z,r,rate in p["sources"])
            q=s-p["dt"]*np.array(v)
            value=sample2(old,(q-p["domain_min"])/p["domain_size"],"zero")*math.exp(-p["decay"]*p["dt"])+p["dt"]*source
            out.append([np.clip(value,0,1),source])
        return np.array(out)
    if name=="optics_query":
        return np.array([optics(row[:3],row[3:6],p,row[6:9]) for row in p["optical_rays"]])
    if name=="wave_step":
        h=np.array(p["height"]).reshape(shape); prev=np.array(p["height_prev"]).reshape(shape)
        value=(2-p["gamma"]*p["dt"])*h-(1-p["gamma"]*p["dt"])*prev+p["wave_speed"]**2*p["dt"]**2*laplacian(h,p)+p["dt"]**2*np.array(p["force"]).reshape(shape)
        return value.reshape(-1,1)
    if name=="wave_normal_query":
        h=np.array(p["height"]).reshape(shape); a=np.pad(h,1,mode="edge")
        dx,dz=np.array(p["domain_size"])/p["grid_size"]
        normal=np.stack((-(a[1:-1,2:]-a[1:-1,:-2])/(2*dx),np.ones(shape),-(a[2:,1:-1]-a[:-2,1:-1])/(2*dz)),axis=-1)
        normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
        return normal.reshape(-1,3)
    raise ValueError(name)
