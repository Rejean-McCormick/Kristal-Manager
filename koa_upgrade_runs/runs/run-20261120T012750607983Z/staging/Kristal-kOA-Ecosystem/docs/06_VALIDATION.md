# Validation

Validation is layered. A structural Local Kit pass is not a claim that every domain assertion is universally true.

## Native domain validation

```bash
python knowledge-base/tools/validate.py
```

At normalization time this passes with 7,929 assertions, 2,523 relations, 718 referents and 117 components.

## Legacy v9 validation

```bash
python .kristal/v9/validate.py
```

The retained legacy envelope validates the pre-existing state commitment:

`sha256:c5cea1280163558bc93a3126138628df918f919482ab9278c4fb7f32c09d8322`

## Local Kit 3.2.2

```bash
python tools/kristal.py check .
python tools/kristal.py build-v9 .
```

The 3.2.2 build is expected to preserve the same State Logical Commitment because it composes the same canonical member commitment under the same state scope. Any divergence must be investigated before publication.
