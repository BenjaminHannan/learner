"""Unit checks plus optional real Chromium oracle checks, on either OS."""
import asyncio
import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest import mock
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src/hands-gym'))
from hands_gym import tasks
from hands_gym.actions import cell_center, decode_action, key_name
from hands_gym.protocol import parse_request, ProtocolError

class TaskTests(unittest.TestCase):
    def test_all_builders_reproducible_and_random(self):
        self.assertGreaterEqual(len(tasks.TASK_TYPES),7)
        for kind in tasks.TASK_TYPES:
            a=tasks.build(kind,42)
            self.assertEqual(a,tasks.build(kind,42))
            self.assertNotEqual(a['html'],tasks.build(kind,43)['html'])
            self.assertTrue(a['instruction'].strip())
            self.assertIn('window.__gym.state',a['html'])
        with self.assertRaises(ValueError):tasks.build('bedwars',0)
        with self.assertRaises(ValueError):tasks.build('click_button',True)

    def test_reward_success_and_negative(self):
        cases=[('click_button',{'target':'a'},{'clicks':['a']},{'clicks':[]}),
            ('type_text',{'target':'a'},{'value':'a','submitted':True},{'value':''}),
            ('dropdown',{'target':'a'},{'value':'a'},{'value':None}),
            ('close_popup',{}, {'closed':True},{'closed':False}),
            ('drag_slider',{'target':50},{'value':50,'dragged':True},{'value':0,'dragged':False}),
            ('click_link',{'target':'a'},{'clicks':['a']},{'clicks':[]}),
            ('menu_select',{'target':'a'},{'choice':'a'},{'choice':None}),
            ('checkbox',{'target':'a'},{'checks':{'a':True}},{'checks':{}}),
            ('form_fill',{'name':'a','city':'b'},{'name':'a','city':'b','submitted':True},{'name':'','city':''})]
        for k,s,good,bad in cases:
            ok,r,done=tasks.check(k,s,good,bad,0)
            self.assertTrue(ok,k);self.assertGreaterEqual(r,1);self.assertTrue(done)
            self.assertFalse(tasks.check(k,s,bad,bad,0)[0],k)
            self.assertTrue(tasks.check(k,s,bad,bad,7,8)[2])
            self.assertFalse(tasks.check(k,s,bad,bad,6,8)[2])

    def test_action_and_protocol(self):
        self.assertEqual(key_name(128),'Enter')
        self.assertEqual(key_name(ord('a')),'a')
        for i in (0,335):
            x,y=cell_center(i);self.assertTrue(0<x<1 and 0<y<1)
        with self.assertRaises(ValueError):cell_center(336)
        self.assertEqual(decode_action(1,0,1)['kind'],'drag')
        with self.assertRaises(ProtocolError):parse_request({'cmd':'reset','kind':'a','seed':True})

class GpuGateTests(unittest.TestCase):
    def test_gpu_ownership_and_foreign_client_gate(self):
        from hands_gym import gpu_gate
        idle={'compute_apps':r'1, C:\Windows\System32\dwm.exe','gpu':'0, 1400, 8'}
        with tempfile.TemporaryDirectory(prefix='hands-gym-',dir=Path(__file__).resolve().parent) as d:
            with mock.patch.object(gpu_gate,'inspect',return_value=idle):
                with gpu_gate.Lease(d):
                    owner=Path(d,'GPU-OWNER.json').read_bytes()
                    with self.assertRaises(FileExistsError):
                        with gpu_gate.Lease(d):pass
                    self.assertEqual(owner,Path(d,'GPU-OWNER.json').read_bytes())
                self.assertFalse(Path(d,'GPU-OWNER.json').exists())
            busy={**idle,'compute_apps':r'123, C:\Python\python.exe'}
            self.assertEqual(gpu_gate.foreign_clients(busy,123),[])
            with mock.patch.object(gpu_gate,'inspect',return_value=busy):
                with self.assertRaises(RuntimeError):
                    with gpu_gate.Lease(d):pass
            with mock.patch.object(gpu_gate,'inspect',return_value={**idle,'gpu':'100, 15000, 78'}):
                with self.assertRaises(RuntimeError):
                    with gpu_gate.Lease(d):pass

@unittest.skipUnless(importlib.util.find_spec('numpy'),'numpy not installed')
class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_full_screenshot_roundtrip(self):
        from hands_gym import protocol
        import numpy as np
        rng=np.random.default_rng(3)
        obs={'overview':rng.integers(0,256,(180,320,3),dtype=np.uint8),
             'detail':rng.integers(0,256,(192,192,3),dtype=np.uint8)}
        data=protocol.encode_message({'obs':protocol.encode_obs(obs)})
        self.assertGreater(len(data),65536)
        reader=asyncio.StreamReader(limit=protocol.MAX_MESSAGE_BYTES)
        reader.feed_data(data);reader.feed_eof()
        out=protocol.decode_obs((await protocol.read_message(reader))['obs'])
        for k in obs:np.testing.assert_array_equal(obs[k],out[k])

