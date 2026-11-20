# Théophile — mini-site premium 

Mini-site Next.js pour une présence vitrine haut de gamme : blueprint architectural premium, bleu nuit, ivoire, or doux, portail, chemin et animations sobres.

## Pages incluses

- `/` — Accueil
- `/methode` — Cristalliser / Éclairer / Soutenir
- `/systemes` — Ce qu’est un système opérable
- `/contact` — Page de contact par lien email


## Lancement automatique sur Windows

Double-clique sur :

```txt
start-theophile.bat
```

Le script vérifie Node.js, installe les dépendances au premier lancement, démarre le serveur local et ouvre automatiquement :

```txt
http://localhost:3000
```

Pour arrêter le site local : `CTRL + C` dans la fenêtre du terminal.

## Lancer le site

```bash
npm install
npm run dev
```

Puis ouvrir :

```txt
http://localhost:3000
```

## Déploiement

Le projet est prêt pour Vercel.

```bash
npm run build
```

## Personnaliser

Les textes principaux sont dans :

```txt
lib/brand.ts
```

À modifier en priorité :

```ts
contactEmail: "contact@theophile.studio"
```

## Structure

```txt
app/
  page.tsx
  methode/page.tsx
  systemes/page.tsx
  contact/page.tsx
components/
  BlueprintBackground.tsx
  PortalMark.tsx
  BlueprintCard.tsx
  ContactPanel.tsx
  Footer.tsx
  Navigation.tsx
  PathDivider.tsx
  SectionTitle.tsx
lib/
  brand.ts
public/
  favicon.svg
  og-theophile.png
```


## Logo SVG stack intégré

Le package `theophile-svg-stack-package-with-bat(4).zip` a été intégré au mini-site.

Fichiers ajoutés :

```txt
components/TheophileSvgStack.tsx
public/logo-layers/*.svg
app/logo-test/page.tsx
tools/logo-stack/
```

Le hero de la page d’accueil utilise maintenant :

```tsx
<TheophileSvgStack />
```

Page de test locale :

```txt
http://localhost:3000/logo-test
```

Les outils d’ajustement/export fournis dans ton package sont conservés dans :

```txt
tools/logo-stack/
```

Pour modifier le logo plus tard : corriger les layers/placements avec le GUI, exporter le JSON, puis remplacer les SVG dans `public/logo-layers/` ou mettre à jour `components/TheophileSvgStack.tsx`.

## Lancement Windows avec logs visibles

- Double-cliquez `start-theophile.bat`.
- Au premier lancement, l'installation peut prendre plusieurs minutes.
- Le script affiche maintenant les logs npm pour vérifier que l'installation avance.
- Si l'installation semble réellement bloquée, fermez la fenêtre et lancez `reset-install.bat`.

## Correction SVG baked

Les ajustements de proportion/position du petit outil ont été intégrés directement dans les fichiers SVG de `public/logo-layers/`.

- Les `x` / `y` du composant React sont remis à `0`.
- Le `scale` du composant React est remis à sa valeur neutre `1`.
- Les animations sont conservées dans `components/TheophileSvgStack.tsx`.
- Les valeurs d'ajustement utilisées pour le baking sont archivées dans `tools/logo-stack/placements.baked-source.json`.
- Les SVG originaux non baked sont archivés dans `tools/logo-stack/original-unbaked/`.
