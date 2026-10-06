# Adaptive Compute Architecture

### Sparse cognition, latent reasoning, and the right to think harder

---

A standard transformer spends the same compute on every token. It will lavish identical attention on a trivial schema field and a make-or-break decision. This is a strange property if you stop to look at it. No human cognition works this way. No serious physical system works this way. We do not understand why we have accepted it in our models for as long as we have.

This devlog is about what changes when you stop accepting it.

## The wrong default

The default of "one forward pass, equal effort" is a holdover from the era when we did not yet know how to do anything else. In 2026, we know how. Latent reasoning loops, mixture-of-depths routing, evidence-token routers, speculative decoding, sparse expert routing -- all of them are different angles on the same realization: **compute is a resource the model should be able to spend, not a constant it has to consume**.

In our system, this is not an inference-time bolt-on. It is a property of the architecture, baked in from training. The model learns from the beginning that not every input deserves the same depth, and that abstention from compute is sometimes the right answer.

## Three places where compute can land

Without describing the exact routing logic -- which is one of the more sensitive parts of the recipe -- there are three classes of place where adaptive compute shows up in our stack.

**Reflex layers.** A small, fast pathway handles the cases where the answer is obvious. Schema validation. Known-trivial states. Inputs whose action is overwhelmingly determined by a single feature. These get a shallow pass with minimal depth and exit early. The model is not pretending to think when there is nothing to think about.

**Deep reasoning.** Hard inputs trigger a different pathway. Latent reasoning loops let the model iterate in continuous representation space before committing to discrete output. The number of iterations is itself a learned, decision-dependent quantity. The model is allowed to spend orders of magnitude more compute on a genuinely hard decision than on a trivial one. We deliberately do not publish how the depth is selected.

**Evidence-token routing.** Some tokens in the input carry decision-relevant evidence. Most do not. A routing layer learns to send the high-value tokens to the deeper part of the network while routine tokens skip ahead. The effect is that compute concentrates where the information is, not where the input happens to be longest.

These three are not independent features. They compose. A decision can be reflex on one channel and deep on another. A long input can trigger deep reasoning on a small subset of its tokens and reflex on the rest. The architecture is sparse in multiple dimensions at once, and the dimensions interact.

## Latent reasoning, briefly

Latent reasoning is the part of this story that has the most published precedent and the least to hide. The basic idea is that the model's hardest thinking should happen in continuous representation space, not by emitting tokens through a softmax.

A traditional chain-of-thought model thinks by writing English. That is fine for tasks where the thinking *is* English. For tasks where the thinking is numerical, structural, or multi-signal -- and trading decisions are all three at once -- squeezing intermediate computation through a tokenizer designed for prose throws away most of the available compute.

In our architecture, the model can switch into a latent loop where the hidden state is fed back as the next input embedding without ever committing to a discrete word. Only when the loop terminates does the model emit audit prose and a typed action. The discrete output is the *summary* of the reasoning, not the reasoning itself.

How the loop terminates is, deliberately, not something we are publishing.

## Sparse cognition, not small cognition

The phrase we use internally is **sparse cognition**. The total cognitive capacity of the system can be much larger than the active capacity any single decision uses, and that is the whole point.

This shows up at every level. Sparse mixture-of-experts means most parameters are not active for most tokens. Mixture-of-depths means most layers are not visited by most tokens. Adaptive latent depth means most decisions do not trigger long reasoning loops. Evidence-token routing means most tokens do not reach the deep path.

The model is not small. It is *sparse*. The stored capacity is broad; the active footprint is narrow; the compute follows the evidence. That combination is what makes consumer-hardware frontier work possible. A dense model with the same active footprint would be much weaker. A dense model with the same total capacity would not fit on the GPU.

## The right to abstain from thinking

There is a property of adaptive compute that we did not anticipate when we started building it, and that we now consider central.

**The model gains the right to abstain from thinking.**

In a fixed-compute architecture, every decision burns the same FLOPs whether or not the model has anything useful to say. This produces a subtle pathology: the model is structurally pressured to *generate output* even when the honest answer is "I do not know." It cannot signal that it has nothing to contribute by simply consuming less compute.

An adaptive-compute model can. A reflex pass on a low-evidence input is, implicitly, the model saying "this one is not worth thinking about, here is the obvious answer." A long latent loop is the model saying "this one matters, give me a moment." The compute trace itself becomes part of the audit.

We have started reading the compute trace deliberately. Decisions that produce a lot of confidence with very little compute are different from decisions that produce the same confidence after a long latent loop. The former is reflex. The latter is judgment. They should be treated differently by the rest of the system, and increasingly, they are.

## Why this matters

Three reasons.

**Economics.** Equal-compute-per-token is enormously wasteful on a consumer envelope. Adaptive compute is how the small-hardware story stops being a sacrifice and starts being an advantage. The model spends its limited budget where it counts.

**Quality.** Hard decisions get more thinking. Easy decisions stop being polluted by overprocessed noise. The decision-quality curve as a function of difficulty starts looking like it should.

**Auditability.** The compute trace is a readable artifact. It tells you what the model treated as important. That is information the shell, the verifier, and the operator can all use.

## What comes next

The next entry covers **compact frontier architectures** -- the parameter systems that make sparse cognition cheap to store. Ternary FFNs, routed low-rank experts, and the storage-aware design choices that determine whether a 1B model can carry a many-B specialist skill surface without secretly turning into a 32B model on disk.

We will also return, later in the series, to how the **shell governs adaptive compute** -- because letting the model decide how hard to think is only safe if the layer above it can refuse, cap, or override that decision when the stakes demand it.

For now: stop spending equal compute on every input. Most of your tokens do not deserve it. Most of your decisions do not need it. The ones that do should get much more than you are currently giving them.

---

*Implementation details and certain training procedures are intentionally withheld.*

*Part 4 of an ongoing devlog series. Routing logic and termination criteria are intentionally not described.*

*If this work is useful to you and you want to support it: [ko-fi.com/tjarvis91](https://ko-fi.com/tjarvis91)*
