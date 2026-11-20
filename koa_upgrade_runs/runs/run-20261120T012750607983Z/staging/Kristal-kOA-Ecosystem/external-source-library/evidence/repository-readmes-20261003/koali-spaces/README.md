# Koali Spaces reference implementation

Reference implementation of the independently versioned Koali Spaces experience layer. The kOA integration protocol identifier remains `koa_spaces`; the public product name is **Koali Spaces**.

Koali Spaces composes validated Space definitions and product/module interface manifests into a responsive Ant Design shell. It is an optional **integrated composition host**, not the mandatory runtime of product user interfaces. A product can remain independently runnable while contributing routes, surface profiles, navigation, widgets, commands and contextual-inspector references to Koali Spaces. Koali Spaces owns presentation and experience composition only: it does not acquire owner business data, workflow, authorization, identity, or internal application UI authority.

## Surface Layer

The repository now contains the Koali Spaces Surface Layer v1.1 specification with the **implementation hardening baseline v1.2**:

- server-side `SurfaceResolutionService`;
- strict `ResolvedSurfaceInternal -> SurfaceDescriptorPublic` minimization;
- three closed surface kinds: `local_shell_page`, `registered_component_surface`, `local_module_surface`;
- closed local registries rather than manifest-driven executable imports;
- `ApplicationHost` with framed and immersive Koali layout modes;
- owner-router preservation after the initial admitted deep link, including namespace-safe owner `/` routes and canonical alias forwarding;
- a separate Koali-owned runtime registration projection (`surface-runtime.json`);
- bounded iframe loading/retry behavior with explicit render-state tracking;
- CSP frame allowlisting without arbitrary runtime URLs from Space definitions, plus closed iframe permission/sandbox token catalogues;
- lifecycle requests separated from process execution;
- global Home/Health/Offline/Settings surfaces and closed Search/Tasks provider registries;
- strict activation checks for route namespaces, fallback references, `home_route_override`, shell-page ownership and schema-safe paths;
- immersive focus restoration with the activation control kept mounted;
- semantic module accent tokens mapped through safe CSS-variable indirection;
- declarative product `surface_profiles` that project existing routes/navigation/widgets without duplicating product pages;
- explicit UI portability metadata for standalone + integrated product operation;
- dynamic production product discovery from admitted manifests, plus a development-only linked-repository catalogue for one-command ecosystem bootstrap;
- Appearance Authority with Space policy/defaults separated from device-local user preferences;
- system/light/dark mode, canonical local accents, density and surface style;
- adaptive shell chrome that omits empty sidebar/Drawer and keeps the healthy topbar quiet;
- addressable/restorable product surface state through reserved `ks_surface` navigation metadata;
- topbar projection binding (`projection_ref`) separated from route/command activation.

The final transport catalogue, optional parent/child bridge, Browser Fullscreen behavior and display-mode persistence remain explicit `OPEN-KS-SURF-*` decisions in `docs/06-surface-layer/`. Global SSO is closed by `ADR-KS-SURF-0001` as the `koa-common-oidc-v1` integration profile; Koali Spaces still does not become an IdP or inject owner credentials.

## Stack and runtime

The reference stack is Next.js 15.5.24, React 18.2.0, Ant Design 5.26.2, `@ant-design/pro-components` 2.8.10, TypeScript 5.9.x and pnpm 10.20.0.

Presentation HTTP is loopback-bound by default. Linux additionally exposes the declared HTTP-over-Unix control boundary; Windows disables that Unix socket for presentation/runtime smoke testing. Required shell runtime assets are local and remote runtime assets are rejected.

Useful gates:

```text
pnpm run validate
pnpm run build
pnpm run smoke:runtime
```

`validate` includes Surface Layer spec validation. `build` packages the Next standalone runtime and verifies `dist/runtime/server.js`. `smoke:runtime` boots the packaged runtime and checks the principal shell routes.


## Ecosystem owner-contract development

`pnpm dev` starts one generic workspace launcher before starting the Koali shell. Koali itself does not know whether an owner application is Django, Nest, Next, Streamlit, Python, or another stack. Each owner repository publishes a root `koali.integration.json` containing its own development commands, embed target, port variables, and required readiness probes.

The current owner contracts cover Konnaxion, Konnaxion Worlds, Orgo, Orgo Worlds, SemantiK Architect, and Médiathèque kOA. Worlds repositories remain selectable sources for the same product identity rather than duplicate shell modules. Kristal Framework, kOA Linux, Koali Control Panel, and kOA Digital Ecosystem remain source/infrastructure links rather than fake application surfaces.

Repository discovery is only a bootstrap mechanism. After the first successful discovery, Koali writes `.koali-dev/workspace.json` and prefers those explicit working-tree links on later runs. No owner source is copied into this repository.

Runtime readiness is contract-driven and conjunctive: every required probe must be ready before the product is marked ready. A healthy frontend with a failed required API therefore becomes `degraded`, not `ready`. The `/ecosystem` page shows owner-contract admission, process state, and individual probes.

Use `pnpm run dev:koali` to start only the Koali shell, `pnpm run ecosystem:workspace` to refresh discovery/runtime projection without process launch, or `KOALI_ECOSYSTEM_AUTOSTART=0 pnpm dev` to link without spawning owner runtimes. See `UPDATE_KS4_OWNER_CONTRACTS.md`.

## Runtime surface registry

By default Koali reads:

```text
<KOALI_SPACES_STATE_ROOT>/surface-runtime.json
```

or the path in `KOALI_SPACES_SURFACE_REGISTRY`. This file is a Koali runtime projection, not a capability grant. Module manifests still cannot provide arbitrary executable URLs.

Additional absolute iframe origins must also be present in the build-time `KOALI_SPACES_FRAME_SRC` CSP allowlist. The absence of a runtime registration or target fails closed.

## Naming

Use **Koali Spaces** for product/UI/repository naming. Use `koa_spaces` only where the existing kOA protocol/contract identifier requires it. Runtime configuration uses `KOALI_SPACES_*` environment variables.


## Product UI portability

Koali Spaces intentionally supports removable products. The integrated shell discovers only modules/products that are enabled by the active Space and backed by admitted manifests. A product such as Orgo or Konnaxion can expose a standalone application entry point and also publish an integrated manifest. Removing one product removes its manifest contribution; it must not require source edits to unrelated product interfaces.

The current contract remains backward compatible: manifests without `surface_profiles` are treated as one synthetic `control` surface using their existing home route, sidebar and topbar widgets.
