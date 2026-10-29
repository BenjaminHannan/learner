import sys,unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import torch
from privileged_kl import answer_kl,Limits
class Review(unittest.TestCase):
 def test_asymmetric_kl_and_alignment(self):
  t=torch.zeros(2,7,3,dtype=torch.float64,requires_grad=True);s=torch.zeros(2,6,3,dtype=torch.float64,requires_grad=True)
  with torch.no_grad():
   t[0,2]=torch.tensor([2.,0.,-1.]); t[1,3]=torch.tensor([-1.,2.,0.]);t[1,4]=torch.tensor([0.,-1.,2.])
   s[0,2]=torch.tensor([0.,1.,-1.]); s[1,1]=torch.tensor([1.,0.,-1.]);s[1,2]=torch.tensor([-1.,0.,1.])
  kw=dict(teacher_logits=t,student_logits=s,teacher_ids=torch.tensor([[0,0,0,1,0,0,0],[0,1,0,0,2,1,0]]),student_ids=torch.tensor([[0,0,0,1,0,0],[0,0,2,1,0,0]]),teacher_mask=torch.tensor([[False,True,True,True,False,False,False],[False,True,True,True,True,True,False]]),student_mask=torch.tensor([[False,True,True,True,False,False],[True,True,True,True,False,False]]),teacher_prefix_lengths=torch.tensor([2,3]),student_prefix_lengths=torch.tensor([2,2]),answer_lengths=torch.tensor([1,2]),teacher_vocab_id='v',student_vocab_id='v')
  loss=answer_kl(**kw);tp=torch.stack([t[0,2],t[1,3],t[1,4]]).detach().log_softmax(-1);sp=torch.stack([s[0,2],s[1,1],s[1,2]]).log_softmax(-1)
  expected=(tp.exp()*(tp-sp)).sum()/3; reverse=(sp.exp()*(sp-tp)).sum()/3
  torch.testing.assert_close(loss,expected);self.assertGreater(abs(float((loss-reverse).detach())),.001)
  loss.backward();self.assertIsNone(t.grad);self.assertEqual(float(s.grad[0,1].abs().sum()),0)
 def test_bad_lengths_and_padded_nan(self):
  x=torch.zeros(1,3,3); ids=torch.tensor([[0,1,2]]);mask=torch.tensor([[True,True,True]])
  kw=dict(teacher_logits=x.clone(),student_logits=x.clone(),teacher_ids=ids,student_ids=ids,teacher_mask=mask,student_mask=mask,teacher_prefix_lengths=torch.tensor([1]),student_prefix_lengths=torch.tensor([1]),answer_lengths=torch.tensor([1]),teacher_vocab_id='v',student_vocab_id='v')
  for changes in ({'teacher_prefix_lengths':torch.tensor([False])},{'teacher_mask':torch.tensor([[True,False,True]])},{'limits':Limits(max_sequence_tokens=2)},{'limits':Limits(max_answer_tokens=0)}):
   with self.subTest(changes=changes),self.assertRaises(ValueError):answer_kl(**(kw|changes))
  kw['teacher_mask']=torch.tensor([[True,True,False]]);kw['teacher_logits'][0,2,0]=float('nan')
  with self.assertRaises(ValueError):answer_kl(**kw)
if __name__=='__main__':torch.set_num_threads(2);unittest.main(verbosity=2)
