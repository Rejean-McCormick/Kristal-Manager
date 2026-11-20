# Médiathèque kOA — workspace local

Ce workspace contient **une seule application** et son **contenu adjacent** :

```text
mediatheque/          # logiciel
mediatheque-content/  # contenu local/privé
```

Lance l'application depuis `mediatheque/Start-KoaGui.ps1`. Elle détecte automatiquement `mediatheque-content/`.

Le dossier `mediatheque-content/` peut être déplacé hors de ce workspace en définissant `KOA_CONTENT_ROOT`. Il ne doit pas être traité comme un second repo applicatif.

La Médiathèque UCKK n'est pas incluse ici : elle reste une implémentation Moodle séparée.
