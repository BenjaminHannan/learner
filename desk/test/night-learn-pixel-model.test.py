import importlib.util
from pathlib import Path
import unittest
import torch

path = Path(__file__).resolve().parents[1] / 'src' / 'night-learn' / 'pixel_model.py'
spec = importlib.util.spec_from_file_location('night_pixel_model', path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class PixelModelTests(unittest.TestCase):
    def test_intent_and_shapes(self):
        self.assertTrue(torch.equal(mod.intent_vector('Open the page'), mod.intent_vector('Open the page')))
        self.assertFalse(torch.equal(mod.intent_vector('Open the page'), mod.intent_vector('Close the window')))
        net = mod.NativeActionPolicy().eval()
        with torch.no_grad():
            output, state = net(torch.zeros(1,3,180,320), torch.zeros(1,3,192,192), mod.intent_vector('open').unsqueeze(0), torch.zeros(1,12))
        self.assertEqual(tuple(state.shape), (1,512))
        self.assertEqual(tuple(output['position'].shape), (1,4))
        self.assertEqual(tuple(output['key'].shape), (1,256))

    def test_only_relevant_action_heads_affect_loss_and_weight(self):
        pred = {'kind':torch.zeros(2,4), 'position':torch.zeros(2,4), 'key':torch.zeros(2,256), 'scroll':torch.zeros(2,2)}
        labels = {'kind':torch.tensor([0,0]), 'position':torch.tensor([[0.,0.,0.,0.],[1.,1.,0.,0.]]), 'key':torch.zeros(2,dtype=torch.long), 'scroll':torch.zeros(2,2)}
        a = mod.action_loss(pred, labels, torch.tensor([1.,1.]))
        b = mod.action_loss(pred, labels, torch.tensor([1.,3.]))
        self.assertGreater(b.item(), a.item())
        pred['key'].fill_(100.)
        self.assertEqual(b.item(), mod.action_loss(pred, labels, torch.tensor([1.,3.])).item())

if __name__ == '__main__': unittest.main()