@unittest.skipUnless(importlib.util.find_spec('torch'),'torch not installed')
class ModelTests(unittest.TestCase):
    def test_success_buffer_keeps_complete_wins_and_discards_failures(self):
        import torch
        from hands_gym.train import SuccessBuffer
        buffer=SuccessBuffer(2,capacity=1,seed=19)
        inputs=(torch.ones(2,3,4,4),torch.zeros(2,3,4,4),
                torch.ones(2,64),torch.zeros(2,12))
        actions=torch.tensor([[0,1,0,0],[2,0,0,3]])
        pending=[(None,0,False,{'success':False})]*2
        buffer.record(inputs,actions,pending)
        self.assertIsNone(buffer.sample(32,'cpu'))
        buffer.record(inputs,actions,[(None,1,True,{'success':True}),
                                      (None,0,True,{'success':False})])
        self.assertEqual(len(buffer.episodes),1)
        self.assertEqual(len(buffer.episodes[0]),2)
        self.assertEqual(buffer.pending,[[],[]])
        self.assertEqual(buffer.episodes[0][0][0][0].dtype,torch.uint8)
        sampled_inputs,sampled_actions=buffer.sample(32,'cpu')
        torch.testing.assert_close(sampled_inputs[0],inputs[0])
        torch.testing.assert_close(sampled_actions,actions[0].repeat(2,1))
        buffer.record(inputs,actions,[(None,0,True,{'success':False}),
                                      (None,1,True,{'success':True})])
        self.assertEqual(len(buffer.episodes),1)
        torch.testing.assert_close(buffer.episodes[0][0][1],actions[1])

    def test_cloning_loss_improves_success_action_and_restores_buffer_rng(self):
        import torch
        from hands_gym.model import GymPolicy
        from hands_gym.train import SuccessBuffer, cloning_loss
        torch.set_num_threads(1);torch.manual_seed(17)
        net=GymPolicy()
        inputs=(torch.rand(1,3,32,32),torch.rand(1,3,32,32),
                torch.ones(1,64),torch.zeros(1,12))
        actions=torch.tensor([[0,25,0,0]])
        buffer=SuccessBuffer(1,seed=9)
        self.assertIsNone(cloning_loss(net,buffer,32,'cpu'))
        buffer.record(inputs,actions,[(None,1,True,{'success':True})])
        state=buffer.state_dict()
        restored=SuccessBuffer(1,seed=100);restored.load_state_dict(state)
        first=buffer.sample(32,'cpu');second=restored.sample(32,'cpu')
        for actual,expected in zip(first[0],second[0]):torch.testing.assert_close(actual,expected)
        torch.testing.assert_close(first[1],second[1])
        global_rng=torch.get_rng_state().clone()
        loss=cloning_loss(net,buffer,32,'cpu')
        torch.testing.assert_close(torch.get_rng_state(),global_rng)
        before=float(loss.detach())
        optimizer=torch.optim.SGD(net.parameters(),lr=0.001)
        optimizer.zero_grad();loss.backward();optimizer.step()
        self.assertLess(float(cloning_loss(net,buffer,32,'cpu').detach()),before)
        self.assertGreater(float(net.start_grid.weight.grad.abs().sum()),0)

    def test_policy_action_logprob_and_ppo_gradients(self):
        import torch
        from hands_gym.model import GymPolicy, native_actions, intent_vector
        torch.set_num_threads(1);torch.manual_seed(5)
        net=GymPolicy()
        inp=(torch.rand(4,3,180,320),torch.rand(4,3,192,192),
             torch.stack([intent_vector('Close the popup.')]*4),torch.zeros(4,12))
        actions,lp,entropy,value=net.act(inp)
        _,same,_,_=net.act(inp,actions=actions)
        torch.testing.assert_close(lp,same)
        self.assertEqual(value.shape,(4,))
        self.assertTrue(torch.isfinite(entropy).all())
        for action in native_actions(actions):self.assertIn(action['kind'],('click','drag','key','scroll'))
        # Forced native kinds prove that all relevant stochastic heads train.
        actions[:,0]=torch.tensor([0,1,2,3])
        _,lp,entropy,value=net.act(inp,actions=actions)
        (-lp.mean()+value.square().mean()-0.01*entropy.mean()).backward()
        self.assertGreater(float(net.encoder[0].weight.grad.abs().sum()),0)
        for head in (net.kind,net.start_grid,net.end_grid,net.key,net.value):
            self.assertTrue(torch.isfinite(head.weight.grad).all())
            self.assertGreater(float(head.weight.grad.abs().sum()),0)

