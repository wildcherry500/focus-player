# Clojure → Java Bridge for Rama References

Why this file exists: parts of this reference tree are Clojure-targeted — notably
RPL's own AI skill (`repos/rama-ai-learn/plugins/rama-skill/`) and the `clj-*.md`
docs pages. The **concepts and methodology in those files are authoritative and
language-neutral**. This bridge lets you read them fluently and map them to Java.

Operating principle (a default, not a handcuff):
- **Concepts, design reasoning, methodology** → take directly from Clojure material.
- **Syntax and API signatures** → source from the Java docs (`docs-rama-site/`,
  non-clj pages are Java-primary) and `repos/agent-o-rama/examples/java/`.
- Transliterating Clojure code to Java line-by-line is usually the wrong move;
  find the Java-native expression of the same idea. If no Java example covers it,
  say so explicitly and verify against live Javadoc rather than inventing.
- If newer official material contradicts this file, the official material wins.

## Module structure

| Clojure | Java |
|---|---|
| `(defmodule MyModule [setup topologies] ...)` | `class MyModule implements RamaModule { void define(Setup setup, Topologies topologies) }` |
| Agent modules: same `defmodule` + agent fns | `class MyAgents extends AgentModule` (or `RamaModule` + `AgentTopology.create(setup, topologies)` for combined) |
| `(declare-depot setup *my-depot :random)` | `setup.declareDepot("*my-depot", Depot.random())` |
| `(declare-depot setup *d (hash-by :user-id))` | `setup.declareDepot("*d", Depot.hashBy("userId"))` — field extraction differs: keyword fn vs field name/extractor |
| `(stream-topology topologies "s")` | `topologies.stream("s")` |
| `<<query-topology` | `topologies.query(...)` — see docs-rama-site/query.md |

## Dataflow language

| Clojure | Java |
|---|---|
| `(source> *depot :> *data)` | `.source("*depot").out("*data")` |
| `:>` output binding | `.out("*var")` |
| `?<-` (run dataflow inline) | no direct equivalent — Java composes via `Block` builders |
| `(deframaop ...)` / `(deframafn ...)` | custom operations — see docs-rama-site/intermediate-dataflow.md |
| `(|hash *k)` | `.hashPartition("*k")` |
| `(|all)` | `.allPartition()` |
| `(local-transform> [(keypath *k) (termval *v)] $$p)` | `.localTransform("$$p", Path.key("*k").termVal("*v"))` |
| `(local-select> (keypath *k) $$p :> *v)` | `.localSelect("$$p", Path.key("*k")).out("*v")` |
| path navigators: `keypath`, `termval`, `term`, `must`, `mapVals` | `Path.key(...)`, `.termVal(...)`, `.term(fn)`, `.must(...)`, `.mapVals()` — same navigator names, builder-chained. Full list: docs-rama-site/paths.md |

## Naming conventions — identical in both languages
- Depots: `*name` · PStates/stores: `$$name` · dataflow vars: `*var`
- These are string content, not language syntax — they do NOT change in Java.

## Aggregation
- `+compiled-agg` style aggregators in Clojure ↔ `CompoundAgg` / `Agg.sum()` etc.
  in Java. Semantics (accumulator vs combiner) are identical: docs-rama-site/aggregators.md.

## Reading RPL's rama-ai-learn skill (Clojure-targeted)
Read these for full conceptual value, translating only mechanically:
- Design/methodology refs (phases, app-design, depot-design, patterns,
  troubleshooting, pstate-schema concepts) → **use as-is**.
- Syntax refs (syntax.md, pstate-schema-clojure-api.md) → use this bridge +
  Java docs pages instead.
- Their phased methodology (spec → plan → implement → validate → test) applies
  unchanged to Java projects and pairs well with the lumino-plan-review-gate.

## When RPL ships the Java skill
Their README states a Java equivalent of the rama-ai-learn skill is planned.
When released, pull it into this tree and retire the syntax half of this bridge.
Check: https://github.com/redplanetlabs/rama-ai-learn
