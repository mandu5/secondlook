# Feedback inbox example

The packaged canonical fixture lives in [`src/secondlook/demo`](../../src/secondlook/demo/).

```bash
secondlook demo --offline --output .secondlook/example
```

This copies the synthetic source and capsule into a sibling `example-input` directory and writes the experiment to `example`. It never rewrites the fixture. `reference.json` is a hand-authored offline repair; live mode does not load or show that repair to the model.