@unittest.skipUnless(os.environ.get('HANDS_GYM_BROWSER_TESTS')=='1','set HANDS_GYM_BROWSER_TESTS=1 for Chromium')
class BrowserTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_input_all_nine_tasks(self):
        from playwright.async_api import async_playwright
        from hands_gym.browser_env import BrowserEnv
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(headless=True,args=['--disable-gpu'])
            env=BrowserEnv(browser);await env.start()
            try:
                async def click(selector):
                    b=await env.page.locator(selector).bounding_box()
                    return await env.step({'kind':'click','x':(b['x']+b['width']/2)/640,'y':(b['y']+b['height']/2)/360})
                async def key(code):return await env.step({'kind':'key','keyCode':code})
                for seed in (7,42,99):
                    for kind in tasks.TASK_TYPES:
                        obs=await env.reset(kind,seed)
                        self.assertEqual(obs['overview'].shape,(180,320,3))
                        self.assertEqual(obs['detail'].shape,(192,192,3))
                        spec=env.episode['spec']
                        # These test-only oracle selectors never enter the trainer.
                        if kind in ('click_button','click_link'):
                            result=await click('[data-label="'+spec['target']+'"]')
                        elif kind=='type_text':
                            await click('#text')
                            for ch in spec['target']:await key(ord(ch))
                            result=await key(128)
                        elif kind=='dropdown':
                            await click('#select');result=await click('[data-value="'+spec['target']+'"]')
                        elif kind=='close_popup':result=await click('#close')
                        elif kind=='menu_select':
                            await click('#menubtn');result=await click('[data-value="'+spec['target']+'"]')
                        elif kind=='checkbox':result=await click('input[data-label="'+spec['target']+'"]')
                        elif kind=='form_fill':
                            for field in ('name','city'):
                                await click('#'+field)
                                for ch in spec[field]:await key(ord(ch))
                            result=await click('#submit')
                        else:
                            b=await env.page.locator('#slider').bounding_box()
                            # Portable pointer slider thumb is 16 px; drag from initial value to target.
                            result=await env.step({'kind':'drag','x':(b['x']+8+(b['width']-16)*spec['start']/100)/640,
                                'y':(b['y']+b['height']/2)/360,
                                'endX':(b['x']+8+(b['width']-16)*spec['target']/100)/640,
                                'endY':(b['y']+b['height']/2)/360})
                        self.assertTrue(result[3]['success'],(kind,seed,env.state))
                        self.assertGreaterEqual(result[1],1,(kind,seed))
                        with self.assertRaises(RuntimeError):await env.step({'kind':'click'})
                print('REAL CHROMIUM: 27/27 oracle tasks passed; screenshots + native input',flush=True)
            finally:await env.close();await browser.close()

    async def test_remote_browser_worker_native_action_and_timeout(self):
        from playwright.async_api import async_playwright
        from hands_gym.browser_env import BrowserEnv
        from hands_gym.env_server import handle_client
        from hands_gym.remote import RemoteEnv
        from hands_gym.protocol import MAX_MESSAGE_BYTES
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(headless=True,args=['--disable-gpu'])
            made=[]
            async def factory():
                e=BrowserEnv(browser);await e.start();made.append(e);return e
            async def connection(r,w):await handle_client(r,w,factory)
            server=await asyncio.start_server(connection,'127.0.0.1',0,limit=MAX_MESSAGE_BYTES)
            client=RemoteEnv('127.0.0.1',server.sockets[0].getsockname()[1],max_steps=2)
            await client.connect()
            try:
                obs=await client.reset('close_popup',94)
                self.assertEqual(obs['overview'].shape,(180,320,3))
                b=await made[-1].page.locator('#close').bounding_box()
                _,reward,done,info=await client.step({'kind':'click',
                    'x':(b['x']+20)/640,'y':(b['y']+20)/360})
                self.assertTrue(info['success']);self.assertTrue(done);self.assertEqual(reward,1)
                await client.reset('close_popup',94)
                self.assertFalse((await client.step({'kind':'click','x':0,'y':0}))[2])
                self.assertTrue((await client.step({'kind':'click','x':0,'y':0}))[2])
                print('LOOPBACK REMOTE: screenshot transport + real input + 2-step timeout passed',flush=True)
            finally:
                await client.close();server.close();await server.wait_closed()
                await asyncio.sleep(0.05);await browser.close()

if __name__=='__main__':unittest.main(verbosity=2)
