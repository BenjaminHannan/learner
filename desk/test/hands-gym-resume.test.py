"""Deterministic trainer checkpoint and isolated-evaluation regressions."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src/hands-gym'))


class TrainingResumeTests(unittest.IsolatedAsyncioTestCase):
    async def test_browser_replay_validates_observations(self):
        import numpy as np
        from hands_gym.train import observation_hash, restore_environments

        class Environment:
            async def reset(self,kind,seed):
                self.episode={};self.actions=[]
                return observation

            async def step(self,action):
                self.actions.append(action)
                return observation,0,False,{}

        observation={'overview':np.zeros((4,4,3),dtype=np.uint8),
                     'detail':np.ones((4,4,3),dtype=np.uint8)}
        environment=Environment()
        task={'kind':'close_popup','seed':99,'actions':[{'kind':'key','keyCode':97}],
              'observation_sha256':observation_hash(observation)}
        result=await restore_environments([environment],[task],8)
        self.assertEqual(environment.actions,task['actions'])
        self.assertEqual(environment.episode['max_steps'],8)
        self.assertEqual(observation_hash(result[0]),task['observation_sha256'])
        task['observation_sha256']='not-the-saved-screen'
        with self.assertRaisesRegex(RuntimeError,'screenshot mismatch'):
            await restore_environments([environment],[task],8)

    async def test_interrupted_training_resumes_without_extra_steps(self):
        import argparse
        import numpy as np
        import torch
        from hands_gym import train
        torch.set_num_threads(1)

        class Environment:
            def __init__(self,browser,max_steps):self.max_steps=max_steps
            async def start(self):pass
            async def close(self):pass
            async def reset(self,kind,seed):
                self.episode={'kind':kind,'seed':seed,'instruction':'Close the popup.'}
                self.steps=0
                self.observation={'overview':np.zeros((32,32,3),dtype=np.uint8),
                                  'detail':np.zeros((32,32,3),dtype=np.uint8)}
                return self.observation
            async def step(self,action):
                self.steps+=1
                done=self.steps==self.max_steps
                return self.observation,float(done),done,{'success':done}

        async def evaluate(net,envs,device,episodes,seed,max_steps):
            torch.manual_seed(seed)
            return {'per_task':{'close_popup':{'rate':0.5}},'overall':0.5,'steps':0}

        with tempfile.TemporaryDirectory(prefix='hands-gym-resume-') as directory:
            args=argparse.Namespace(device='cpu',native_checkpoint=None,resume_checkpoint=None,
                resume_training=None,output=directory,seeds=[11],envs=2,remote_endpoints=[],
                max_steps=3,eval_episodes=1,updates=2,rollout=2,epochs=1,minibatch=2,
                lr=0.0003,entropy=0.005,self_imitation_weight=0.1,
                success_buffer_episodes=2,eval_every=1)
            original_save=train.save_training

            def interrupt_after_first(state,path):
                original_save(state,path)
                if state['update']==1:raise InterruptedError('simulated reboot')

            with mock.patch.object(train,'BrowserEnv',Environment),mock.patch.object(train,'evaluate',evaluate):
                with mock.patch.object(train,'save_training',side_effect=interrupt_after_first):
                    with self.assertRaises(InterruptedError):await train.run_seed(args,11,None)
                checkpoint=Path(directory)/'seed-11/training-state.pt'
                args.resume_training=str(checkpoint)
                resumed=await train.run_seed(args,11,None)
                final_state=torch.load(Path(directory)/'seed-11/final.pt',weights_only=True)
                self.assertEqual(resumed['train_steps'],8)
                self.assertEqual([point['update'] for point in resumed['held_out_curve']],[0,1,2])
                args.output=str(Path(directory)/'uninterrupted');args.resume_training=None
                await train.run_seed(args,11,None)
                uninterrupted=torch.load(Path(args.output)/'seed-11/final.pt',weights_only=True)
                for key,value in final_state.items():torch.testing.assert_close(value,uninterrupted[key],rtol=0,atol=0)
                args.output=str(Path(directory)/'without-interim-evaluation');args.eval_every=0
                await train.run_seed(args,11,None)
                without_eval=torch.load(Path(args.output)/'seed-11/final.pt',weights_only=True)
                for key,value in final_state.items():torch.testing.assert_close(value,without_eval[key],rtol=0,atol=0)


if __name__=='__main__':unittest.main(verbosity=2)
