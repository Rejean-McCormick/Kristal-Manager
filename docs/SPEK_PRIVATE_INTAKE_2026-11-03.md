# Réception du paquet privé Spek dans Kristal-Manager

`python -m kristal_manager.private_spek_intake --lock ... --graph ... --identity-map ...`

Contrôle en lecture seule de l'empreinte du graphe canonique v11, des
correspondances historiques `by_kind.A`, des identifiants référencés par les
champs et de la cohérence des relations déclarées. Refuse tout paquet qui
s'auto-attribue une approbation. Ne qualifie pas la vérité scientifique et ne
modifie pas le canon. Ne remplace **aucun** contrôle C1/C2/C3.
