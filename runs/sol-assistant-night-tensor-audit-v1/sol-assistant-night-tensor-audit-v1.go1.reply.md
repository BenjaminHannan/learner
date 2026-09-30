{
  "spec_sha256": "b752876c14912f36117c45bee772c7036ef8545cc091e1a81524eb54655aa442",
  "checks": [
    {
      "name": "all input/source byte pins",
      "pass": true,
      "count": 43
    },
    {
      "name": "manifest bound by final decision",
      "pass": true
    },
    {
      "name": "manifest parent",
      "pass": true
    },
    {
      "name": "manifest prefix",
      "pass": true
    },
    {
      "name": "manifest reader",
      "pass": true
    },
    {
      "name": "final decision pins candidate",
      "pass": true
    },
    {
      "name": "final decision pins prefix",
      "pass": true
    },
    {
      "name": "final decision pins resume",
      "pass": true
    },
    {
      "name": "candidate export equals resume keys",
      "pass": true
    },
    {
      "name": "candidate export equals resume actual tensors",
      "pass": true,
      "tensors": 100,
      "mismatches": []
    },
    {
      "name": "baseline/candidate architecture",
      "pass": true
    },
    {
      "name": "baseline/candidate keys",
      "pass": true
    },
    {
      "name": "actual saved core tensors changed",
      "pass": true,
      "changed_names": [
        "blocks.0.br",
        "blocks.0.bc",
        "blocks.0.ln1.weight",
        "blocks.0.ln1.bias",
        "blocks.0.ln2.weight",
        "blocks.0.ln2.bias",
        "blocks.0.qkv.weight",
        "blocks.0.qkv.bias",
        "blocks.0.out.weight",
        "blocks.0.out.bias",
        "blocks.0.mlp.experts.0.0.weight",
        "blocks.0.mlp.experts.0.0.bias",
        "blocks.0.mlp.experts.0.2.weight",
        "blocks.0.mlp.experts.0.2.bias",
        "blocks.0.mlp.experts.1.0.weight",
        "blocks.0.mlp.experts.1.0.bias",
        "blocks.0.mlp.experts.1.2.weight",
        "blocks.0.mlp.experts.1.2.bias",
        "blocks.0.mlp.experts.2.0.weight",
        "blocks.0.mlp.experts.2.0.bias",
        "blocks.0.mlp.experts.2.2.weight",
        "blocks.0.mlp.experts.2.2.bias",
        "blocks.0.mlp.experts.3.0.weight",
        "blocks.0.mlp.experts.3.0.bias",
        "blocks.0.mlp.experts.3.2.weight",
        "blocks.0.mlp.experts.3.2.bias",
        "blocks.0.mlp.experts.4.0.weight",
        "blocks.0.mlp.experts.4.0.bias",
        "blocks.0.mlp.experts.4.2.weight",
        "blocks.0.mlp.experts.4.2.bias",
        "blocks.0.mlp.experts.5.0.weight",
        "blocks.0.mlp.experts.5.0.bias",
        "blocks.0.mlp.experts.5.2.weight",
        "blocks.0.mlp.experts.5.2.bias",
        "blocks.0.mlp.experts.6.0.weight",
        "blocks.0.mlp.experts.6.0.bias",
        "blocks.0.mlp.experts.6.2.weight",
        "blocks.0.mlp.experts.6.2.bias",
        "blocks.0.mlp.experts.7.0.weight",
        "blocks.0.mlp.experts.7.0.bias",
        "blocks.0.mlp.experts.7.2.weight",
        "blocks.0.mlp.experts.7.2.bias",
        "blocks.0.mlp.router.weight",
        "blocks.0.mlp.router.bias",
        "blocks.1.br",
        "blocks.1.bc",
        "blocks.1.ln1.weight",
        "blocks.1.ln1.bias",
        "blocks.1.ln2.weight",
        "blocks.1.ln2.bias",
        "blocks.1.qkv.weight",
        "blocks.1.qkv.bias",
        "blocks.1.out.weight",
        "blocks.1.out.bias",
        "blocks.1.mlp.experts.0.0.weight",
        "blocks.1.mlp.experts.0.0.bias",
        "blocks.1.mlp.experts.0.2.weight",
        "blocks.1.mlp.experts.0.2.bias",
        "blocks.1.mlp.experts.1.0.weight",
        "blocks.1.mlp.experts.1.0.bias",
        "blocks.1.mlp.experts.1.2.weight",
        "blocks.1.mlp.experts.1.2.bias",
        "blocks.1.mlp.experts.2.0.weight",
        "blocks.1.mlp.experts.2.0.bias",
        "blocks.1.mlp.experts.2.2.weight",
        "blocks.1.mlp.experts.2.2.bias",
        "blocks.1.mlp.experts.3.0.weight",
        "blocks.1.mlp.experts.3.0.bias",
        "blocks.1.mlp.experts.3.2.weight",
        "blocks.1.mlp.experts.3.2.bias",
        "blocks.1.mlp.experts.4.0.weight",
        "blocks.1.mlp.experts.4.0.bias",
        "blocks.1.mlp.experts.4.2.weight",
        "blocks.1.mlp.experts.4.2.bias",
        "blocks.1.mlp.experts.5.0.weight",
        "blocks.1.mlp.experts.5.0.bias",
        "blocks.1.mlp.experts.5.2.weight",
        "blocks.1.mlp.experts.5.2.bias",
        "blocks.1.mlp.experts.6.0.weight",
        "blocks.1.mlp.experts.6.0.bias",
        "blocks.1.mlp.experts.6.2.weight",
        "blocks.1.mlp.experts.6.2.bias",
        "blocks.1.mlp.experts.7.0.weight",
        "blocks.1.mlp.experts.7.0.bias",
        "blocks.1.mlp.experts.7.2.weight",
        "blocks.1.mlp.experts.7.2.bias",
        "blocks.1.mlp.router.weight",
        "blocks.1.mlp.router.bias",
        "ln_state.weight",
        "ln_state.bias"
      ],
      "changed_count": 90,
      "total_tensors": 100
    },
    {
      "name": "core finite actual tensors",
      "pass": true,
      "nonfinite_names": []
    },
    {
      "name": "reader finite actual tensors",
      "pass": true,
      "nonfinite_names": []
    },
    {
      "name": "prefix finite actual tensors",
      "pass": true,
      "nonfinite_names": []
    },
    {
      "name": "halt/position buffers unchanged",
      "pass": true,
      "names": [
        "position_frequencies",
        "boundary_roles",
        "halt.weight",
        "halt.bias"
      ]
    },
    {
      "name": "reader actual tensors unchanged keys",
      "pass": true
    },
    {
      "name": "reader actual tensors unchanged actual tensors",
      "pass": true,
      "tensors": 6,
      "mismatches": []
    },
    {
      "name": "prefix actual tensors unchanged keys",
      "pass": true
    },
    {
      "name": "prefix actual tensors unchanged actual tensors",
      "pass": true,
      "tensors": 6,
      "mismatches": []
    },
    {
      "name": "prefix rebound parent",
      "pass": true
    },
    {
      "name": "prefix same reader",
      "pass": true
    },
    {
      "name": "core-only resume schema",
      "pass": true
    },
    {
      "name": "Adam groups map exact core parameter order",
      "pass": true,
      "group_count": 1,
      "group_params": 96,
      "native_nonhalt_params": 96
    },
    {
      "name": "Adam hyperparameters match sealed plan",
      "pass": true
    },
    {
      "name": "populated Adam state IDs subset of groups",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.br",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.br",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.br",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.br",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.br",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.bc",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.bc",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.bc",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.bc",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.bc",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.ln1.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.ln1.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.ln1.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.ln1.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.ln1.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.ln1.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.ln1.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.ln1.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.ln1.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.ln1.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.ln2.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.ln2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.ln2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.ln2.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.ln2.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.ln2.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.ln2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.ln2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.ln2.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.ln2.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.qkv.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.qkv.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.qkv.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.qkv.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.qkv.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.qkv.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.qkv.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.qkv.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.qkv.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.qkv.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.out.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.out.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.out.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.out.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.out.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.out.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.out.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.out.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.out.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.out.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.experts.0.0.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.experts.0.0.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.experts.0.0.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.experts.0.0.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.experts.0.0.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.experts.0.0.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.experts.0.0.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.experts.0.0.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.experts.0.0.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.experts.0.0.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.experts.0.2.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.experts.0.2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.experts.0.2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.experts.0.2.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.experts.0.2.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.experts.0.2.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.experts.0.2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.experts.0.2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.experts.0.2.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.experts.0.2.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.experts.1.0.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.experts.1.0.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.experts.1.0.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.experts.1.0.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.experts.1.0.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.experts.1.0.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.experts.1.0.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.experts.1.0.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.experts.1.0.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.experts.1.0.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.experts.1.2.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.experts.1.2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.experts.1.2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.experts.1.2.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.experts.1.2.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.experts.1.2.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.experts.1.2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.experts.1.2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.experts.1.2.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.experts.1.2.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.experts.2.0.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.experts.2.0.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.experts.2.0.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.experts.2.0.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.experts.2.0.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.experts.2.0.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.experts.2.0.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.experts.2.0.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.experts.2.0.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.experts.2.0.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.experts.2.2.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.experts.2.2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.experts.2.2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.experts.2.2.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.experts.2.2.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.experts.2.2.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.experts.2.2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.experts.2.2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.experts.2.2.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.experts.2.2.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.experts.3.0.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.experts.3.0.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.experts.3.0.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.experts.3.0.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.experts.3.0.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.experts.3.0.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.experts.3.0.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.experts.3.0.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.experts.3.0.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.experts.3.0.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.experts.3.2.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.experts.3.2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.experts.3.2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.experts.3.2.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.experts.3.2.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.experts.3.2.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.experts.3.2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.experts.3.2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.experts.3.2.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.experts.3.2.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.experts.4.0.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.experts.4.0.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.experts.4.0.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.experts.4.0.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.experts.4.0.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.experts.4.0.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.experts.4.0.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.experts.4.0.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.experts.4.0.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.experts.4.0.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.experts.4.2.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.experts.4.2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.experts.4.2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.experts.4.2.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.experts.4.2.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.experts.4.2.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.experts.4.2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.experts.4.2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.experts.4.2.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.experts.4.2.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.experts.5.0.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.experts.5.0.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.experts.5.0.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.experts.5.0.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.experts.5.0.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.experts.5.0.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.experts.5.0.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.experts.5.0.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.experts.5.0.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.experts.5.0.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.experts.5.2.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.experts.5.2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.experts.5.2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.experts.5.2.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.experts.5.2.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.experts.5.2.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.experts.5.2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.experts.5.2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.experts.5.2.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.experts.5.2.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.experts.6.0.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.experts.6.0.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.experts.6.0.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.experts.6.0.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.experts.6.0.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.experts.6.0.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.experts.6.0.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.experts.6.0.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.experts.6.0.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.experts.6.0.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.experts.6.2.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.experts.6.2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.experts.6.2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.experts.6.2.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.experts.6.2.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.experts.6.2.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.experts.6.2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.experts.6.2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.experts.6.2.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.experts.6.2.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.experts.7.0.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.experts.7.0.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.experts.7.0.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.experts.7.0.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.experts.7.0.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.experts.7.0.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.experts.7.0.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.experts.7.0.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.experts.7.0.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.experts.7.0.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.experts.7.2.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.experts.7.2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.experts.7.2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.experts.7.2.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.experts.7.2.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.experts.7.2.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.experts.7.2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.experts.7.2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.experts.7.2.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.experts.7.2.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.router.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.router.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.router.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.router.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.router.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.0.mlp.router.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.0.mlp.router.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.0.mlp.router.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.0.mlp.router.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.0.mlp.router.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.br",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.br",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.br",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.br",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.br",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.bc",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.bc",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.bc",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.bc",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.bc",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.ln1.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.ln1.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.ln1.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.ln1.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.ln1.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.ln1.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.ln1.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.ln1.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.ln1.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.ln1.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.ln2.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.ln2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.ln2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.ln2.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.ln2.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.ln2.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.ln2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.ln2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.ln2.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.ln2.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.qkv.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.qkv.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.qkv.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.qkv.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.qkv.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.qkv.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.qkv.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.qkv.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.qkv.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.qkv.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.out.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.out.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.out.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.out.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.out.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.out.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.out.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.out.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.out.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.out.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.experts.0.0.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.experts.0.0.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.experts.0.0.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.experts.0.0.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.experts.0.0.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.experts.0.0.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.experts.0.0.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.experts.0.0.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.experts.0.0.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.experts.0.0.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.experts.0.2.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.experts.0.2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.experts.0.2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.experts.0.2.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.experts.0.2.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.experts.0.2.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.experts.0.2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.experts.0.2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.experts.0.2.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.experts.0.2.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.experts.1.0.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.experts.1.0.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.experts.1.0.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.experts.1.0.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.experts.1.0.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.experts.1.0.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.experts.1.0.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.experts.1.0.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.experts.1.0.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.experts.1.0.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.experts.1.2.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.experts.1.2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.experts.1.2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.experts.1.2.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.experts.1.2.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.experts.1.2.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.experts.1.2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.experts.1.2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.experts.1.2.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.experts.1.2.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.experts.2.0.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.experts.2.0.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.experts.2.0.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.experts.2.0.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.experts.2.0.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.experts.2.0.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.experts.2.0.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.experts.2.0.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.experts.2.0.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.experts.2.0.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.experts.2.2.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.experts.2.2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.experts.2.2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.experts.2.2.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.experts.2.2.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.experts.2.2.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.experts.2.2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.experts.2.2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.experts.2.2.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.experts.2.2.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.experts.3.0.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.experts.3.0.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.experts.3.0.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.experts.3.0.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.experts.3.0.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.experts.3.0.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.experts.3.0.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.experts.3.0.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.experts.3.0.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.experts.3.0.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.experts.3.2.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.experts.3.2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.experts.3.2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.experts.3.2.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.experts.3.2.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.experts.3.2.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.experts.3.2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.experts.3.2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.experts.3.2.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.experts.3.2.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.experts.4.0.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.experts.4.0.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.experts.4.0.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.experts.4.0.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.experts.4.0.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.experts.4.0.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.experts.4.0.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.experts.4.0.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.experts.4.0.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.experts.4.0.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.experts.4.2.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.experts.4.2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.experts.4.2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.experts.4.2.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.experts.4.2.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.experts.4.2.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.experts.4.2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.experts.4.2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.experts.4.2.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.experts.4.2.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.experts.5.0.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.experts.5.0.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.experts.5.0.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.experts.5.0.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.experts.5.0.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.experts.5.0.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.experts.5.0.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.experts.5.0.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.experts.5.0.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.experts.5.0.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.experts.5.2.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.experts.5.2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.experts.5.2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.experts.5.2.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.experts.5.2.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.experts.5.2.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.experts.5.2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.experts.5.2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.experts.5.2.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.experts.5.2.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.experts.6.0.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.experts.6.0.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.experts.6.0.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.experts.6.0.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.experts.6.0.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.experts.6.0.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.experts.6.0.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.experts.6.0.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.experts.6.0.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.experts.6.0.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.experts.6.2.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.experts.6.2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.experts.6.2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.experts.6.2.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.experts.6.2.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.experts.6.2.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.experts.6.2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.experts.6.2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.experts.6.2.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.experts.6.2.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.experts.7.0.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.experts.7.0.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.experts.7.0.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.experts.7.0.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.experts.7.0.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.experts.7.0.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.experts.7.0.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.experts.7.0.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.experts.7.0.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.experts.7.0.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.experts.7.2.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.experts.7.2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.experts.7.2.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.experts.7.2.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.experts.7.2.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.experts.7.2.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.experts.7.2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.experts.7.2.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.experts.7.2.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.experts.7.2.bias",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.router.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.router.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.router.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.router.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.router.weight",
      "pass": true
    },
    {
      "name": "Adam fields blocks.1.mlp.router.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step blocks.1.mlp.router.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg blocks.1.mlp.router.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq blocks.1.mlp.router.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative blocks.1.mlp.router.bias",
      "pass": true
    },
    {
      "name": "Adam fields ln_state.weight",
      "pass": true
    },
    {
      "name": "Adam positive bounded step ln_state.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg ln_state.weight",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq ln_state.weight",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative ln_state.weight",
      "pass": true
    },
    {
      "name": "Adam fields ln_state.bias",
      "pass": true
    },
    {
      "name": "Adam positive bounded step ln_state.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg ln_state.bias",
      "pass": true
    },
    {
      "name": "Adam finite matching exp_avg_sq ln_state.bias",
      "pass": true
    },
    {
      "name": "Adam second moment nonnegative ln_state.bias",
      "pass": true
    },
    {
      "name": "actual nonzero Adam moments",
      "pass": true
    },
    {
      "name": "resume and JSON ledger exact equality",
      "pass": true
    },
    {
      "name": "stored RNG tensors finite uint8",
      "pass": true
    },
    {
      "name": "repeat input/source byte hashes unchanged",
      "pass": true,
      "changed_files": 0
    }
  ],
  "measurements": {
    "Adam_states": [
      {
        "id": 2,
        "parameter": "blocks.0.br",
        "shape": [
          8,
          9
        ],
        "step": 25.0,
        "exp_avg_nonzero": 8,
        "exp_avg_sq_nonzero": 8
      },
      {
        "id": 3,
        "parameter": "blocks.0.bc",
        "shape": [
          8,
          9
        ],
        "step": 25.0,
        "exp_avg_nonzero": 48,
        "exp_avg_sq_nonzero": 48
      },
      {
        "id": 4,
        "parameter": "blocks.0.ln1.weight",
        "shape": [
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 256,
        "exp_avg_sq_nonzero": 256
      },
      {
        "id": 5,
        "parameter": "blocks.0.ln1.bias",
        "shape": [
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 256,
        "exp_avg_sq_nonzero": 256
      },
      {
        "id": 6,
        "parameter": "blocks.0.ln2.weight",
        "shape": [
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 256,
        "exp_avg_sq_nonzero": 256
      },
      {
        "id": 7,
        "parameter": "blocks.0.ln2.bias",
        "shape": [
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 256,
        "exp_avg_sq_nonzero": 256
      },
      {
        "id": 8,
        "parameter": "blocks.0.qkv.weight",
        "shape": [
          768,
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 196608,
        "exp_avg_sq_nonzero": 196608
      },
      {
        "id": 9,
        "parameter": "blocks.0.qkv.bias",
        "shape": [
          768
        ],
        "step": 25.0,
        "exp_avg_nonzero": 768,
        "exp_avg_sq_nonzero": 768
      },
      {
        "id": 10,
        "parameter": "blocks.0.out.weight",
        "shape": [
          256,
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 65536,
        "exp_avg_sq_nonzero": 65536
      },
      {
        "id": 11,
        "parameter": "blocks.0.out.bias",
        "shape": [
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 256,
        "exp_avg_sq_nonzero": 256
      },
      {
        "id": 12,
        "parameter": "blocks.0.mlp.experts.0.0.weight",
        "shape": [
          1024,
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 262144,
        "exp_avg_sq_nonzero": 262144
      },
      {
        "id": 13,
        "parameter": "blocks.0.mlp.experts.0.0.bias",
        "shape": [
          1024
        ],
        "step": 25.0,
        "exp_avg_nonzero": 1024,
        "exp_avg_sq_nonzero": 1024
      },
      {
        "id": 14,
        "parameter": "blocks.0.mlp.experts.0.2.weight",
        "shape": [
          256,
          1024
        ],
        "step": 25.0,
        "exp_avg_nonzero": 262144,
        "exp_avg_sq_nonzero": 262144
      },
      {
        "id": 15,
        "parameter": "blocks.0.mlp.experts.0.2.bias",
        "shape": [
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 256,
        "exp_avg_sq_nonzero": 256
      },
      {
        "id": 16,
        "parameter": "blocks.0.mlp.experts.1.0.weight",
        "shape": [
          1024,
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 262144,
        "exp_avg_sq_nonzero": 262144
      },
      {
        "id": 17,
        "parameter": "blocks.0.mlp.experts.1.0.bias",
        "shape": [
          1024
        ],
        "step": 25.0,
        "exp_avg_nonzero": 1024,
        "exp_avg_sq_nonzero": 1024
      },
      {
        "id": 18,
        "parameter": "blocks.0.mlp.experts.1.2.weight",
        "shape": [
          256,
          1024
        ],
        "step": 25.0,
        "exp_avg_nonzero": 262144,
        "exp_avg_sq_nonzero": 262144
      },
      {
        "id": 19,
        "parameter": "blocks.0.mlp.experts.1.2.bias",
        "shape": [
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 256,
        "exp_avg_sq_nonzero": 256
      },
      {
        "id": 20,
        "parameter": "blocks.0.mlp.experts.2.0.weight",
        "shape": [
          1024,
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 262144,
        "exp_avg_sq_nonzero": 262144
      },
      {
        "id": 21,
        "parameter": "blocks.0.mlp.experts.2.0.bias",
        "shape": [
          1024
        ],
        "step": 25.0,
        "exp_avg_nonzero": 1024,
        "exp_avg_sq_nonzero": 1024
      },
      {
        "id": 22,
        "parameter": "blocks.0.mlp.experts.2.2.weight",
        "shape": [
          256,
          1024
        ],
        "step": 25.0,
        "exp_avg_nonzero": 262144,
        "exp_avg_sq_nonzero": 262144
      },
      {
        "id": 23,
        "parameter": "blocks.0.mlp.experts.2.2.bias",
        "shape": [
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 256,
        "exp_avg_sq_nonzero": 256
      },
      {
        "id": 24,
        "parameter": "blocks.0.mlp.experts.3.0.weight",
        "shape": [
          1024,
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 262144,
        "exp_avg_sq_nonzero": 262144
      },
      {
        "id": 25,
        "parameter": "blocks.0.mlp.experts.3.0.bias",
        "shape": [
          1024
        ],
        "step": 25.0,
        "exp_avg_nonzero": 1024,
        "exp_avg_sq_nonzero": 1024
      },
      {
        "id": 26,
        "parameter": "blocks.0.mlp.experts.3.2.weight",
        "shape": [
          256,
          1024
        ],
        "step": 25.0,
        "exp_avg_nonzero": 262144,
        "exp_avg_sq_nonzero": 262144
      },
      {
        "id": 27,
        "parameter": "blocks.0.mlp.experts.3.2.bias",
        "shape": [
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 256,
        "exp_avg_sq_nonzero": 256
      },
      {
        "id": 28,
        "parameter": "blocks.0.mlp.experts.4.0.weight",
        "shape": [
          1024,
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 262144,
        "exp_avg_sq_nonzero": 262144
      },
      {
        "id": 29,
        "parameter": "blocks.0.mlp.experts.4.0.bias",
        "shape": [
          1024
        ],
        "step": 25.0,
        "exp_avg_nonzero": 1024,
        "exp_avg_sq_nonzero": 1024
      },
      {
        "id": 30,
        "parameter": "blocks.0.mlp.experts.4.2.weight",
        "shape": [
          256,
          1024
        ],
        "step": 25.0,
        "exp_avg_nonzero": 262144,
        "exp_avg_sq_nonzero": 262144
      },
      {
        "id": 31,
        "parameter": "blocks.0.mlp.experts.4.2.bias",
        "shape": [
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 256,
        "exp_avg_sq_nonzero": 256
      },
      {
        "id": 32,
        "parameter": "blocks.0.mlp.experts.5.0.weight",
        "shape": [
          1024,
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 262144,
        "exp_avg_sq_nonzero": 262144
      },
      {
        "id": 33,
        "parameter": "blocks.0.mlp.experts.5.0.bias",
        "shape": [
          1024
        ],
        "step": 25.0,
        "exp_avg_nonzero": 1024,
        "exp_avg_sq_nonzero": 1024
      },
      {
        "id": 34,
        "parameter": "blocks.0.mlp.experts.5.2.weight",
        "shape": [
          256,
          1024
        ],
        "step": 25.0,
        "exp_avg_nonzero": 262144,
        "exp_avg_sq_nonzero": 262144
      },
      {
        "id": 35,
        "parameter": "blocks.0.mlp.experts.5.2.bias",
        "shape": [
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 256,
        "exp_avg_sq_nonzero": 256
      },
      {
        "id": 36,
        "parameter": "blocks.0.mlp.experts.6.0.weight",
        "shape": [
          1024,
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 262144,
        "exp_avg_sq_nonzero": 262144
      },
      {
        "id": 37,
        "parameter": "blocks.0.mlp.experts.6.0.bias",
        "shape": [
          1024
        ],
        "step": 25.0,
        "exp_avg_nonzero": 1024,
        "exp_avg_sq_nonzero": 1024
      },
      {
        "id": 38,
        "parameter": "blocks.0.mlp.experts.6.2.weight",
        "shape": [
          256,
          1024
        ],
        "step": 25.0,
        "exp_avg_nonzero": 262144,
        "exp_avg_sq_nonzero": 262144
      },
      {
        "id": 39,
        "parameter": "blocks.0.mlp.experts.6.2.bias",
        "shape": [
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 256,
        "exp_avg_sq_nonzero": 256
      },
      {
        "id": 40,
        "parameter": "blocks.0.mlp.experts.7.0.weight",
        "shape": [
          1024,
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 262144,
        "exp_avg_sq_nonzero": 262144
      },
      {
        "id": 41,
        "parameter": "blocks.0.mlp.experts.7.0.bias",
        "shape": [
          1024
        ],
        "step": 25.0,
        "exp_avg_nonzero": 1024,
        "exp_avg_sq_nonzero": 1024
      },
      {
        "id": 42,
        "parameter": "blocks.0.mlp.experts.7.2.weight",
        "shape": [
          256,
          1024
        ],
        "step": 25.0,
        "exp_avg_nonzero": 262144,
        "exp_avg_sq_nonzero": 262144
      },
      {
        "id": 43,
        "parameter": "blocks.0.mlp.experts.7.2.bias",
        "shape": [
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 256,
        "exp_avg_sq_nonzero": 256
      },
      {
        "id": 44,
        "parameter": "blocks.0.mlp.router.weight",
        "shape": [
          8,
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 2048,
        "exp_avg_sq_nonzero": 2048
      },
      {
        "id": 45,
        "parameter": "blocks.0.mlp.router.bias",
        "shape": [
          8
        ],
        "step": 25.0,
        "exp_avg_nonzero": 8,
        "exp_avg_sq_nonzero": 8
      },
      {
        "id": 46,
        "parameter": "blocks.1.br",
        "shape": [
          8,
          9
        ],
        "step": 25.0,
        "exp_avg_nonzero": 8,
        "exp_avg_sq_nonzero": 8
      },
      {
        "id": 47,
        "parameter": "blocks.1.bc",
        "shape": [
          8,
          9
        ],
        "step": 25.0,
        "exp_avg_nonzero": 48,
        "exp_avg_sq_nonzero": 48
      },
      {
        "id": 48,
        "parameter": "blocks.1.ln1.weight",
        "shape": [
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 256,
        "exp_avg_sq_nonzero": 256
      },
      {
        "id": 49,
        "parameter": "blocks.1.ln1.bias",
        "shape": [
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 256,
        "exp_avg_sq_nonzero": 256
      },
      {
        "id": 50,
        "parameter": "blocks.1.ln2.weight",
        "shape": [
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 256,
        "exp_avg_sq_nonzero": 256
      },
      {
        "id": 51,
        "parameter": "blocks.1.ln2.bias",
        "shape": [
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 256,
        "exp_avg_sq_nonzero": 256
      },
      {
        "id": 52,
        "parameter": "blocks.1.qkv.weight",
        "shape": [
          768,
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 196608,
        "exp_avg_sq_nonzero": 196608
      },
      {
        "id": 53,
        "parameter": "blocks.1.qkv.bias",
        "shape": [
          768
        ],
        "step": 25.0,
        "exp_avg_nonzero": 768,
        "exp_avg_sq_nonzero": 768
      },
      {
        "id": 54,
        "parameter": "blocks.1.out.weight",
        "shape": [
          256,
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 65536,
        "exp_avg_sq_nonzero": 65536
      },
      {
        "id": 55,
        "parameter": "blocks.1.out.bias",
        "shape": [
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 256,
        "exp_avg_sq_nonzero": 256
      },
      {
        "id": 56,
        "parameter": "blocks.1.mlp.experts.0.0.weight",
        "shape": [
          1024,
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 262144,
        "exp_avg_sq_nonzero": 262144
      },
      {
        "id": 57,
        "parameter": "blocks.1.mlp.experts.0.0.bias",
        "shape": [
          1024
        ],
        "step": 25.0,
        "exp_avg_nonzero": 1024,
        "exp_avg_sq_nonzero": 1024
      },
      {
        "id": 58,
        "parameter": "blocks.1.mlp.experts.0.2.weight",
        "shape": [
          256,
          1024
        ],
        "step": 25.0,
        "exp_avg_nonzero": 262144,
        "exp_avg_sq_nonzero": 262144
      },
      {
        "id": 59,
        "parameter": "blocks.1.mlp.experts.0.2.bias",
        "shape": [
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 256,
        "exp_avg_sq_nonzero": 256
      },
      {
        "id": 60,
        "parameter": "blocks.1.mlp.experts.1.0.weight",
        "shape": [
          1024,
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 262144,
        "exp_avg_sq_nonzero": 262144
      },
      {
        "id": 61,
        "parameter": "blocks.1.mlp.experts.1.0.bias",
        "shape": [
          1024
        ],
        "step": 25.0,
        "exp_avg_nonzero": 1024,
        "exp_avg_sq_nonzero": 1024
      },
      {
        "id": 62,
        "parameter": "blocks.1.mlp.experts.1.2.weight",
        "shape": [
          256,
          1024
        ],
        "step": 25.0,
        "exp_avg_nonzero": 262144,
        "exp_avg_sq_nonzero": 262144
      },
      {
        "id": 63,
        "parameter": "blocks.1.mlp.experts.1.2.bias",
        "shape": [
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 256,
        "exp_avg_sq_nonzero": 256
      },
      {
        "id": 64,
        "parameter": "blocks.1.mlp.experts.2.0.weight",
        "shape": [
          1024,
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 262144,
        "exp_avg_sq_nonzero": 262144
      },
      {
        "id": 65,
        "parameter": "blocks.1.mlp.experts.2.0.bias",
        "shape": [
          1024
        ],
        "step": 25.0,
        "exp_avg_nonzero": 1024,
        "exp_avg_sq_nonzero": 1024
      },
      {
        "id": 66,
        "parameter": "blocks.1.mlp.experts.2.2.weight",
        "shape": [
          256,
          1024
        ],
        "step": 25.0,
        "exp_avg_nonzero": 262144,
        "exp_avg_sq_nonzero": 262144
      },
      {
        "id": 67,
        "parameter": "blocks.1.mlp.experts.2.2.bias",
        "shape": [
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 256,
        "exp_avg_sq_nonzero": 256
      },
      {
        "id": 68,
        "parameter": "blocks.1.mlp.experts.3.0.weight",
        "shape": [
          1024,
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 262144,
        "exp_avg_sq_nonzero": 262144
      },
      {
        "id": 69,
        "parameter": "blocks.1.mlp.experts.3.0.bias",
        "shape": [
          1024
        ],
        "step": 25.0,
        "exp_avg_nonzero": 1024,
        "exp_avg_sq_nonzero": 1024
      },
      {
        "id": 70,
        "parameter": "blocks.1.mlp.experts.3.2.weight",
        "shape": [
          256,
          1024
        ],
        "step": 25.0,
        "exp_avg_nonzero": 262144,
        "exp_avg_sq_nonzero": 262144
      },
      {
        "id": 71,
        "parameter": "blocks.1.mlp.experts.3.2.bias",
        "shape": [
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 256,
        "exp_avg_sq_nonzero": 256
      },
      {
        "id": 72,
        "parameter": "blocks.1.mlp.experts.4.0.weight",
        "shape": [
          1024,
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 262144,
        "exp_avg_sq_nonzero": 262144
      },
      {
        "id": 73,
        "parameter": "blocks.1.mlp.experts.4.0.bias",
        "shape": [
          1024
        ],
        "step": 25.0,
        "exp_avg_nonzero": 1024,
        "exp_avg_sq_nonzero": 1024
      },
      {
        "id": 74,
        "parameter": "blocks.1.mlp.experts.4.2.weight",
        "shape": [
          256,
          1024
        ],
        "step": 25.0,
        "exp_avg_nonzero": 262144,
        "exp_avg_sq_nonzero": 262144
      },
      {
        "id": 75,
        "parameter": "blocks.1.mlp.experts.4.2.bias",
        "shape": [
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 256,
        "exp_avg_sq_nonzero": 256
      },
      {
        "id": 76,
        "parameter": "blocks.1.mlp.experts.5.0.weight",
        "shape": [
          1024,
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 262144,
        "exp_avg_sq_nonzero": 262144
      },
      {
        "id": 77,
        "parameter": "blocks.1.mlp.experts.5.0.bias",
        "shape": [
          1024
        ],
        "step": 25.0,
        "exp_avg_nonzero": 1024,
        "exp_avg_sq_nonzero": 1024
      },
      {
        "id": 78,
        "parameter": "blocks.1.mlp.experts.5.2.weight",
        "shape": [
          256,
          1024
        ],
        "step": 25.0,
        "exp_avg_nonzero": 262144,
        "exp_avg_sq_nonzero": 262144
      },
      {
        "id": 79,
        "parameter": "blocks.1.mlp.experts.5.2.bias",
        "shape": [
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 256,
        "exp_avg_sq_nonzero": 256
      },
      {
        "id": 80,
        "parameter": "blocks.1.mlp.experts.6.0.weight",
        "shape": [
          1024,
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 262144,
        "exp_avg_sq_nonzero": 262144
      },
      {
        "id": 81,
        "parameter": "blocks.1.mlp.experts.6.0.bias",
        "shape": [
          1024
        ],
        "step": 25.0,
        "exp_avg_nonzero": 1024,
        "exp_avg_sq_nonzero": 1024
      },
      {
        "id": 82,
        "parameter": "blocks.1.mlp.experts.6.2.weight",
        "shape": [
          256,
          1024
        ],
        "step": 25.0,
        "exp_avg_nonzero": 262144,
        "exp_avg_sq_nonzero": 262144
      },
      {
        "id": 83,
        "parameter": "blocks.1.mlp.experts.6.2.bias",
        "shape": [
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 256,
        "exp_avg_sq_nonzero": 256
      },
      {
        "id": 84,
        "parameter": "blocks.1.mlp.experts.7.0.weight",
        "shape": [
          1024,
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 262144,
        "exp_avg_sq_nonzero": 262144
      },
      {
        "id": 85,
        "parameter": "blocks.1.mlp.experts.7.0.bias",
        "shape": [
          1024
        ],
        "step": 25.0,
        "exp_avg_nonzero": 1024,
        "exp_avg_sq_nonzero": 1024
      },
      {
        "id": 86,
        "parameter": "blocks.1.mlp.experts.7.2.weight",
        "shape": [
          256,
          1024
        ],
        "step": 25.0,
        "exp_avg_nonzero": 262144,
        "exp_avg_sq_nonzero": 262144
      },
      {
        "id": 87,
        "parameter": "blocks.1.mlp.experts.7.2.bias",
        "shape": [
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 256,
        "exp_avg_sq_nonzero": 256
      },
      {
        "id": 88,
        "parameter": "blocks.1.mlp.router.weight",
        "shape": [
          8,
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 2048,
        "exp_avg_sq_nonzero": 2048
      },
      {
        "id": 89,
        "parameter": "blocks.1.mlp.router.bias",
        "shape": [
          8
        ],
        "step": 25.0,
        "exp_avg_nonzero": 8,
        "exp_avg_sq_nonzero": 8
      },
      {
        "id": 94,
        "parameter": "ln_state.weight",
        "shape": [
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 256,
        "exp_avg_sq_nonzero": 256
      },
      {
        "id": 95,
        "parameter": "ln_state.bias",
        "shape": [
          256
        ],
        "step": 25.0,
        "exp_avg_nonzero": 256,
        "exp_avg_sq_nonzero": 256
      }
    ],
    "Adam_missing_state_parameters": [
      "tok.weight",
      "slot.weight",
      "ln_out.weight",
      "ln_out.bias",
      "head.weight",
      "head.bias"
    ],
    "populated_Adam_state_count": 90,
    "ledger_updates_not_independent_step_history": 25,
    "reader_limitation": "same frozen reader file is referenced; no separate post-training reader export exists. Does not prove live training-time memory immutability."
  },
  "inference_calls": 0,
  "optimizer_steps": 0,
  "activation": false,
  "actual_day_experience": false,
  "scope": "actual saved checkpoint bytes, one trained seed0; no learning/retention/semantic claim",
  "pass": true,
  "checks_passed": 481,
  "checks_total": 481
}
{"returncode": 0, "model_forwards": 0, "optimizer_steps": 0}
rc=0
