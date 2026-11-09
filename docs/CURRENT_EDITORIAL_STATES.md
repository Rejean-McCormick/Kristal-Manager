# Current editorial states (Manager + Analysis Center)

Kristal Manager is a new local product. Default views show one **current editorial state** for each Kristal, not the history of earlier proposals.

- **Ready:** local structure, source evidence and the current semantic description are available, with no open issue detected by this limited review. **Not** domain certification, scientific approval, publication permission, or Framework C1/C2/C3.
- **Needs work:** a concrete structural problem or evidence/catalogue gap was observed.
- **Building:** the workspace declares its authoring status as `building`.
- **Not assessed:** the evidence, native semantics or an unresolved current classification proposal needs review. This does **not** mean the Kristal is defective.

The **Essential** and **Review queue** views in both windows use these states. The Review focus chooser can filter by each one. Technical and older review data remain available in detailed views when needed, but archived suggestions alone do not change the current editorial state.

## Lightweight decisions

Select a Kristal and choose **Editorial state** to record the current editorial decision (Ready / Needs work / Not assessed) or clear it. Only the current decision and a short optional note are kept. No growing historical ledger is created.

The decision file is stored in the user's local app-data directory, **outside** `locals` and outside the Manager application folder. A saved decision is compared with current workspace metadata, authoring documents, the source catalogue, the canonical index and its registered canonical artifacts. When any of these sources change, the decision becomes **Not assessed** until reconsidered. Manager never automatically changes the canonical classification, the workspace `status`, or a Framework approval.

Changing a structural problem or a workspace still marked `building` to Ready is refused. The independent Framework qualification process remains separate.

## Scope and safety

This change only modifies Manager code and adds a local decision registry **when the operator explicitly saves a decision**. Browsing, scanning and exporting remain read-only for Kristal source trees. Publishing, Git and remote synchronization stay blocked. Inventory-only scans still do not verify derived Discovery 3.3 files.
