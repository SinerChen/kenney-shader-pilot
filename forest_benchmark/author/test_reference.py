import unittest
import numpy as np
from model import defaults,merge
from reference_cpu import evaluate,noise
from simulation_cpu import Simulator


class AnalyticTests(unittest.TestCase):
    def setUp(self):self.p=defaults()
    def test_noise_lattice(self):
        for x in [[0,0,0],[-2,7,3],[256,-256,11]]:
            self.assertEqual(noise(np.array(x),self.p["P"]),0.)
    def test_front_anchor(self):
        p=merge(self.p,{"noise_amplitude":0.,"R0":1.,"speed":0.,"origin_ref":[0,0,0],"points":[[1,0,0]]})
        np.testing.assert_allclose(evaluate("burn_query",p)[0,1:],[0,.5,1])
    def test_burn_monotone(self):
        values=[evaluate("burn_query",merge(self.p,{"time":t}))[:,2] for t in [0,.5,1,2,5]]
        self.assertTrue(np.all(np.diff(values,axis=0)>=0))
    def test_particle_anchor(self):
        p=merge(self.p,{"curl_strength":0.,"up_speed":1.,"dt":.1,"lifetime":1.,"particles":[[0,0,0,0]]})
        np.testing.assert_allclose(evaluate("particle_step",p)[0],[0,.1,0,.1,1,.9])
    def test_stamp_saturation(self):
        p=merge(self.p,{"mask":[1.]*48,"contacts":[[1,0,0,0,4,3,.02],[2,0,0,0,4,3,.02]],"d_max":.03})
        np.testing.assert_allclose(evaluate("stamp_query",p),.03)
    def test_pom_anchor(self):
        p=merge(self.p,{"depth":[.02]*48,"pom_rays":[[0,0,.6,.8,0]]})
        r=evaluate("pom_query",p)[0]
        self.assertAlmostEqual(r[1],.02);self.assertAlmostEqual(r[4],-.015)
    def test_wet_anchor(self):
        p=merge(self.p,{"diffusion":0.,"source":[0.]*48,"wetness":[.8]*48,"depth":[.08]*48,"lambda0":1.,"beta":1.,"dt":.1})
        np.testing.assert_allclose(evaluate("wet_step",p),np.tile([.76,.5],(48,1)))
    def test_diffusion_conserves_without_clamp(self):
        p=merge(self.p,{"lambda0":0.,"source":[0.]*48})
        self.assertAlmostEqual(evaluate("wet_step",p)[:,0].sum(),sum(p["wetness"]),places=10)
    def test_cloud_uniform(self):
        p=merge(self.p,{"cloud_min":[-5,0,-5],"cloud_max":[5,10,5],"density":[.5]*60,"cloud_sigma":.4,"points":[[0,-1,0]],"light_dir":[0,1,0]})
        np.testing.assert_allclose(evaluate("cloud_query",p),[[1,1,11,2,np.exp(-2)]])
    def test_hg_isotropic(self):
        p=merge(self.p,{"g":0.})
        np.testing.assert_allclose(evaluate("fog_query",p)[:,0],1/(4*np.pi))
    def test_fog_vacuum(self):
        p=merge(self.p,{"fog_density":0.})
        r=evaluate("fog_query",p)
        np.testing.assert_allclose(r[:,1:4],0);np.testing.assert_allclose(r[:,4],1)
    def test_flow_anchor(self):
        p=merge(self.p,{"flow":[[.4,0.]]*48,"uvs":[[.5,.5]],"period":2.,"time":.5,"phase":0.,"tiling":1.})
        np.testing.assert_allclose(evaluate("flow_query",p)[0,:6],[.45,.5,.35,.5,.5,.5])
    def test_foam_anchor(self):
        p=merge(self.p,{"flow":[[0,0]]*48,"sources":[],"foam":[.5]*48,"decay":2.,"dt":.1})
        np.testing.assert_allclose(evaluate("foam_step",p)[:,0],.5*np.exp(-.2))
    def test_optics_anchor(self):
        p=merge(self.p,{"eta_i":1.,"eta_t":1.5,"sigma_a":[0,0,0],"optical_rays":[[0,-1,0,0,1,0,0,0,.5]]})
        r=evaluate("optics_query",p)[0]
        self.assertAlmostEqual(r[0],.04);np.testing.assert_allclose(r[1:4],[0,-1,0]);np.testing.assert_allclose(r[7:10],1)
    def test_snell_angle(self):
        r=evaluate("optics_query",self.p)[0]
        self.assertAlmostEqual(np.linalg.norm(r[1:4]),1)
        self.assertAlmostEqual(r[1]*self.p["eta_t"],.6*self.p["eta_i"])
    def test_wave_anchor(self):
        p=merge(self.p,{"height":[1.]*48,"height_prev":[1.]*48,"force":[0.]*48})
        np.testing.assert_allclose(evaluate("wave_step",p),1.)
        np.testing.assert_allclose(evaluate("wave_normal_query",p),np.tile([0,1,0],(48,1)))
    def test_wave_linear(self):
        a=evaluate("wave_step",self.p)
        p=merge(self.p,{"height":(np.array(self.p["height"])*2).tolist()})
        np.testing.assert_allclose(evaluate("wave_step",p),a*2)
    def test_event_dedup_and_reset(self):
        p=merge(self.p,{"task_id":"B_L1"})
        s=Simulator();s.reset(p)
        event={"type":"contact","event_id":"a","contact":[1,0,0,0,1.,1.5,.03]}
        s.advance(.02,[event]);first=s.state["depth_field"].copy()
        s.advance(.02,[event]);np.testing.assert_array_equal(first,s.state["depth_field"])
        s.reset(p);s.advance(.02,[]);np.testing.assert_array_equal(s.state["depth_field"],np.zeros((48,1)))
    def test_input_stability(self):
        for chain in "ABCDE":
            p=self.p;dx,dz=np.array(p["domain_size"])/p["grid_size"]
            self.assertLessEqual(p["dt"]*(2*p["diffusion"]/dx**2+2*p["diffusion"]/dz**2+p["lambda0"]),1)
            self.assertLessEqual(p["wave_speed"]**2*p["dt"]**2*(1/dx**2+1/dz**2),.8)


if __name__=="__main__":unittest.main(verbosity=2)
