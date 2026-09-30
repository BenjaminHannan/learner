{"torch": "2.11.0+cu128", "gpu": "NVIDIA GeForce RTX 5070 Ti", "scope": "awake only"}
{
  "scope": "contract only; random initialized; no empirical task performance",
  "seeds": [
    0,
    1
  ],
  "torch": "2.11.0+cu128",
  "checks": {
    "s0_symbolic_labels_disjoint_structures_and_order": true,
    "s0_full_bptt_program_attention_router_gradients_no_updates": true,
    "s0_communication_causal_and_cut_isolated": true,
    "s0_no_table_prompt_passthrough_and_no_cached_batch": true,
    "s0_learned_stop_removes_rows_and_cap": true,
    "s0_human_raw_notebook_digest_latent_only_boundary": true,
    "s1_symbolic_labels_disjoint_structures_and_order": true,
    "s1_full_bptt_program_attention_router_gradients_no_updates": true,
    "s1_communication_causal_and_cut_isolated": true,
    "s1_no_table_prompt_passthrough_and_no_cached_batch": true,
    "s1_learned_stop_removes_rows_and_cap": true,
    "s1_human_raw_notebook_digest_latent_only_boundary": true,
    "source_tensor_api_notebook_attention_export_empty_memory": true,
    "serialization_roundtrip_and_idle_STOP_guards_no_updates": true,
    "no_training_no_optimizer_steps": true
  },
  "passed": 15,
  "total": 15,
  "evidence": {
    "s0_gradient_l1": {
      "record.record_gru.weight_ih": 4.269599914550781,
      "numeric.recurrent.weight_ih": 20.161781311035156,
      "blocks.0.attention.q.weight": 3.8350636959075928,
      "blocks.0.router.weight": 27.645750045776367
    },
    "s0_batch_isolation_error": 7.152557373046875e-07,
    "parameter_counts": {
      "compose": {
        "stored": 323160,
        "trainable": 323160,
        "transformer": 83464,
        "record": 119970,
        "numeric": 41840
      },
      "no_communication": {
        "stored": 323160,
        "trainable": 323160,
        "transformer": 83464,
        "record": 119970,
        "numeric": 41840
      },
      "joint": {
        "stored": 323180,
        "trainable": 323180,
        "transformer": 245294,
        "record": 0,
        "numeric": 0
      },
      "plain": {
        "stored": 322860,
        "trainable": 322860,
        "transformer": 244974,
        "record": 0,
        "numeric": 0
      },
      "record_only": {
        "stored": 281320,
        "trainable": 281320,
        "transformer": 83464,
        "record": 119970,
        "numeric": 0
      },
      "numeric_only": {
        "stored": 203190,
        "trainable": 203190,
        "transformer": 83464,
        "record": 0,
        "numeric": 41840
      }
    },
    "s1_gradient_l1": {
      "record.record_gru.weight_ih": 1.3972944021224976,
      "numeric.recurrent.weight_ih": 5.897705078125,
      "blocks.0.attention.q.weight": 0.459669291973114,
      "blocks.0.router.weight": 6.569854259490967
    },
    "s1_batch_isolation_error": 6.407499313354492e-07
  },
  "optimizer_steps": 0,
  "trained": false,
  "holdout_opened": false
}
{"utc": "2026-09-30T03:19:02.716593+00:00", "completed": "compose-s0", "seconds": 57.92200000000594, "sleep_updates": 0}
{"utc": "2026-09-30T03:19:42.616823+00:00", "completed": "no_communication-s0", "seconds": 39.79700000000594, "sleep_updates": 0}
{"utc": "2026-09-30T03:19:59.888091+00:00", "completed": "joint-s0", "seconds": 17.202999999994063, "sleep_updates": 0}
{"utc": "2026-09-30T03:20:19.375190+00:00", "completed": "plain-s0", "seconds": 19.421999999991385, "sleep_updates": 0}
{"utc": "2026-09-30T03:21:04.662456+00:00", "completed": "record_only-s0", "seconds": 45.21899999999732, "sleep_updates": 0}
{"utc": "2026-09-30T03:21:46.119838+00:00", "completed": "numeric_only-s0", "seconds": 41.375, "sleep_updates": 0}
{"utc": "2026-09-30T03:22:44.308547+00:00", "completed": "compose-s1", "seconds": 57.54700000000594, "sleep_updates": 0}
{"utc": "2026-09-30T03:23:23.396276+00:00", "completed": "no_communication-s1", "seconds": 39.01499999999942, "sleep_updates": 0}
{"utc": "2026-09-30T03:23:41.519696+00:00", "completed": "joint-s1", "seconds": 18.046999999991385, "sleep_updates": 0}
{"utc": "2026-09-30T03:24:00.336914+00:00", "completed": "plain-s1", "seconds": 18.735000000000582, "sleep_updates": 0}
{"utc": "2026-09-30T03:24:46.199181+00:00", "completed": "record_only-s1", "seconds": 45.8130000000092, "sleep_updates": 0}
{"utc": "2026-09-30T03:25:27.747363+00:00", "completed": "numeric_only-s1", "seconds": 41.469000000011874, "sleep_updates": 0}
{
  "scope": "AWAKE TRAIN/dev diagnostic only",
  "rows": [
    {
      "seed": 0,
      "split": "dev_structure",
      "candidate": 24,
      "n": 200,
      "controls": {
        "no_communication": 25,
        "joint": 23,
        "plain": 23,
        "record_only": 24,
        "numeric_only": 27
      },
      "gap_pp": -1.5,
      "screen_bar_pp": 10.0,
      "screen_met": false
    },
    {
      "seed": 0,
      "split": "dev_order",
      "candidate": 27,
      "n": 200,
      "controls": {
        "no_communication": 25,
        "joint": 20,
        "plain": 16,
        "record_only": 16,
        "numeric_only": 21
      },
      "gap_pp": 1.0,
      "screen_bar_pp": 10.0,
      "screen_met": false
    },
    {
      "seed": 1,
      "split": "dev_structure",
      "candidate": 28,
      "n": 200,
      "controls": {
        "no_communication": 34,
        "joint": 26,
        "plain": 25,
        "record_only": 31,
        "numeric_only": 27
      },
      "gap_pp": -3.0,
      "screen_bar_pp": 10.0,
      "screen_met": false
    },
    {
      "seed": 1,
      "split": "dev_order",
      "candidate": 22,
      "n": 200,
      "controls": {
        "no_communication": 21,
        "joint": 22,
        "plain": 21,
        "record_only": 18,
        "numeric_only": 16
      },
      "gap_pp": 0.0,
      "screen_bar_pp": 10.0,
      "screen_met": false
    }
  ],
  "stop_readiness": {
    "compose-s0": {
      "checkpoint_sha256": "f13c7949fede60c4f8aa4f3e95529d635e8824afcb41358982ab51ce12d7acd4",
      "split": "TRAIN_retention",
      "n": 100,
      "learned_stop_exact": 13,
      "fixed_exact": 13,
      "stop_loss_count": 0,
      "mean_rounds": 6.0,
      "cap_hits": 100,
      "frozen_marks": {
        "exact_min": 90,
        "stop_loss_max": 2,
        "mean_rounds_max": 4.5,
        "cap_hits_max": 10
      },
      "ready_for_SEPARATE_stop_review": false,
      "authorizes_sleep": false,
      "independent_stop_audit_required": true
    },
    "no_communication-s0": {
      "checkpoint_sha256": "236a153c1553d60584eaddc400eb11325efad851bf2a258c2f327684528f877e",
      "split": "TRAIN_retention",
      "n": 100,
      "learned_stop_exact": 12,
      "fixed_exact": 12,
      "stop_loss_count": 0,
      "mean_rounds": 6.0,
      "cap_hits": 100,
      "frozen_marks": {
        "exact_min": 90,
        "stop_loss_max": 2,
        "mean_rounds_max": 4.5,
        "cap_hits_max": 10
      },
      "ready_for_SEPARATE_stop_review": false,
      "authorizes_sleep": false,
      "independent_stop_audit_required": true
    },
    "joint-s0": {
      "checkpoint_sha256": "889cf3bf4847395defb961c4a6ad198433dc271a9b0e820bea7e138e7e53642f",
      "split": "TRAIN_retention",
      "n": 100,
      "learned_stop_exact": 14,
      "fixed_exact": 14,
      "stop_loss_count": 0,
      "mean_rounds": 6.0,
      "cap_hits": 100,
      "frozen_marks": {
        "exact_min": 90,
        "stop_loss_max": 2,
        "mean_rounds_max": 4.5,
        "cap_hits_max": 10
      },
      "ready_for_SEPARATE_stop_review": false,
      "authorizes_sleep": false,
      "independent_stop_audit_required": true
    },
    "plain-s0": {
      "checkpoint_sha256": "f73c95d6616358a90382155efe7c8b116e5a5088b8307f3692c050002770d3b1",
      "split": "TRAIN_retention",
      "n": 100,
      "learned_stop_exact": 19,
      "fixed_exact": 19,
      "stop_loss_count": 0,
      "mean_rounds": 6.0,
      "cap_hits": 100,
      "frozen_marks": {
        "exact_min": 90,
        "stop_loss_max": 2,
        "mean_rounds_max": 4.5,
        "cap_hits_max": 10
      },
      "ready_for_SEPARATE_stop_review": false,
      "authorizes_sleep": false,
      "independent_stop_audit_required": true
    },
    "record_only-s0": {
      "checkpoint_sha256": "6bf73c790713c4833caed4d862e3fb3c4cffe4b4a4ca1e2007d5de25eef31589",
      "split": "TRAIN_retention",
      "n": 100,
      "learned_stop_exact": 20,
      "fixed_exact": 20,
      "stop_loss_count": 0,
      "mean_rounds": 6.0,
      "cap_hits": 100,
      "frozen_marks": {
        "exact_min": 90,
        "stop_loss_max": 2,
        "mean_rounds_max": 4.5,
        "cap_hits_max": 10
      },
      "ready_for_SEPARATE_stop_review": false,
      "authorizes_sleep": false,
      "independent_stop_audit_required": true
    },
    "numeric_only-s0": {
      "checkpoint_sha256": "d977532cebcaf695a348debb3f4cc38d66149b073dbc5748529b67200beb330e",
      "split": "TRAIN_retention",
      "n": 100,
      "learned_stop_exact": 17,
      "fixed_exact": 17,
      "stop_loss_count": 0,
      "mean_rounds": 6.0,
      "cap_hits": 100,
      "frozen_marks": {
        "exact_min": 90,
        "stop_loss_max": 2,
        "mean_rounds_max": 4.5,
        "cap_hits_max": 10
      },
      "ready_for_SEPARATE_stop_review": false,
      "authorizes_sleep": false,
      "independent_stop_audit_required": true
    },
    "compose-s1": {
      "checkpoint_sha256": "886359f4b54edffd88d44085f6f67ad0d3df2d7f6a63630a1ae1e3f2b31c3a6c",
      "split": "TRAIN_retention",
      "n": 100,
      "learned_stop_exact": 15,
      "fixed_exact": 15,
      "stop_loss_count": 0,
      "mean_rounds": 6.0,
      "cap_hits": 100,
      "frozen_marks": {
        "exact_min": 90,
        "stop_loss_max": 2,
        "mean_rounds_max": 4.5,
        "cap_hits_max": 10
      },
      "ready_for_SEPARATE_stop_review": false,
      "authorizes_sleep": false,
      "independent_stop_audit_required": true
    },
    "no_communication-s1": {
      "checkpoint_sha256": "dac3fb8b66afa98046e5f15a7ab187d658a69c9b7cc4bdb5644519a194316c31",
      "split": "TRAIN_retention",
      "n": 100,
      "learned_stop_exact": 18,
      "fixed_exact": 18,
      "stop_loss_count": 0,
      "mean_rounds": 6.0,
      "cap_hits": 100,
      "frozen_marks": {
        "exact_min": 90,
        "stop_loss_max": 2,
        "mean_rounds_max": 4.5,
        "cap_hits_max": 10
      },
      "ready_for_SEPARATE_stop_review": false,
      "authorizes_sleep": false,
      "independent_stop_audit_required": true
    },
    "joint-s1": {
      "checkpoint_sha256": "ec4acf2d5ed64dce275fbf147c10e07fe48e1a5157bffb186693976e7d791287",
      "split": "TRAIN_retention",
      "n": 100,
      "learned_stop_exact": 18,
      "fixed_exact": 18,
      "stop_loss_count": 0,
      "mean_rounds": 6.0,
      "cap_hits": 100,
      "frozen_marks": {
        "exact_min": 90,
        "stop_loss_max": 2,
        "mean_rounds_max": 4.5,
        "cap_hits_max": 10
      },
      "ready_for_SEPARATE_stop_review": false,
      "authorizes_sleep": false,
      "independent_stop_audit_required": true
    },
    "plain-s1": {
      "checkpoint_sha256": "98e09c1e3324c35f6af3665f876ae79b7598ce4bb7cf8866839f23eef37010ce",
      "split": "TRAIN_retention",
      "n": 100,
      "learned_stop_exact": 15,
      "fixed_exact": 15,
      "stop_loss_count": 0,
      "mean_rounds": 6.0,
      "cap_hits": 100,
      "frozen_marks": {
        "exact_min": 90,
        "stop_loss_max": 2,
        "mean_rounds_max": 4.5,
        "cap_hits_max": 10
      },
      "ready_for_SEPARATE_stop_review": false,
      "authorizes_sleep": false,
      "independent_stop_audit_required": true
    },
    "record_only-s1": {
      "checkpoint_sha256": "c880b4a4a424e7126f1e7844863b3725c2ee4feeff7ff81b851bbe789a9749ee",
      "split": "TRAIN_retention",
      "n": 100,
      "learned_stop_exact": 15,
      "fixed_exact": 15,
      "stop_loss_count": 0,
      "mean_rounds": 6.0,
      "cap_hits": 100,
      "frozen_marks": {
        "exact_min": 90,
        "stop_loss_max": 2,
        "mean_rounds_max": 4.5,
        "cap_hits_max": 10
      },
      "ready_for_SEPARATE_stop_review": false,
      "authorizes_sleep": false,
      "independent_stop_audit_required": true
    },
    "numeric_only-s1": {
      "checkpoint_sha256": "5a232583f2ec94c6b63247519e156e7073f3553233633176d0c7e0851f4ea906",
      "split": "TRAIN_retention",
      "n": 100,
      "learned_stop_exact": 16,
      "fixed_exact": 16,
      "stop_loss_count": 0,
      "mean_rounds": 6.0,
      "cap_hits": 100,
      "frozen_marks": {
        "exact_min": 90,
        "stop_loss_max": 2,
        "mean_rounds_max": 4.5,
        "cap_hits_max": 10
      },
      "ready_for_SEPARATE_stop_review": false,
      "authorizes_sleep": false,
      "independent_stop_audit_required": true
    }
  },
  "decision": "SCREEN NOT MET; DIAGNOSE WITHOUT PROMOTION",
  "statistical_claim": "INSUFFICIENT: two-seed diagnostic span only",
  "sleep_updates": 0,
  "sleep_authorized": false,
  "holdout_opened": false,
  "english_proven": false,
  "general_reasoner_proven": false,
  "F_eq": "NOT EVALUATED",
  "F_few": "NOT EVALUATED"
}
{"returncode": 0, "raw_sha256": "b8de626943b66c8e9d4990eed5df629b914aeef4c50cbae3e2c83a61dccefc3c"}
rc=0
